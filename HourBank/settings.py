"""
Django settings for HourBank project.
"""

import os

from pathlib import Path
from dotenv import load_dotenv
import dj_database_url


# ==================================================
# المسار الرئيسي للمشروع
# ==================================================

BASE_DIR = Path(__file__).resolve().parent.parent


# ==================================================
# تحميل متغيرات ملف .env
# ==================================================

load_dotenv(BASE_DIR / '.env')


# ==================================================
# إعدادات الأمان
# ==================================================

SECRET_KEY = os.environ['DJANGO_SECRET_KEY']

DEBUG = os.getenv('DJANGO_DEBUG', 'True').strip().lower() in {
    '1', 'true', 'yes', 'on',
}


def env_list(name, default=''):
    """Return a clean comma-separated environment variable as a list."""
    return [item.strip() for item in os.getenv(name, default).split(',') if item.strip()]


ALLOWED_HOSTS = env_list(
    'DJANGO_ALLOWED_HOSTS',
    '127.0.0.1,localhost' if DEBUG else '',
)

CSRF_TRUSTED_ORIGINS = env_list('DJANGO_CSRF_TRUSTED_ORIGINS')

# Optional canonical public URL for integrations that need an absolute URL.
# Django's password reset view continues to use the current request host.
SITE_URL = os.getenv('SITE_URL', '').rstrip('/')


if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = os.getenv(
        'DJANGO_SECURE_SSL_REDIRECT', 'True'
    ).strip().lower() in {'1', 'true', 'yes', 'on'}

WEBRTC_ICE_SERVERS = [{'urls': os.getenv('WEBRTC_STUN_URL', 'stun:stun.l.google.com:19302')}]
if os.getenv('WEBRTC_TURN_URL'):
    WEBRTC_ICE_SERVERS.append({
        'urls': os.environ['WEBRTC_TURN_URL'],
        'username': os.getenv('WEBRTC_TURN_USERNAME', ''),
        'credential': os.getenv('WEBRTC_TURN_CREDENTIAL', ''),
    })


# ==================================================
# التطبيقات
# ==================================================

INSTALLED_APPS = [
    # تطبيقات Django الأساسية
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',

    # الملفات الثابتة
    'django.contrib.staticfiles',

    # Cloudinary
    'cloudinary_storage',
    'cloudinary',

    # تطبيقات HourBank
    'accounts.apps.AccountsConfig',
    'skills.apps.SkillsConfig',
    'marketplace.apps.MarketplaceConfig',
    'exchanges.apps.ExchangesConfig',
    'wallet.apps.WalletConfig',
    'communications.apps.CommunicationsConfig',
]


# ==================================================
# Middleware
# ==================================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',

    # دعم اللغة والترجمة
    'django.middleware.locale.LocaleMiddleware',

    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# ==================================================
# الروابط الرئيسية
# ==================================================

ROOT_URLCONF = 'HourBank.urls'


# ==================================================
# القوالب Templates
# ==================================================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',

        'DIRS': [
            BASE_DIR / 'templates',
        ],

        'APP_DIRS': True,

        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'HourBank.context_processors.site_contact',
                'communications.context_processors.unread_messages',
                'exchanges.context_processors.unseen_exchange_requests',
            ],
        },
    },
]


# ==================================================
# WSGI
# ==================================================

WSGI_APPLICATION = 'HourBank.wsgi.application'


# ==================================================
# قاعدة البيانات Supabase PostgreSQL
# ==================================================

DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600,
        ssl_require=True,
    )
}


# ==================================================
# التحقق من كلمات المرور
# ==================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': (
            'django.contrib.auth.password_validation.'
            'UserAttributeSimilarityValidator'
        ),
    },
    {
        'NAME': (
            'django.contrib.auth.password_validation.'
            'MinimumLengthValidator'
        ),
    },
    {
        'NAME': (
            'django.contrib.auth.password_validation.'
            'CommonPasswordValidator'
        ),
    },
    {
        'NAME': (
            'django.contrib.auth.password_validation.'
            'NumericPasswordValidator'
        ),
    },
]


# ==================================================
# اللغة والتوقيت
# ==================================================

LANGUAGE_CODE = 'ar'

LANGUAGES = [
    ('ar', 'Arabic'),
    ('en', 'English'),
]

LOCALE_PATHS = [BASE_DIR / 'locale']

TIME_ZONE = 'Asia/Riyadh'

USE_I18N = True

USE_TZ = True


# ==================================================
# الملفات الثابتة Static
# ==================================================

STATIC_URL = '/static/'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

STATIC_ROOT = BASE_DIR / 'staticfiles'


# ==================================================
# إعدادات Cloudinary
# ==================================================

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ['CLOUDINARY_CLOUD_NAME'],
    'API_KEY': os.environ['CLOUDINARY_API_KEY'],
    'API_SECRET': os.environ['CLOUDINARY_API_SECRET'],
    'SECURE': True,
}


# ==================================================
# نظام التخزين
# ==================================================

STORAGES = {
    # ملفات Media المرفوعة من المستخدمين
    'default': {
        'BACKEND': (
            'cloudinary_storage.storage.'
            'MediaCloudinaryStorage'
        ),
    },

    # ملفات Static
    'staticfiles': {
        'BACKEND': (
            'whitenoise.storage.'
            'CompressedManifestStaticFilesStorage'
        ),
    },
}


# ==================================================
# ملفات المستخدمين Media
# ==================================================

MEDIA_URL = '/media/'

MEDIA_ROOT = BASE_DIR / 'media'


# ==================================================
# البريد الإلكتروني
# ==================================================

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True

EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER)


# ==================================================
# نوع المفتاح الافتراضي للنماذج
# ==================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
