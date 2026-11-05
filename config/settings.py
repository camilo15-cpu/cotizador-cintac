"""
Configuración de Django para el Cotizador Interno de Fletes CINTAC.

Toda la configuración sensible se lee desde variables de entorno (django-environ),
por lo que el mismo código sirve en el computador local y en Render.
"""
import sys
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, False))
_archivo_env = BASE_DIR / '.env'
if _archivo_env.exists():
    environ.Env.read_env(_archivo_env)

TESTING = 'test' in sys.argv

# ------------------------------------------------------------------ Seguridad básica
DEBUG = env('DEBUG')
# En producción SECRET_KEY es obligatoria: si falta, Django no arranca.
SECRET_KEY = env('SECRET_KEY', default='clave-insegura-solo-desarrollo' if DEBUG else environ.Env.NOTSET)

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])

# Render define esta variable automáticamente con el dominio público del servicio.
RENDER_EXTERNAL_HOSTNAME = env('RENDER_EXTERNAL_HOSTNAME', default='')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
    CSRF_TRUSTED_ORIGINS.append(f'https://{RENDER_EXTERNAL_HOSTNAME}')

# ------------------------------------------------------------------ Aplicaciones
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Aplicaciones del proyecto
    'apps.usuarios',
    'apps.tarifas',
    'apps.cotizaciones',
    'apps.auditoria',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',          # archivos estáticos en producción
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Obliga a cambiar la clave temporal antes de usar cualquier otra pantalla
    'apps.usuarios.middleware.CambioClaveObligatorioMiddleware',
]

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

# ------------------------------------------------------------------ Base de datos
# Con DATABASE_URL (Render / PostgreSQL local) se usa PostgreSQL; sin ella, SQLite para desarrollo.
if env('DATABASE_URL', default=''):
    DATABASES = {'default': env.db('DATABASE_URL')}
    DATABASES['default']['CONN_MAX_AGE'] = env.int('CONN_MAX_AGE', default=60)
    DATABASES['default']['CONN_HEALTH_CHECKS'] = True
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ------------------------------------------------------------------ Autenticación y contraseñas
AUTH_USER_MODEL = 'usuarios.Usuario'
LOGIN_URL = 'usuarios:login'
LOGIN_REDIRECT_URL = 'cotizaciones:simulador'
LOGOUT_REDIRECT_URL = 'usuarios:login'

AUTH_PASSWORD_VALIDATORS = [
    # Regla de la rúbrica (CP01): 8+ caracteres, mayúscula, minúscula, número y símbolo, vía regex
    {'NAME': 'apps.usuarios.validators.ComplejidadClaveValidator'},
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
]
# PBKDF2 con sal (por defecto de Django). Para usar Argon2: pip install argon2-cffi y
# anteponer 'django.contrib.auth.hashers.Argon2PasswordHasher' a PASSWORD_HASHERS.

# Sesión: se cierra por inactividad y la cookie no es accesible desde JavaScript
SESSION_COOKIE_AGE = env.int('SESSION_COOKIE_AGE', default=1800)
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
# La clave temporal se muestra una sola vez; los mensajes viajan en la sesión (servidor), no en cookie
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

# ------------------------------------------------------------------ Reglas del cotizador
# True: superar 25 t por contenedor (Decreto 75) bloquea la cotización. False: solo advierte.
COTIZADOR_BLOQUEAR_EXCESO_PESO = env.bool('COTIZADOR_BLOQUEAR_EXCESO_PESO', default=True)

# ------------------------------------------------------------------ Internacionalización
LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True

# ------------------------------------------------------------------ Archivos estáticos (WhiteNoise)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}

# ------------------------------------------------------------------ Endurecimiento en producción
if not DEBUG and not TESTING:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')   # Render termina el HTTPS en su proxy
    SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = env.int('SECURE_HSTS_SECONDS', default=3600)
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': 'INFO'},
}
