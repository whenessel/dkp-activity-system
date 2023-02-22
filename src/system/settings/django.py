from system.env import env, BASE_DIR, Path


DEBUG = env.bool('DEBUG', default=True)

SITE_ID = env.int('SITE_ID', default=0)

SECRET_KEY = env.str('SECRET_KEY', default='django-insecure-&s91k(3aj-jthe*u$x7ziu0w1z1g$i06dcsm2d3!y-_n-e9ers')

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['*', ])

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

]

THIRD_PARTY_APPS = [
    'import_export',
]

LOCAL_APPS = [
    'evebot',
    'activity',

]

INSTALLED_APPS = [
    *DJANGO_APPS,
    *THIRD_PARTY_APPS,
    *LOCAL_APPS
]


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


ROOT_URLCONF = 'system.urls'


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


WSGI_APPLICATION = 'system.wsgi.application'
ASGI_APPLICATION = 'system.asgi.application'


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},

]


PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]


LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_L10N = True
USE_TZ = False


DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
DATETIME_INPUT_FORMATS = '%Y-%m-%d %H:%M:%S'


STORAGE_ROOT = env.get_value('STORAGE_ROOT', cast=Path, default=BASE_DIR / 'storage')


STATIC_URL = '/static/'
STATIC_ROOT = env.get_value('STATIC_ROOT', cast=Path, default=BASE_DIR / 'static')

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',

]

STATICFILES_DIRS = [

]


MEDIA_URL = '/media/'
MEDIA_ROOT = env.get_value('MEDIA_ROOT', cast=Path, default=BASE_DIR / 'media')


FIXTURE_DIRS = [
    BASE_DIR / 'fixtures',

]
