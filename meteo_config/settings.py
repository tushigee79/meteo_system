import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-your-secret-key"
DEBUG = True
ALLOWED_HOSTS = ["*"]
DASHBOARD_USE_MOCK = True
DASHBOARD_USE_MOCK = False


INSTALLED_APPS = [
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "inventory.apps.InventoryConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "inventory.middleware.ForcePasswordChangeMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "meteo_config.urls"

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

WSGI_APPLICATION = "meteo_config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LANGUAGE_CODE = "mn"
TIME_ZONE = "Asia/Ulaanbaatar"
USE_I18N = True
USE_TZ = True

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "/django-admin/login/"
LOGIN_REDIRECT_URL = "/django-admin/"

STATIC_URL = "/static/"
STATICFILES_DIRS = [
    BASE_DIR / "static",
    BASE_DIR / "inventory" / "static",
]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# =========================================================
# JAZZMIN
# =========================================================
JAZZMIN_SETTINGS = {
    "site_title": "БҮРТГЭЛ",
    "site_header": "Ус, Цаг Уурын Систем",
    "site_brand": "БҮРТГЭЛ",
    "welcome_sign": "БҮРТГЭЛ админ удирдлага",
    "copyright": "ЦУОШГ",

    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": [],
    "hide_models": [],

    "theme": "cosmo",

    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.group": "fas fa-users",

        "inventory.device": "fas fa-microchip",
        "inventory.location": "fas fa-map-marker-alt",
        "inventory.organization": "fas fa-building",
        "inventory.instrumentcatalog": "fas fa-list",
        "inventory.maintenanceservice": "fas fa-tools",
        "inventory.controladjustment": "fas fa-sliders-h",
        "inventory.devicemovement": "fas fa-exchange-alt",

        "inventory.sparepartorder": "fas fa-shopping-cart",
        "inventory.authauditlog": "fas fa-user-shield",
    },

    # Sidebar: Inventory app дээр нэмэлт линкүүд
    "custom_links": {
        "inventory": [
            {
                "name": "Хүснэгт статистик",
                "url": "admin:dashboard_table",
                "icon": "fas fa-table",
                "permissions": ["inventory.view_device"],
            },
            {
                "name": "График статистик",
                "url": "admin:dashboard_graph",
                "icon": "fas fa-chart-line",
                "permissions": ["inventory.view_device"],
            },
            {
                "name": "Ерөнхий самбар",
                "url": "admin:dashboard_general",
                "icon": "fas fa-tachometer-alt",
                "permissions": ["inventory.view_device"],
            },
            {
                "name": "Өгөгдөл оруулах",
                "url": "inventory_admin:admin_data_entry",
                "icon": "fas fa-edit",
                "permissions": ["auth.view_user"],
            },
            {
                "name": "Газрын зураг",
                "url": "admin:inventory_map",
                "icon": "fas fa-map-marked-alt",
                "permissions": ["inventory.view_location"],
            },
            {
                "name": "Хүлээгдэж буй ажлууд",
                "url": "inventory_admin:workflow_pending",
                "icon": "fas fa-tasks",
                "permissions": [
                    "inventory.view_maintenanceservice",
                    "inventory.view_controladjustment",
                ],
            },
            {
                "name": "Хяналтын түүх (Audit)",
                "url": "admin:workflow_audit",
                "icon": "fas fa-clipboard-list",
                "permissions": ["inventory.view_authauditlog"],
                
            },
        ],
    },

    # 2. Top menu links
    "topmenu_links": [
        {"name": "Админ", "url": "admin:index"},
        {
            "name": "Газрын зураг",
            "url": "admin:inventory_map",  # admin: нэмэв
            "permissions": ["inventory.view_location"],
        },
        {
            "name": "Dashboard",
            "url": "admin:dashboard_table",
            "permissions": ["inventory.view_device"],
        },
        {
            "name": "График тайлан",
            "url": "admin:dashboard_graph",
            "permissions": ["inventory.view_device"],
        },
        {
            "name": "Өгөгдөл бүртгэх",
            "url": "admin:admin_data_entry",
            "permissions": ["auth.view_user"],
        },
    ],
}

# ==================================================
# Verification expiry config (admin + dashboard)
# ==================================================
VERIF_DUE_30_DAYS = 30
VERIF_DUE_90_DAYS = 90

