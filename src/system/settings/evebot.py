from pathlib import Path

from system.env import BASE_DIR, env

EVE_PREFIX = env.str("EVE_PREFIX", default="!")
EVE_GUILD = env.str("EVE_GUILD", default="")
EVE_CHANNEL = env.str("EVE_CHANNEL", default="")
EVE_OWNERS = env.list("EVE_OWNERS", cast=int, default=[])
EVE_TOKEN = env.str("EVE_TOKEN", default="")
EVE_APPLICATION_ID = env.int("EVE_APPLICATION_ID", default=None)
EVE_PUBLIC_KEY = env.str("EVE_PUBLIC_KEY", default="")
EVE_CLIENT_ID = env.int("EVE_CLIENT_ID", default=None)
EVE_CLIENT_SECRET = env.str("EVE_CLIENT_SECRET", default="")
EVE_PERMISSIONS = env.int("EVE_PERMISSIONS", default=0)
EVE_SYNC_COMMANDS_GLOBALLY = env.bool("EVE_SYNC_COMMANDS_GLOBALLY", default=False)

EVE_PROXY_TYPE = env.str("EVE_PROXY_TYPE", default="")
EVE_PROXY_HOST = env.str("EVE_PROXY_HOST", default="")
EVE_PROXY_PORT = env.str("EVE_PROXY_PORT", default="")
EVE_PROXY_USER = env.str("EVE_PROXY_USER", default="")
EVE_PROXY_PASSWORD = env.str("EVE_PROXY_PASSWORD", default="")
