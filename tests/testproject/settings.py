import os
import dj_database_url

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SECRET_KEY = "02^5l2jh+t-)3#+9!7&^5n0c#&o(ararue&=gj(*b02pk)i9(#"
DEBUG = True
ALLOWED_HOSTS = []

USE_TZ = True

# Application definition
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django_safemigrate",
]
MIDDLEWARE = []
ROOT_URLCONF = "testproject.urls"
DATABASES = {"default": dj_database_url.config(default="sqlite:///:memory:")}
