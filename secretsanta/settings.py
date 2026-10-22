from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# fine for local use, change this and turn DEBUG off before deploying
SECRET_KEY = "dev-key-change-me"
DEBUG = True
ALLOWED_HOSTS = []

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "santa",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]

ROOT_URLCONF = "secretsanta.urls"
WSGI_APPLICATION = "secretsanta.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
TIME_ZONE = "Asia/Kolkata"
USE_TZ = True

# the draw refuses to run with fewer people than this
MIN_PARTICIPANTS = 3
MAX_WISHLIST_LENGTH = 500
