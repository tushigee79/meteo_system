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

    # Sidebar: Inventory апп дээр нэмэлт линкүүд
    "custom_links": {
        "inventory": [
            {
                "name": "Dashboard (Нүүр)",
                "url": "admin:dashboard_home",
                "icon": "fas fa-tachometer-alt",
                "permissions": ["inventory.view_location"],
            },
            {
                "name": "Өгөгдөл бүртгэх (Админ)",
                "url": "admin:admin_data_entry",
                "icon": "fas fa-database",
                "permissions": ["auth.view_user"],
            },
            {
                "name": "Dashboard (Хүснэгт)",
                "url": "admin:dashboard_table",
                "icon": "fas fa-table",
                "permissions": ["inventory.view_device"],
            },
            {
                "name": "Dashboard (График)",
                "url": "admin:dashboard_graph",
                "icon": "fas fa-chart-bar",
                "permissions": ["inventory.view_device"],
            },
            {
                "name": "Газрын зураг",
                "url": "inventory_map",
                "icon": "fas fa-map-marked-alt",
                "permissions": ["inventory.view_location"],
            },
            {
                "name": "Хүлээгдэж буй ажлууд",
                "url": "admin:workflow_pending",
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
            {
                "name": "📊 Тайлан (Reports)",
                "url": "admin:reports_hub",
                "icon": "fas fa-chart-pie",
                "permissions": ["inventory.view_device"],
            },
            {
                "name": "📌 Ерөнхий мэдээлэл",
                "url": "admin:dashboard_general",
                "icon": "fas fa-info-circle",
                "permissions": ["inventory.view_device"],
            },
        ],
    },

    # Top menu: давхардалгүй, зөвхөн “гол” линкүүд
    "topmenu_links": [
        {"name": "Админ", "url": "admin:index"},
        {"name": "Газрын зураг", "url": "inventory_map", "permissions": ["inventory.view_location"]},
        {"name": "Dashboard", "url": "admin:dashboard_table", "permissions": ["inventory.view_device"]},
        {"name": "График тайлан", "url": "admin:dashboard_graph", "permissions": ["inventory.view_device"]},
        {"name": "Өгөгдөл бүртгэх", "url": "admin:admin_data_entry", "permissions": ["auth.view_user"]},
        {"name": "Reports", "url": "admin:reports_hub", "permissions": ["inventory.view_device"]},
    ],
}

# ✅ Clickjacking / Leaflet admin map iframe зөвшөөрөх
X_FRAME_OPTIONS = "SAMEORIGIN"


# ==================================================
# Verification expiry config (admin + dashboard)
# ==================================================
VERIF_DUE_30_DAYS = 30
VERIF_DUE_90_DAYS = 90

