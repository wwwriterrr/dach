"""Разработка: DEBUG, Vite dev-server с HMR, отладочная панель."""

from .base import *  # noqa: F403
from .base import INSTALLED_APPS, MIDDLEWARE, env_bool

DEBUG = True
ALLOWED_HOSTS = ["*"]

DJANGO_VITE["default"]["dev_mode"] = env_bool("DJANGO_VITE_DEV_MODE", True)  # noqa: F405

if env_bool("DJANGO_DEBUG_TOOLBAR", False):
    INSTALLED_APPS += ["debug_toolbar"]
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
    INTERNAL_IPS = ["127.0.0.1"]
    # в контейнере IP клиента — не 127.0.0.1, поэтому показываем панель всегда
    DEBUG_TOOLBAR_CONFIG = {"SHOW_TOOLBAR_CALLBACK": lambda request: True}

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
