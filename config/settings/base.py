from pathlib import Path
import os
from urllib.parse import quote_plus

import dj_database_url
from corsheaders.defaults import default_headers
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# BASE_DIR is now three levels up: config/settings/base.py -> config/settings/ -> config/ -> Kinaadman-be/
BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def env_list(name: str) -> list[str]:
    raw = os.environ.get(name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def env_int(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


def get_default_database_url() -> str:
    db_name = os.environ.get("DB_NAME", "kinaadman_db")
    db_user = os.environ.get("DB_USER", "postgres")
    db_password = quote_plus(os.environ.get("DB_PASSWORD", "qwerty"))
    db_host = os.environ.get("DB_HOST", "localhost")
    db_port = os.environ.get("DB_PORT", "5432")

    return (
        f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    )


# Quick-start development settings - unsuitable for production
SECRET_KEY = os.environ.get("SECRET_KEY", "default-insecure-key")

DEBUG = env_bool("DEBUG", False)

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS")
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "").strip()
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

if DEBUG:
    for host in ("localhost", "127.0.0.1", "[::1]"):
        if host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(host)

# CORS settings
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")
CORS_ALLOW_HEADERS = list(default_headers) + [
    "x-tenant-id",
]

# Application definition
INSTALLED_APPS = [
    "unfold",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",

    # Third party
    "rest_framework",
    "corsheaders",
    "ninja",

    # Local apps
    "core",
    "apps.tenants",
    "apps.users",
    "apps.authentication",
    "apps.repository",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "core" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Database
DATABASES = {
    "default": dj_database_url.config(
        default=os.environ.get("DATABASE_URL", get_default_database_url()),
        conn_max_age=env_int("DATABASE_CONN_MAX_AGE", 600),
        conn_health_checks=True,
    ),
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

AUTH_USER_MODEL = "users.User"
AUTHENTICATION_BACKENDS = ["apps.users.backends.EmailBackend"]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Authentication Redirects
LOGIN_URL = "admin:login"
LOGIN_REDIRECT_URL = "admin:index"
LOGOUT_REDIRECT_URL = "admin:login"

# Static files
STATIC_URL = "/static/"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Media files
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

from django.templatetags.static import static
from django.urls import reverse_lazy

UNFOLD = {
    "SITE_TITLE": "Kinaadman",
    "SITE_HEADER": "Kinaadman Dashboard",
    "SITE_URL": "/",
    "STYLES": [
        lambda request: static("css/admin_custom.css"),
    ],
    "SITE_ICON": {
        "light": lambda request: static("icon-light.png") + "?v=2",  # light mode
        "dark": lambda request: static("icon-dark.png") + "?v=2",  # dark mode
    },
    "SITE_FAVICONS": [
        {
            "rel": "icon",
            "href": lambda request: static("icon-light.png") + "?v=2",
        }
    ],
    # "SITE_LOGO": {
    #     "light": lambda request: static("logo-light.svg"),  # light mode
    #     "dark": lambda request: static("logo-dark.svg"),  # dark mode
    # },
    "SITE_SYMBOL": "speed",
    "COLORS": {
        "primary": {
            "50": "242 246 249",
            "100": "223 232 239",
            "200": "191 209 223",
            "300": "153 181 204",
            "400": "109 146 179",
            "500": "75 116 153",
            "600": "56 90 122",
            "700": "45 72 99",
            "800": "38 61 84",
            "900": "15 42 68",
            "950": "10 26 43",
        },
    },
    "COMMAND": {
        "search_models": True,
        "show_history": True,
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "command_search": True,
        "navigation": [
            {
                "title": "Tenants",
                "separator": True,
                "items": [
                    {
                        "title": "Tenants",
                        "icon": "business",
                        "link": reverse_lazy("admin:tenants_tenant_changelist"),
                    },
                ],
            },
            {
                "title": "Users",
                "separator": True,
                "items": [
                    {
                        "title": "Users",
                        "icon": "people",
                        "link": reverse_lazy("admin:users_user_changelist"),
                    },
                    {
                        "title": "Tenant Memberships",
                        "icon": "card_membership",
                        "link": reverse_lazy("admin:users_tenantmembership_changelist"),
                    },
                ],
            },
            {
                "title": "Authentication",
                "separator": True,
                "items": [
                    {
                        "title": "Auth Sessions",
                        "icon": "computer",
                        "link": reverse_lazy("admin:authentication_authsession_changelist"),
                    },
                    {
                        "title": "Auth Events",
                        "icon": "history",
                        "link": reverse_lazy("admin:authentication_authevent_changelist"),
                    },
                ],
            },
        ],
    },
}
