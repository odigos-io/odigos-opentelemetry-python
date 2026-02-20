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
