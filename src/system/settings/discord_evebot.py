from system.env import env


EVE_PREFIX = env.str('EVE_PREFIX', default='!')
EVE_GUILD = env.str('EVE_GUILD', default='')
EVE_CHANNEL = env.str('EVE_CHANNEL', default='')
EVE_OWNERS = env.list('EVE_OWNERS', default=['410756194597339136', ])
EVE_TOKEN = env.str('EVE_TOKEN', default='')
EVE_APPLICATION_ID = env.str('EVE_APPLICATION_ID', default='')
EVE_PUBLIC_KEY = env.str('EVE_PUBLIC_KEY', default='')
EVE_CLIENT_ID = env.str('EVE_CLIENT_ID', default='')
EVE_CLIENT_SECRET = env.str('EVE_CLIENT_SECRET', default='')
EVE_PERMISSIONS = env.int('EVE_PERMISSIONS', default=0)
EVE_SYNC_COMMANDS_GLOBALLY = env.bool('EVE_SYNC_COMMANDS_GLOBALLY', default=False)

EVE_INSTALLED_COGS = [
    'game_activity',

]