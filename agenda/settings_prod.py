from .settings import *


def bar_str(name, default=''):
    value = env_str(name, default)
    if value is None:
        return ''
    return value


def bar_bool(name, default=False):
    return bar_str(name, str(default)).lower() == 'true'


def bar_list(name, default=''):
    return [item.strip() for item in bar_str(name, default).split(',') if item.strip()]


SECRET_KEY = bar_str('BAR_SECRET_KEY', SECRET_KEY)
DEBUG = False
ALLOWED_HOSTS = bar_list('BAR_ALLOWED_HOSTS', '127.0.0.1,localhost')
CSRF_TRUSTED_ORIGINS = bar_list('BAR_CSRF_TRUSTED_ORIGINS', '')

DATABASES = {
    'default': {
        'ENGINE': bar_str('BAR_DB_ENGINE', 'django.db.backends.mysql'),
        'NAME': bar_str('BAR_DB_NAME', 'agenda_consultorio'),
        'USER': bar_str('BAR_DB_USER', 'root'),
        'PASSWORD': bar_str('BAR_DB_PASSWORD', ''),
        'HOST': bar_str('BAR_DB_HOST', '127.0.0.1'),
        'PORT': bar_str('BAR_DB_PORT', '3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
        },
    }
}

EMAIL_BACKEND = bar_str('BAR_EMAIL_BACKEND', EMAIL_BACKEND)
EMAIL_HOST = bar_str('BAR_EMAIL_HOST', EMAIL_HOST)
EMAIL_HOST_USER = bar_str('BAR_EMAIL_HOST_USER', EMAIL_HOST_USER)
EMAIL_HOST_PASSWORD = bar_str('BAR_EMAIL_HOST_PASSWORD', EMAIL_HOST_PASSWORD)
EMAIL_PORT = int(bar_str('BAR_EMAIL_PORT', str(EMAIL_PORT)))
EMAIL_USE_TLS = bar_bool('BAR_EMAIL_USE_TLS', EMAIL_USE_TLS)
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER or DEFAULT_FROM_EMAIL

DJANGO_USE_WHITENOISE = True
if 'whitenoise.middleware.WhiteNoiseMiddleware' not in MIDDLEWARE:
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

SECURE_SSL_REDIRECT = bar_bool('BAR_SECURE_SSL_REDIRECT', True)
SESSION_COOKIE_SECURE = bar_bool('BAR_SESSION_COOKIE_SECURE', True)
CSRF_COOKIE_SECURE = bar_bool('BAR_CSRF_COOKIE_SECURE', True)
SECURE_HSTS_SECONDS = int(bar_str('BAR_SECURE_HSTS_SECONDS', '31536000'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = bar_bool('BAR_SECURE_HSTS_INCLUDE_SUBDOMAINS', True)
SECURE_HSTS_PRELOAD = bar_bool('BAR_SECURE_HSTS_PRELOAD', True)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
