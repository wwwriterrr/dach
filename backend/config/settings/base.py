"""
Базовые настройки. Общие для всех окружений.
Окружение выбирается переменной DJANGO_SETTINGS_MODULE (см. config/settings/dev.py, prod.py).
"""

import os
from pathlib import Path

# backend/config/settings/base.py -> backend/
BASE_DIR = Path(__file__).resolve().parent.parent.parent
# корень репозитория (там лежит docker-compose.yml)
REPO_ROOT = BASE_DIR.parent


def env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None:
        raise RuntimeError(f"Не задана обязательная переменная окружения: {name}")
    return value


def env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


SECRET_KEY = env("DJANGO_SECRET_KEY", "insecure-dev-key-change-me")
DEBUG = env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    # third-party
    "django_vite",
    "rest_framework",
    # local
    "apps.core",
    "apps.pedigree",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

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

# --- база данных ---------------------------------------------------------
# Postgres обязателен: рекурсивные CTE для родословных, pg_trgm для поиска,
# ArrayField/JSONB в моделях. SQLite здесь не подойдёт даже для тестов.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", "dachs"),
        "USER": env("POSTGRES_USER", "dachs"),
        "PASSWORD": env("POSTGRES_PASSWORD", "dachs"),
        "HOST": env("POSTGRES_HOST", "127.0.0.1"),
        "PORT": env("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {"connect_timeout": 5},
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Порядок важен: первый хешер используется для новых паролей.
# Наследие Drupal 6 (голый MD5) добавим отдельным классом на этапе миграции
# пользователей — Django перехеширует пароль в PBKDF2 при первом успешном входе.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

# --- локализация ---------------------------------------------------------
LANGUAGE_CODE = "ru"
LANGUAGES = [("ru", "Русский"), ("en", "English")]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# --- статика и медиа -----------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = REPO_ROOT / "var" / "static"
STATICFILES_DIRS = [
    # сюда Vite кладёт собранный бандл (см. frontend/vite.config.ts)
    BASE_DIR / "frontend_dist",
    # статика, которую отдаёт сам Django: логотипы, иконки, favicon.
    # Через Vite их гнать незачем — они нужны шаблонам, а не островам,
    # и шаблон не достанет хешированное имя из манифеста.
    BASE_DIR / "static",
]

MEDIA_URL = "/media/"
MEDIA_ROOT = REPO_ROOT / "var" / "media"

# --- Vite / React-острова ------------------------------------------------
DJANGO_VITE = {
    "default": {
        "dev_mode": env_bool("DJANGO_VITE_DEV_MODE", False),
        "dev_server_host": env("DJANGO_VITE_DEV_HOST", "localhost"),
        "dev_server_port": int(env("DJANGO_VITE_DEV_PORT", "5173")),
        "manifest_path": BASE_DIR / "frontend_dist" / ".vite" / "manifest.json",
    }
}

# --- Celery --------------------------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", "redis://127.0.0.1:6379/1")
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_TIMEZONE = TIME_ZONE

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "{levelname} {asctime} {name} {message}", "style": "{"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "root": {"handlers": ["console"], "level": env("DJANGO_LOG_LEVEL", "INFO")},
}
