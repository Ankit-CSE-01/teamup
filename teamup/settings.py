import os
from pathlib import Path
from django.contrib.messages import constants as messages
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-teamup-int253-course-project-key-2026",
)

# Toggle DEBUG via environment variable (defaults to True for local development).
# Note: To preview custom 404.html and 403.html templates in the browser,
# run with DJANGO_DEBUG=False and pass --insecure to runserver so static files load:
# DJANGO_DEBUG=False python manage.py runserver --insecure
DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() in ("true", "1", "yes")

ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]

# Support Render external hostname (e.g. teamup-xxxx.onrender.com)
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# Additional custom allowed hosts from environment
env_allowed_hosts = os.environ.get("ALLOWED_HOSTS")
if env_allowed_hosts:
    ALLOWED_HOSTS.extend([h.strip() for h in env_allowed_hosts.split(",") if h.strip()])

CSRF_TRUSTED_ORIGINS = [
    "https://*.onrender.com",
    "http://127.0.0.1:8001",
    "http://localhost:8001",
]
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Local apps
    "accounts.apps.AccountsConfig",
    "projects.apps.ProjectsConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ---------------------------------------------------------------------------
# HOW TO USE DJANGO DEBUG TOOLBAR (Unit VI Debugging & Profiling):
# 1. Run: pip install django-debug-toolbar
# 2. Add "debug_toolbar" to INSTALLED_APPS above.
# 3. Add "debug_toolbar.middleware.DebugToolbarMiddleware" to MIDDLEWARE.
# 4. Add INTERNAL_IPS = ["127.0.0.1"] below.
# 5. In teamup/urls.py, append path("__debug__/", include("debug_toolbar.urls"))
#    when settings.DEBUG is True.
# ---------------------------------------------------------------------------

ROOT_URLCONF = "teamup.urls"

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

WSGI_APPLICATION = "teamup.wsgi.application"

database_url = os.environ.get("DATABASE_URL")
if database_url:
    DATABASES = {
        "default": dj_database_url.config(
            default=database_url,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# WhiteNoise production compressed static file storage
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "projects:dashboard"
LOGOUT_REDIRECT_URL = "projects:project_list"

MESSAGE_TAGS = {
    messages.DEBUG: "info",
    messages.INFO: "info",
    messages.SUCCESS: "success",
    messages.WARNING: "warning",
    messages.ERROR: "danger",
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# EMAIL CONFIGURATION (Development Console Backend)
# ---------------------------------------------------------------------------
EMAIL_BACKEND = os.environ.get(
    "DJANGO_EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)
DEFAULT_FROM_EMAIL = "TeamUp CSE Collab <noreply@teamup.univ.edu>"
