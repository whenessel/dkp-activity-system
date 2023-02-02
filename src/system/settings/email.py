from system.env import env


EMAIL_CONFIG = env.email('EMAIL_URL', default='consolemail://')

DEFAULT_FROM_EMAIL = f"DKP <{EMAIL_CONFIG['EMAIL_HOST_USER']}>"

vars().update(EMAIL_CONFIG)
vars().update(EMAIL_CONFIG.get('OPTIONS', {}))
