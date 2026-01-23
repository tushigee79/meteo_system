import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = 'django-insecure-your-secret-key'
DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'inventory.apps.InventoryConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'inventory.middleware.ForcePasswordChangeMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'meteo_config.urls'

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LANGUAGE_CODE = 'mn'
TIME_ZONE = 'Asia/Ulaanbaatar'
USE_I18N = True
USE_TZ = True

# Password policy
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "/django-admin/login/"
LOGIN_REDIRECT_URL = "/django-admin/"

# =========================
# Static & Media (FINAL)
# =========================
STATIC_URL = "/static/"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# =========================
# Jazzmin
# =========================
JAZZMIN_SETTINGS = {
    "site_title": "NAMEM Багаж Хяналт",
    "site_header": "NAMEM",
    "site_brand": "Ус, Цаг Уурын Систем",
    "copyright": "NAMEM 2026",
    "search_model": ["inventory.Device"],
    "show_sidebar": True,
    "navigation_expanded": True,

    "base_url": "/django-admin/",

    "custom_js": "js/admin_sidebar_link.js",

    "use_google_fonts": True,
    "icons": {
        "auth": "fas fa-users-cog",
        "inventory.Location": "fas fa-map-marker-alt",
        "inventory.Device": "fas fa-tools",
        "inventory.SparePartOrder": "fas fa-shopping-cart",
    },

    "custom_links": {
        "Inventory": [
            {"name": "Dashboard (Хүснэгт)", "url": "/admin/dashboard/table/", "icon": "fas fa-table"},
            {"name": "Dashboard (График)", "url": "/admin/dashboard/graph/", "icon": "fas fa-chart-bar"},
        ]
    },

    "custom_links_top": [
        {
            "name": "Админ хэсэг",
            "url": "/django-admin/",
            "icon": "fas fa-user-shield",
            "permissions": [],
        }
    ],
}
