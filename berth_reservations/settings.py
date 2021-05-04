import os
import subprocess

import environ
import sentry_sdk
from django.utils.translation import gettext_lazy as _
from sentry_sdk.integrations.django import DjangoIntegration

checkout_dir = environ.Path(__file__) - 2
assert os.path.exists(checkout_dir("manage.py"))

parent_dir = checkout_dir.path("..")
if os.path.isdir(parent_dir("etc")):
    env_file = parent_dir("etc/env")
    default_var_root = environ.Path(parent_dir("var"))
else:
    env_file = checkout_dir(".env")
    default_var_root = environ.Path(checkout_dir("var"))

env = environ.Env(
    DEBUG=(bool, False),
    TIER=(str, "dev"),  # one of: prod, qa, stage, test, dev
    SECRET_KEY=(str, ""),
    MEDIA_ROOT=(environ.Path(), default_var_root("media")),
    STATIC_ROOT=(environ.Path(), default_var_root("static")),
    MEDIA_URL=(str, "/media/"),
    STATIC_URL=(str, "/static/"),
    ALLOWED_HOSTS=(list, []),
    DATABASE_URL=(
        str,
        "postgis://berth_reservations:berth_reservations@localhost/berth_reservations",
    ),
    DATABASE_CONN_MAX_AGE=(int, 60 * 60),  # 60 min
    CACHE_URL=(str, "locmemcache://"),
    MAILER_EMAIL_BACKEND=(str, "django.core.mail.backends.console.EmailBackend"),
    DEFAULT_FROM_EMAIL=(str, "venepaikkavaraukset@hel.fi"),
    MAIL_MAILGUN_KEY=(str, ""),
    MAIL_MAILGUN_DOMAIN=(str, ""),
    MAIL_MAILGUN_API=(str, ""),
    SENTRY_DSN=(str, ""),
    SENTRY_ENVIRONMENT=(str, ""),
    CORS_ORIGIN_WHITELIST=(list, []),
    CORS_ORIGIN_ALLOW_ALL=(bool, False),
    NOTIFICATIONS_ENABLED=(bool, False),
    ORDER_EXPIRATION_CRONJOB_ENABLED=(bool, False),
    OFFER_EXPIRATION_CRONJOB_ENABLED=(bool, False),
    TOKEN_AUTH_ACCEPTED_AUDIENCE=(str, "https://api.hel.fi/auth/berths"),
    TOKEN_AUTH_ACCEPTED_SCOPE_PREFIX=(str, "berths"),
    TOKEN_AUTH_AUTHSERVER_URL=(str, ""),
    TOKEN_AUTH_FIELD_FOR_CONSENTS=(str, "https://api.hel.fi/auth"),
    TOKEN_AUTH_REQUIRE_SCOPE_PREFIX=(bool, True),
    VENE_PAYMENTS_PROVIDER_CLASS=(str, "payments.providers.BamboraPayformProvider"),
    VENE_CONTRACTS_SERVICE_CLASS=(str, "contracts.services.VismaContractService"),
    VENE_UI_RETURN_URL=(str, "https://venepaikat.hel.fi/"),
    VENE_UI_URL=(str, "https://venepaikat.hel.fi"),
    FORCE_SCRIPT_NAME=(str, ""),
    CSRF_COOKIE_NAME=(str, ""),
    CSRF_COOKIE_PATH=(str, ""),
    CSRF_COOKIE_SECURE=(bool, None),
    SESSION_COOKIE_NAME=(str, ""),
    SESSION_COOKIE_PATH=(str, ""),
    SESSION_COOKIE_SECURE=(bool, None),
    USE_X_FORWARDED_HOST=(bool, False),
    CSRF_TRUSTED_ORIGINS=(list, []),
    FORCED_HOST=(str, None),
    ENABLE_APM_TOOLS=(bool, False),
    ENABLE_PROFILING_TOOLS=(bool, False),
)
if os.path.exists(env_file):
    env.read_env(env_file)

BASE_DIR = str(checkout_dir)

DEBUG = env.bool("DEBUG")
TIER = env.str("TIER")
SECRET_KEY = env.str("SECRET_KEY")
if DEBUG and not SECRET_KEY:
    SECRET_KEY = "xxx"

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
USE_X_FORWARDED_HOST = env.bool("USE_X_FORWARDED_HOST")

REQUEST_LOGGER_IGNORE_PATHS = (
    "/healthz",
    "/readiness",
    "/static",
)

if env("CSRF_TRUSTED_ORIGINS"):
    CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS")

if env.str("FORCE_SCRIPT_NAME"):
    FORCE_SCRIPT_NAME = env.str("FORCE_SCRIPT_NAME")
    REQUEST_LOGGER_IGNORE_PATHS = tuple(
        f"{FORCE_SCRIPT_NAME}{path}" for path in REQUEST_LOGGER_IGNORE_PATHS
    )

DATABASES = {"default": env.db()}
# Ensure postgis engine
DATABASES["default"]["ENGINE"] = "django.contrib.gis.db.backends.postgis"
# Configure the age of DB connections
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DATABASE_CONN_MAX_AGE")

CACHES = {"default": env.cache()}

DEFAULT_FROM_EMAIL = env.str("DEFAULT_FROM_EMAIL")
if env("MAIL_MAILGUN_KEY"):
    ANYMAIL = {
        "MAILGUN_API_KEY": env("MAIL_MAILGUN_KEY"),
        "MAILGUN_SENDER_DOMAIN": env("MAIL_MAILGUN_DOMAIN"),
        "MAILGUN_API_URL": env("MAIL_MAILGUN_API"),
    }

EMAIL_BACKEND = "mailer.backend.DbBackend"
MAILER_EMAIL_BACKEND = env.str("MAILER_EMAIL_BACKEND")

try:
    version = subprocess.check_output(
        ["git", "describe"], stderr=subprocess.STDOUT
    ).strip()
except Exception:
    version = "n/a"

sentry_sdk.init(
    dsn=env.str("SENTRY_DSN"),
    release=version,
    environment=env("SENTRY_ENVIRONMENT"),
    integrations=[DjangoIntegration()],
)
sentry_sdk.integrations.logging.ignore_logger("graphql.execution.utils")

MEDIA_ROOT = env("MEDIA_ROOT")
STATIC_ROOT = env("STATIC_ROOT")
MEDIA_URL = env.str("MEDIA_URL")
STATIC_URL = env.str("STATIC_URL")

ROOT_URLCONF = "berth_reservations.urls"
WSGI_APPLICATION = "berth_reservations.wsgi.application"

LANGUAGE_CODE = "fi"
LANGUAGES = (("fi", _("Finnish")), ("en", _("English")), ("sv", _("Swedish")))
TIME_ZONE = "Europe/Helsinki"
USE_I18N = True
USE_L10N = True
USE_TZ = True

LOCALE_PATHS = (os.path.join(BASE_DIR, "locale"),)

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    "helusers",
    "helusers.apps.HelusersAdminConfig",
    "django_filters",
    "corsheaders",
    "parler",
    "anymail",
    "mptt",
    "munigeo",
    "mailer",
    "graphene_django",
    "django_ilmoitin",
    "silk",
    # Local apps
    "users",
    "customers",
    "applications",
    "harbors",
    "resources",
    "leases",
    "payments",
    "contracts",
]

AUTH_USER_MODEL = "users.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "berth_reservations.logging.RequestLogger",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "berth_reservations.oidc.GraphQLApiTokenAuthentication",
]

SITE_ID = 1

DEFAULT_SRID = 4326

NOTIFICATIONS_ENABLED = env("NOTIFICATIONS_ENABLED")
ORDER_EXPIRATION_CRONJOB_ENABLED = env("ORDER_EXPIRATION_CRONJOB_ENABLED")
OFFER_EXPIRATION_CRONJOB_ENABLED = env("OFFER_EXPIRATION_CRONJOB_ENABLED")

PARLER_LANGUAGES = {SITE_ID: ({"code": "fi"}, {"code": "en"}, {"code": "sv"})}
PARLER_DEFAULT_ACTIVATE = True

CORS_ORIGIN_WHITELIST = env.list("CORS_ORIGIN_WHITELIST")
CORS_ORIGIN_ALLOW_ALL = env.bool("CORS_ORIGIN_ALLOW_ALL")

OIDC_API_TOKEN_AUTH = {
    "AUDIENCE": env.str("TOKEN_AUTH_ACCEPTED_AUDIENCE"),
    "API_SCOPE_PREFIX": env.str("TOKEN_AUTH_ACCEPTED_SCOPE_PREFIX"),
    "ISSUER": env.str("TOKEN_AUTH_AUTHSERVER_URL"),
    "API_AUTHORIZATION_FIELD": env.str("TOKEN_AUTH_FIELD_FOR_CONSENTS"),
    "REQUIRE_API_SCOPE_FOR_AUTHENTICATION": env.bool("TOKEN_AUTH_REQUIRE_SCOPE_PREFIX"),
}

OIDC_AUTH = {"OIDC_LEEWAY": 60 * 60}

GRAPHENE = {
    "SCHEMA": "berth_reservations.schema.schema",
    "MIDDLEWARE": [
        "graphql_jwt.middleware.JSONWebTokenMiddleware",
        "berth_reservations.middlewares.GQLDataLoaders",
    ],
    "RELAY_CONNECTION_MAX_LIMIT": 5000,
}

GRAPHQL_JWT = {"JWT_AUTH_HEADER_PREFIX": "Bearer"}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"django_server": {"()": "berth_reservations.logging.LogRequestFilter"}},
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "plain",
            "filters": ["django_server"],
        },
        "json": {"class": "logging.StreamHandler", "formatter": "json"},
    },
    "formatters": {
        "json": {"()": "json_log_formatter.JSONFormatter"},
        "plain": {
            "()": "django.utils.log.ServerFormatter",
            "format": "[{server_time}] {message}",
            "style": "{",
        },
    },
    "loggers": {
        "requests": {"handlers": ["json"], "level": "INFO"},
        "django": {"handlers": ["console"], "level": "INFO"},
    },
}

ENABLE_PROFILING_TOOLS = env("ENABLE_PROFILING_TOOLS")

SILKY_AUTHENTICATION = True

# Dotted path to the active payment provider class, see payments.providers init.
# Example value: 'payments.providers.BamboraPayformProvider'
VENE_PAYMENTS_PROVIDER_CLASS = env("VENE_PAYMENTS_PROVIDER_CLASS")

VENE_CONTRACTS_SERVICE_CLASS = env("VENE_CONTRACTS_SERVICE_CLASS")

VENE_UI_RETURN_URL = env("VENE_UI_RETURN_URL")

VENE_UI_URL = env("VENE_UI_URL")

if env("ENABLE_APM_TOOLS"):
    INSTALLED_APPS += ["elasticapm.contrib.django"]

if env("ENABLE_PROFILING_TOOLS"):
    MIDDLEWARE += [
        "silk.middleware.SilkyMiddleware",
    ]

if env("FORCED_HOST"):
    FORCED_HOST = env("FORCED_HOST")
    MIDDLEWARE.insert(0, "berth_reservations.middlewares.HostFixupMiddleware")

if env("CSRF_COOKIE_NAME"):
    CSRF_COOKIE_NAME = env.str("CSRF_COOKIE_NAME")

if env("CSRF_COOKIE_PATH"):
    CSRF_COOKIE_PATH = env.str("CSRF_COOKIE_PATH")

if env("CSRF_COOKIE_SECURE") is not None:
    CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE")

if env("SESSION_COOKIE_NAME"):
    SESSION_COOKIE_NAME = env.str("SESSION_COOKIE_NAME")

if env("SESSION_COOKIE_PATH"):
    SESSION_COOKIE_PATH = env.str("SESSION_COOKIE_PATH")

if env("SESSION_COOKIE_SECURE") is not None:
    SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE")

EXPIRE_WAITING_ORDERS_OLDER_THAN_DAYS = 7
EXPIRE_WAITING_OFFERS_OLDER_THAN_DAYS = 7

# local_settings.py can be used to override environment-specific settings
# like database and email that differ between development and production.
local_settings_path = os.path.join(checkout_dir(), "local_settings.py")
if os.path.exists(local_settings_path):
    with open(local_settings_path) as fp:
        code = compile(fp.read(), local_settings_path, "exec")
    exec(code, globals(), locals())
