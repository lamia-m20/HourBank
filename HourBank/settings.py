"""
Django settings for HourBank project.
"""

from pathlib import Path


# ==================================================
# المسار الرئيسي للمشروع
# ==================================================

BASE_DIR = Path(__file__).resolve().parent.parent


# ==================================================
# إعدادات الأمان
# ==================================================

SECRET_KEY = 'django-insecure-2ddtxt9qfpc_fzp+1gv8+mv%04k0ge7*b^@+v-7nn30pe^+(@*'

DEBUG = True

ALLOWED_HOSTS = []


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
    'django.contrib.staticfiles',

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
            ],
        },
    },
]


# ==================================================
# WSGI
# ==================================================

WSGI_APPLICATION = 'HourBank.wsgi.application'


# ==================================================
# قاعدة البيانات SQLite
# ==================================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
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

TIME_ZONE = 'Asia/Riyadh'

USE_I18N = True

USE_TZ = True


# ==================================================
# الملفات الثابتة Static
# ==================================================

STATIC_URL = 'static/'


# ==================================================
# البريد الإلكتروني
# أثناء التطوير تظهر الرسائل في Terminal
# ==================================================

MAILERS = {
    'default': {
        'BACKEND': 'django.core.mail.backends.console.EmailBackend',
    },
}


# ==================================================
# نوع المفتاح الافتراضي للنماذج
# ==================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'