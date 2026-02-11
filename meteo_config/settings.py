import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-your-secret-key"
DEBUG = True
ALLOWED_HOSTS = ["*"]

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
    "site_title": "Ð‘Ò®Ð Ð¢Ð“Ð­Ð›",
    "site_header": "Ð£Ñ, Ð¦Ð°Ð³ Ð£ÑƒÑ€Ñ‹Ð½ Ð¡Ð¸ÑÑ‚ÐµÐ¼",
    "site_brand": "Ð‘Ò®Ð Ð¢Ð“Ð­Ð›",
    "welcome_sign": "Ð‘Ò®Ð Ð¢Ð“Ð­Ð› Ð°Ð´Ð¼Ð¸Ð½ ÑƒÐ´Ð¸Ñ€Ð´Ð»Ð°Ð³Ð°",
    "copyright": "Ð¦Ð£ÐžÐ¨Ð“",

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

    # Sidebar: Inventory Ð°Ð¿Ð¿ Ð´ÑÑÑ€ Ð½ÑÐ¼ÑÐ»Ñ‚ Ð»Ð¸Ð½ÐºÒ¯Ò¯Ð´
    "custom_links": {
        "inventory": [
            {
                "name": "Dashboard (ÐÒ¯Ò¯Ñ€)",
                "url": "inventory_inventory_inventory_admin:dashboard_home",
                "icon": "fas fa-tachometer-alt",
                "permissions": ["inventory.view_location"],
            },
            {
                "name": "Dashboard (Ð¥Ò¯ÑÐ½ÑÐ³Ñ‚)",
                "url": "inventory_inventory_inventory_admin:dashboard_table",
                "icon": "fas fa-table",
                "permissions": ["inventory.view_device"],
            },
            {
                "name": "Ð“Ñ€Ð°Ñ„Ð¸Ðº Ñ‚Ð°Ð¹Ð»Ð°Ð½",
                "url": "inventory_inventory_inventory_admin:dashboard_graph",
                "icon": "fas fa-chart-bar",
                "permissions": ["inventory.view_device"],
            },
            {
                "name": "ðŸ“Œ Ð•Ñ€Ó©Ð½Ñ…Ð¸Ð¹ Ð¼ÑÐ´ÑÑÐ»ÑÐ»",
                "url": "inventory_inventory_inventory_admin:dashboard_general",
                "icon": "fas fa-info-circle",
                "permissions": ["inventory.view_device"],
            },
            {
                "name": "Ó¨Ð³Ó©Ð³Ð´Ó©Ð» Ð±Ò¯Ñ€Ñ‚Ð³ÑÑ… (ÐÐ´Ð¼Ð¸Ð½)",
                "url": "inventory_inventory_inventory_admin:admin_data_entry",
                "icon": "fas fa-database",
                "permissions": ["auth.view_user"],
            },
            {
                "name": "Ð“Ð°Ð·Ñ€Ñ‹Ð½ Ð·ÑƒÑ€Ð°Ð³",
                "url": "inventory:inventory_map",
                "icon": "fas fa-map-marked-alt",
                "permissions": ["inventory.view_location"],
            },
            {
                "name": "Ð¥Ò¯Ð»ÑÑÐ³Ð´ÑÐ¶ Ð±ÑƒÐ¹ Ð°Ð¶Ð»ÑƒÑƒÐ´",
                "url": "inventory_inventory_inventory_admin:workflow_pending",
                "icon": "fas fa-tasks",
                "permissions": [
                    "inventory.view_maintenanceservice",
                    "inventory.view_controladjustment",
                ],
            },
            {
                "name": "Ð¥ÑÐ½Ð°Ð»Ñ‚Ñ‹Ð½ Ñ‚Ò¯Ò¯Ñ… (Audit)",
                "url": "inventory_inventory_inventory_admin:workflow_audit",
                "icon": "fas fa-clipboard-list",
                "permissions": ["inventory.view_authauditlog"],
            },
        ],
    },

    # Top menu (custom admin site namespace Ð°ÑˆÐ¸Ð³Ð»Ð°Ð½Ð°)
    "topmenu_links": [
        {"name": "ÐÐ´Ð¼Ð¸Ð½", "url": "admin:index"},
        {"name": "Ð“Ð°Ð·Ñ€Ñ‹Ð½ Ð·ÑƒÑ€Ð°Ð³", "url": "inventory:inventory_map", "permissions": ["inventory.view_location"]},
        {"name": "Dashboard", "url": "inventory_inventory_inventory_admin:dashboard_table", "permissions": ["inventory.view_device"]},
        {"name": "Ð“Ñ€Ð°Ñ„Ð¸Ðº Ñ‚Ð°Ð¹Ð»Ð°Ð½", "url": "inventory_inventory_inventory_admin:dashboard_graph", "permissions": ["inventory.view_device"]},
        {"name": "Ó¨Ð³Ó©Ð³Ð´Ó©Ð» Ð±Ò¯Ñ€Ñ‚Ð³ÑÑ…", "url": "inventory_inventory_inventory_admin:admin_data_entry", "permissions": ["auth.view_user"]},
    ],
}

# âœ… Clickjacking / Leaflet admin map iframe Ð·Ó©Ð²ÑˆÓ©Ó©Ñ€Ó©Ñ…
X_FRAME_OPTIONS = "SAMEORIGIN"

# ==================================================
# Verification expiry config (admin + dashboard)
# ==================================================
VERIF_DUE_30_DAYS = 30
VERIF_DUE_90_DAYS = 90







