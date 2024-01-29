import asyncio
import json
import os
import typing as t
import uuid

_T = t.TypeVar("_T")


ObjectHook = t.Callable[[t.Dict[str, t.Any]], t.Any]


class PersistJsonFile(t.Generic[_T]):
    """The "database" object. Internally based on ``json``."""

    def __init__(
        self,
        name: str,
        *,
        object_hook: t.Optional[ObjectHook] = None,
        encoder: t.Optional[t.Type[json.JSONEncoder]] = None,
        load_later: bool = False,
    ):
        self.name = name
        self.object_hook = object_hook
        self.encoder = encoder
        self.loop = asyncio.get_running_loop()
        self.lock = asyncio.Lock()
        self._db: t.Dict[str, t.Union[_T, t.Any]] = {}
        if load_later:
            self.loop.create_task(self.load())
        else:
            self.load_from_file()

    def load_from_file(self):
        try:
            with open(self.name, "r", encoding="utf-8") as f:
                self._db = json.load(f, object_hook=self.object_hook)
        except FileNotFoundError:
            self._db = {}

    async def load(self):
        async with self.lock:
            await self.loop.run_in_executor(None, self.load_from_file)

    def _dump(self):
        temp = f"{uuid.uuid4()}-{self.name}.tmp"
        with open(temp, "w", encoding="utf-8") as tmp:
            json.dump(
                self._db.copy(),
                tmp,
                ensure_ascii=True,
                cls=self.encoder,
                separators=(",", ":"),
            )

        # atomically move the file
        os.replace(temp, self.name)

    async def save(self) -> None:
        async with self.lock:
            await self.loop.run_in_executor(None, self._dump)

    @t.overload
    def get(self, key: t.Any) -> t.Optional[t.Union[_T, t.Any]]:
        ...

    @t.overload
    def get(self, key: t.Any, default: t.Any) -> t.Union[_T, t.Any]:
        ...

    def get(self, key: t.Any, default: t.Any = None) -> t.Optional[t.Union[_T, t.Any]]:
        """Retrieves a config entry."""
        return self._db.get(str(key), default)

    async def put(self, key: t.Any, value: t.Union[_T, t.Any]) -> None:
        """Edits a config entry."""
        self._db[str(key)] = value
        await self.save()

    async def remove(self, key: t.Any) -> None:
        """Removes a config entry."""
        del self._db[str(key)]
        await self.save()

    def __contains__(self, item: t.Any) -> bool:
        return str(item) in self._db

    def __getitem__(self, item: t.Any) -> t.Union[_T, t.Any]:
        return self._db[str(item)]

    def __len__(self) -> int:
        return len(self._db)

    def all(self) -> t.Dict[str, t.Union[_T, t.Any]]:
        return self._db
