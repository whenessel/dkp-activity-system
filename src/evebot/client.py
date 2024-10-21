import asyncio
import datetime
import logging
import socket
import typing as t
from collections import deque
from urllib.parse import quote as _uriquote

import aiohttp
import yarl
from aiohttp_socks.connector import ProxyConnector
from discord import (
    AppInfo,
    ClientException,
    ConnectionClosed,
    DiscordServerError,
    File,
    Forbidden,
    HTTPException,
    LoginFailure,
    NotFound,
    PrivilegedIntentsRequired,
    RateLimited,
    Status,
    VoiceClient,
    utils,
)
from discord.activity import BaseActivity
from discord.client import Client, _loop
from discord.flags import Intents
from discord.gateway import *
from discord.gateway import DiscordClientWebSocketResponse
from discord.http import HTTPClient as DiscordHTTPClient
from discord.http import MultipartParameters, Route, json_or_text
from discord.shard import EventItem, EventType, Shard, ShardInfo
from discord.state import AutoShardedConnectionState, ConnectionState
from discord.types import user
from discord.types.snowflake import Snowflake
from discord.utils import MISSING

if t.TYPE_CHECKING:
    from discord.gateway import DiscordWebSocket
    from discord.types import message

    T = t.TypeVar("T")
    BE = t.TypeVar("BE", bound=BaseException)
    Response = t.Coroutine[t.Any, t.Any, T]


_log = logging.getLogger(__name__)


class HTTPClient(DiscordHTTPClient):
    """Represents an HTTP client sending HTTP requests to the Discord API."""

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        connector: t.Optional[aiohttp.BaseConnector] = None,
        *args: t.Any,
        proxy: t.Optional[str] = None,
        proxy_auth: t.Optional[aiohttp.BasicAuth] = None,
        proxy_uri: t.Optional[str] = None,
        unsync_clock: bool = True,
        http_trace: t.Optional[aiohttp.TraceConfig] = None,
        max_ratelimit_timeout: t.Optional[float] = None,
    ) -> None:
        super().__init__(
            loop,
            connector,
            proxy=proxy,
            proxy_auth=proxy_auth,
            unsync_clock=unsync_clock,
            http_trace=http_trace,
            max_ratelimit_timeout=max_ratelimit_timeout,
        )
        self.proxy_uri = proxy_uri

    @property
    def session(self) -> aiohttp.ClientSession:
        return self.__session

    async def static_login(self, token: str) -> user.User:
        # Necessary to get aiohttp to stop complaining about session creation
        if self.connector is MISSING:
            # discord does not support ipv6
            self.connector = aiohttp.TCPConnector(limit=0, family=socket.AF_INET)

        if self.proxy_uri:
            self.connector = ProxyConnector.from_url(self.proxy_uri)

        self.__session = aiohttp.ClientSession(
            connector=self.connector,
            ws_response_class=DiscordClientWebSocketResponse,
            trace_configs=None if self.http_trace is None else [self.http_trace],
        )

        self._global_over = asyncio.Event()
        self._global_over.set()

        old_token = self.token
        self.token = token

        try:
            data = await self.request(Route("GET", "/users/@me"))
        except HTTPException as exc:
            self.token = old_token
            if exc.status == 401:
                raise LoginFailure("Improper token has been passed.") from exc
            raise

        return data

    async def request(
        self,
        route: Route,
        *,
        files: t.Optional[t.Sequence[File]] = None,
        form: t.Optional[t.Iterable[t.Dict[str, t.Any]]] = None,
        **kwargs: t.Any,
    ) -> t.Any:
        method = route.method
        url = route.url
        route_key = route.key

        bucket_hash = None
        try:
            bucket_hash = self._bucket_hashes[route_key]
        except KeyError:
            key = f"{route_key}:{route.major_parameters}"
        else:
            key = f"{bucket_hash}:{route.major_parameters}"

        ratelimit = self.get_ratelimit(key)

        # header creation
        headers: t.Dict[str, str] = {
            "User-Agent": self.user_agent,
        }

        if self.token is not None:
            headers["Authorization"] = "Bot " + self.token
        # some checking if it's a JSON request
        if "json" in kwargs:
            headers["Content-Type"] = "application/json"
            kwargs["data"] = utils._to_json(kwargs.pop("json"))

        try:
            reason = kwargs.pop("reason")
        except KeyError:
            pass
        else:
            if reason:
                headers["X-Audit-Log-Reason"] = _uriquote(reason, safe="/ ")

        kwargs["headers"] = headers

        # Proxy support
        if self.proxy is not None:
            kwargs["proxy"] = self.proxy
        if self.proxy_auth is not None:
            kwargs["proxy_auth"] = self.proxy_auth

        if not self._global_over.is_set():
            # wait until the global lock is complete
            await self._global_over.wait()

        response: t.Optional[aiohttp.ClientResponse] = None
        data: t.Optional[t.Union[t.Dict[str, t.Any], str]] = None
        async with ratelimit:
            for tries in range(5):
                if files:
                    for f in files:
                        f.reset(seek=tries)

                if form:
                    form_data = aiohttp.FormData(quote_fields=False)
                    for params in form:
                        form_data.add_field(**params)
                    kwargs["data"] = form_data

                try:
                    async with self.__session.request(
                        method, url, **kwargs
                    ) as response:
                        _log.debug(
                            "%s %s with %s has returned %s",
                            method,
                            url,
                            kwargs.get("data"),
                            response.status,
                        )

                        data = await json_or_text(response)

                        discord_hash = response.headers.get("X-Ratelimit-Bucket")
                        has_ratelimit_headers = (
                            "X-Ratelimit-Remaining" in response.headers
                        )
                        if discord_hash is not None:
                            if bucket_hash != discord_hash:
                                if bucket_hash is not None:
                                    fmt = "A route (%s) has changed hashes: %s -> %s."
                                    _log.debug(
                                        fmt, route_key, bucket_hash, discord_hash
                                    )

                                    self._bucket_hashes[route_key] = discord_hash
                                    recalculated_key = (
                                        discord_hash + route.major_parameters
                                    )
                                    self._buckets[recalculated_key] = ratelimit
                                    self._buckets.pop(key, None)
                                elif route_key not in self._bucket_hashes:
                                    fmt = (
                                        "%s has found its initial rate limit "
                                        "bucket hash (%s)."
                                    )
                                    _log.debug(fmt, route_key, discord_hash)
                                    self._bucket_hashes[route_key] = discord_hash
                                    self._buckets[
                                        discord_hash + route.major_parameters
                                    ] = ratelimit

                        if has_ratelimit_headers:
                            if response.status != 429:
                                ratelimit.update(response, use_clock=self.use_clock)
                                if ratelimit.remaining == 0:
                                    _log.debug(
                                        "A rate limit bucket (%s) has been exhausted. "
                                        "Pre-emptively rate limiting...",
                                        discord_hash or route_key,
                                    )

                        # the request was successful so just return the text/json
                        if 300 > response.status >= 200:
                            _log.debug("%s %s has received %s", method, url, data)
                            return data

                        # we are being rate limited
                        if response.status == 429:
                            if not response.headers.get("Via") or isinstance(data, str):
                                # Banned by Cloudflare more than likely.
                                raise HTTPException(response, data)

                            if ratelimit.remaining > 0:
                                _log.debug(
                                    "%s %s received a 429 despite "
                                    "having %s remaining requests. "
                                    "This is a sub-ratelimit.",
                                    method,
                                    url,
                                    ratelimit.remaining,
                                )

                            retry_after: float = data["retry_after"]
                            if (
                                self.max_ratelimit_timeout
                                and retry_after > self.max_ratelimit_timeout
                            ):
                                _log.warning(
                                    "We are being rate limited. "
                                    "%s %s responded with 429. "
                                    "Timeout of %.2f was too long, erroring instead.",
                                    method,
                                    url,
                                    retry_after,
                                )
                                raise RateLimited(retry_after)

                            fmt = (
                                "We are being rate limited. %s %s responded with 429. "
                                "Retrying in %.2f seconds."
                            )
                            _log.warning(fmt, method, url, retry_after)

                            _log.debug(
                                "Rate limit is being handled "
                                "by bucket hash %s with %r major parameters",
                                bucket_hash,
                                route.major_parameters,
                            )

                            # check if it's a global rate limit
                            is_global = data.get("global", False)
                            if is_global:
                                _log.warning(
                                    "Global rate limit has been hit. "
                                    "Retrying in %.2f seconds.",
                                    retry_after,
                                )
                                self._global_over.clear()

                            await asyncio.sleep(retry_after)
                            _log.debug(
                                "Done sleeping for the rate limit. " "Retrying..."
                            )

                            # release the global lock now that the
                            # global rate limit has passed
                            if is_global:
                                self._global_over.set()
                                _log.debug("Global rate limit is now over.")

                            continue

                        # we've received a 500, 502, 504, or 524, unconditional retry
                        if response.status in {500, 502, 504, 524}:
                            await asyncio.sleep(1 + tries * 2)
                            continue

                        # the usual error cases
                        if response.status == 403:
                            raise Forbidden(response, data)
                        elif response.status == 404:
                            raise NotFound(response, data)
                        elif response.status >= 500:
                            raise DiscordServerError(response, data)
                        else:
                            raise HTTPException(response, data)

                # This is handling exceptions from the request
                except OSError as e:
                    # Connection reset by peer
                    if tries < 4 and e.errno in (54, 10054):
                        await asyncio.sleep(1 + tries * 2)
                        continue
                    raise

            if response is not None:
                # We've run out of retries, raise.
                if response.status >= 500:
                    raise DiscordServerError(response, data)

                raise HTTPException(response, data)

            raise RuntimeError("Unreachable code in HTTP handling")

    def send_message(
        self,
        channel_id: Snowflake,
        *,
        params: MultipartParameters,
    ) -> t.Any:
        r = Route("POST", "/channels/{channel_id}/messages", channel_id=channel_id)
        if params.files:
            return self.request(r, files=params.files, form=params.multipart)
        else:
            return self.request(r, json=params.payload)

    async def ws_connect(
        self, url: str, *, compress: int = 0
    ) -> aiohttp.ClientWebSocketResponse:
        kwargs = {
            "proxy_auth": self.proxy_auth,
            "proxy": self.proxy,
            "max_msg_size": 0,
            "timeout": 30.0,
            "autoclose": False,
            "headers": {
                "User-Agent": self.user_agent,
            },
            "compress": compress,
        }

        return await self.__session.ws_connect(url, **kwargs)


class EveClient(Client):
    def __init__(self, *args, intents: Intents, **options: t.Any) -> None:
        super().__init__(intents=intents, **options)
        self.loop: asyncio.AbstractEventLoop = _loop
        # self.ws is set in the connect method
        self.ws: DiscordWebSocket = None  # type: ignore
        self._listeners: t.Dict[
            str, t.List[t.Tuple[asyncio.Future, t.Callable[..., bool]]]
        ] = {}
        self.shard_id: t.Optional[int] = options.get("shard_id")
        self.shard_count: t.Optional[int] = options.get("shard_count")
        proxy: t.Optional[str] = options.pop("proxy", None)
        proxy_auth: t.Optional[aiohttp.BasicAuth] = options.pop("proxy_auth", None)
        proxy_uri: t.Optional[str] = options.pop("proxy_uri", None)
        unsync_clock: bool = options.pop("assume_unsync_clock", True)
        http_trace: t.Optional[aiohttp.TraceConfig] = options.pop("http_trace", None)
        max_ratelimit_timeout: t.Optional[float] = options.pop(
            "max_ratelimit_timeout", None
        )
        self.http: HTTPClient = HTTPClient(
            self.loop,
            proxy=proxy,
            proxy_auth=proxy_auth,
            proxy_uri=proxy_uri,
            unsync_clock=unsync_clock,
            http_trace=http_trace,
            max_ratelimit_timeout=max_ratelimit_timeout,
        )

        self._handlers: t.Dict[str, t.Callable[..., None]] = {
            "ready": self._handle_ready,
        }

        self._hooks: t.Dict[str, t.Callable[..., t.Coroutine[t.Any, t.Any, t.Any]]] = {
            "before_identify": self._call_before_identify_hook,
        }

        self._enable_debug_events: bool = options.pop("enable_debug_events", False)
        self._connection: ConnectionState[t.Self] = self._get_state(
            intents=intents, **options
        )
        self._connection.shard_count = self.shard_count
        self._closed: bool = False
        self._ready: asyncio.Event = MISSING
        self._application: t.Optional[AppInfo] = None
        self._connection._get_websocket = self._get_websocket
        self._connection._get_client = lambda: self

        if VoiceClient.warn_nacl:
            VoiceClient.warn_nacl = False
            _log.warning("PyNaCl is not installed, voice will NOT be supported")

    # internals

    def _get_websocket(
        self, guild_id: t.Optional[int] = None, *, shard_id: t.Optional[int] = None
    ) -> DiscordWebSocket:
        return self.ws

    def _get_state(self, **options: t.Any) -> ConnectionState:
        return super()._get_state(**options)


class EveAutoShardedClient(EveClient):
    if t.TYPE_CHECKING:
        _connection: AutoShardedConnectionState

    def __init__(self, *args: t.Any, intents: Intents, **kwargs: t.Any) -> None:
        kwargs.pop("shard_id", None)
        self.shard_ids: t.Optional[t.List[int]] = kwargs.pop("shard_ids", None)
        super().__init__(*args, intents=intents, **kwargs)

        if self.shard_ids is not None:
            if self.shard_count is None:
                raise ClientException(
                    "When passing manual shard_ids, you must provide a shard_count."
                )
            elif not isinstance(self.shard_ids, (list, tuple)):
                raise ClientException("shard_ids parameter must be a list or a tuple.")

        # instead of a single websocket, we have multiple
        # the key is the shard_id
        self.__shards = {}
        self._connection._get_websocket = self._get_websocket
        self._connection._get_client = lambda: self

    def _get_websocket(
        self, guild_id: t.Optional[int] = None, *, shard_id: t.Optional[int] = None
    ) -> DiscordWebSocket:
        if shard_id is None:
            shard_id = (guild_id >> 22) % self.shard_count  # type: ignore
        return self.__shards[shard_id].ws

    def _get_state(self, **options: t.Any) -> AutoShardedConnectionState:
        return AutoShardedConnectionState(
            dispatch=self.dispatch,
            handlers=self._handlers,
            hooks=self._hooks,
            http=self.http,
            **options,
        )

    @property
    def latency(self) -> float:
        if not self.__shards:
            return float("nan")
        return sum(latency for _, latency in self.latencies) / len(self.__shards)

    @property
    def latencies(self) -> t.List[t.Tuple[int, float]]:
        return [
            (shard_id, shard.ws.latency) for shard_id, shard in self.__shards.items()
        ]

    def get_shard(self, shard_id: int, /) -> t.Optional[ShardInfo]:
        try:
            parent = self.__shards[shard_id]
        except KeyError:
            return None
        else:
            return ShardInfo(parent, self.shard_count)

    @property
    def shards(self) -> t.Dict[int, ShardInfo]:
        return {
            shard_id: ShardInfo(parent, self.shard_count)
            for shard_id, parent in self.__shards.items()
        }

    async def launch_shard(
        self, gateway: yarl.URL, shard_id: int, *, initial: bool = False
    ) -> None:
        try:
            coro = DiscordWebSocket.from_client(
                self, initial=initial, gateway=gateway, shard_id=shard_id
            )
            ws = await asyncio.wait_for(coro, timeout=180.0)
        except Exception:
            _log.exception("Failed to connect for shard_id: %s. Retrying...", shard_id)
            await asyncio.sleep(5.0)
            return await self.launch_shard(gateway, shard_id)

        # keep reading the shard while others connect
        self.__shards[shard_id] = ret = Shard(ws, self, self.__queue.put_nowait)
        ret.launch()

    async def launch_shards(self) -> None:
        if self.is_closed():
            return

        if self.shard_count is None:
            self.shard_count: int
            self.shard_count, gateway_url = await self.http.get_bot_gateway()
            gateway = yarl.URL(gateway_url)
        else:
            gateway = DiscordWebSocket.DEFAULT_GATEWAY

        self._connection.shard_count = self.shard_count

        shard_ids = self.shard_ids or range(self.shard_count)
        self._connection.shard_ids = shard_ids

        for shard_id in shard_ids:
            initial = shard_id == shard_ids[0]
            await self.launch_shard(gateway, shard_id, initial=initial)

    async def _async_setup_hook(self) -> None:
        await super()._async_setup_hook()
        self.__queue = asyncio.PriorityQueue()

    async def connect(self, *, reconnect: bool = True) -> None:
        self._reconnect = reconnect
        await self.launch_shards()

        while not self.is_closed():
            item = await self.__queue.get()
            if item.type == EventType.close:
                await self.close()
                if isinstance(item.error, ConnectionClosed):
                    if item.error.code != 1000:
                        raise item.error
                    if item.error.code == 4014:
                        raise PrivilegedIntentsRequired(item.shard.id) from None
                return
            elif item.type in (EventType.identify, EventType.resume):
                await item.shard.reidentify(item.error)
            elif item.type == EventType.reconnect:
                await item.shard.reconnect()
            elif item.type == EventType.terminate:
                await self.close()
                raise item.error
            elif item.type == EventType.clean_close:
                return

    async def close(self) -> None:
        """|coro|

        Closes the connection to Discord.
        """
        if self.is_closed():
            return

        self._closed = True
        await self._connection.close()

        to_close = [
            asyncio.ensure_future(shard.close(), loop=self.loop)
            for shard in self.__shards.values()
        ]
        if to_close:
            await asyncio.wait(to_close)

        await self.http.close()
        self.__queue.put_nowait(EventItem(EventType.clean_close, None, None))

    async def change_presence(
        self,
        *,
        activity: t.Optional[BaseActivity] = None,
        status: t.Optional[Status] = None,
        shard_id: t.Optional[int] = None,
    ) -> None:
        """|coro|

        Changes the client's presence.

        Example: ::

            game = discord.Game("with the API")
            await client.change_presence(status=discord.Status.idle, activity=game)

        .. versionchanged:: 2.0
            Removed the ``afk`` keyword-only parameter.

        .. versionchanged:: 2.0
            This function will now raise :exc:`TypeError` instead of
            ``InvalidArgument``.

        Parameters
        ----------
        activity: Optional[:class:`BaseActivity`]
            The activity being done. ``None`` if no currently active activity is done.
        status: Optional[:class:`Status`]
            Indicates what status to change to. If ``None``, then
            :attr:`Status.online` is used.
        shard_id: Optional[:class:`int`]
            The shard_id to change the presence to. If not specified
            or ``None``, then it will change the presence of every
            shard the bot can see.

        Raises
        ------
        TypeError
            If the ``activity`` parameter is not of proper type.
        """

        if status is None:
            status_value = "online"
            status_enum = Status.online
        elif status is Status.offline:
            status_value = "invisible"
            status_enum = Status.offline
        else:
            status_enum = status
            status_value = str(status)

        if shard_id is None:
            for shard in self.__shards.values():
                await shard.ws.change_presence(activity=activity, status=status_value)

            guilds = self._connection.guilds
        else:
            shard = self.__shards[shard_id]
            await shard.ws.change_presence(activity=activity, status=status_value)
            guilds = [g for g in self._connection.guilds if g.shard_id == shard_id]

        activities = () if activity is None else (activity,)
        for guild in guilds:
            me = guild.me
            if me is None:
                continue

            me.activities = activities  # type: ignore
            me.status = status_enum

    def is_ws_ratelimited(self) -> bool:
        """:class:`bool`: Whether the websocket is currently rate limited.

        This can be useful to know when deciding whether you should query members
        using HTTP or via the gateway.

        This implementation checks if any of the shards are rate limited.
        For more granular control, consider :meth:`ShardInfo.is_ws_ratelimited`.

        .. versionadded:: 1.6
        """
        return any(shard.ws.is_ratelimited() for shard in self.__shards.values())
