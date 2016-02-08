#-*- coding: utf-8 -*-
from __future__ import unicode_literals

import os

PRJ_PATH = os.path.abspath(os.path.curdir)

DEBUG = True

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.sqlite3', 
        'NAME':     'django_comments_xtd_test',
        'USER':     '', 
        'PASSWORD': '', 
        'HOST':     '', 
        'PORT':     '',
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Berlin'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

STATIC_URL = '/static/'

SECRET_KEY = 'v2824l&2-n+4zznbsk9c-ap5i)b3e8b+%*a=dxqlahm^%)68jn'

MIDDLEWARE_CLASSES = (
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',    
)

ROOT_URLCONF = 'django_comments_xtd.tests.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
	'DIRS': [
	    os.path.join(os.path.dirname(__file__), "templates"),
	    os.path.join(os.path.dirname(__file__), "..", "templates"),
	],
        'APP_DIRS': True,
	'OPTIONS': {
	    'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
	    ],
	},
    },
]

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django_comments',
    'django_comments_xtd',
    'django_comments_xtd.tests.apps.CommentsXtdTestsConfig',
]

COMMENTS_APP = "django_comments_xtd"

COMMENTS_XTD_CONFIRM_EMAIL = True
COMMENTS_XTD_SALT = b"es-war-einmal-una-bella-princesa-in-a-beautiful-castle"
COMMENTS_XTD_MAX_THREAD_LEVEL = 2
COMMENTS_XTD_MAX_THREAD_LEVEL_BY_APP_MODEL = {'tests.diary': 0}


