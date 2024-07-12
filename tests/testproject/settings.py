import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SECRET_KEY = "02^5l2jh+t-)3#+9!7&^5n0c#&o(ararue&=gj(*b02pk)i9(#"
DEBUG = True
ALLOWED_HOSTS = []

USE_TZ = True

# Application definition
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django_safemigrate.apps.SafeMigrateConfig",
]
MIDDLEWARE = []
ROOT_URLCONF = "testproject.urls"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.{}".format(os.getenv("DB_BACKEND", "sqlite3")),
        "NAME": os.getenv("DB_NAME", ":memory:"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST", ""),
        "PORT": os.getenv("DB_PORT", ""),
        "TEST": {
            "USER": "default_test",
        },
    },
}
