SECRET_KEY = "test-secret-key-for-integration-tests-only"

DEBUG = False

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
]

ROOT_URLCONF = "urls"

WSGI_APPLICATION = "wsgi.application"

DATABASES = {}

# Configure logging at DEBUG via Django's LOGGING setting (applied through dictConfig).
# Under instrumentation the agent must preserve this level.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"level": "DEBUG", "handlers": ["console"]},
}
