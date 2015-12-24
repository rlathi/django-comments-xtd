from django_comments_xtd.conf import settings

from django.apps import apps
from django.utils.module_loading import import_string


default_app_config = 'django_comments_xtd.apps.CommentsXtdConfig'

    
def get_model():
    return import_string(settings.COMMENTS_XTD_MODEL)

def get_form():
    return import_string(settings.COMMENTS_XTD_FORM_CLASS)

VERSION = (1, 5, 0, 'f', 0) # following PEP 440

def get_version():
    version = '%s.%s' % (VERSION[0], VERSION[1])
    if VERSION[2]:
        version = '%s.%s' % (version, VERSION[2])
    if VERSION[3] != 'f':
        version = '%s%s%s' % (version, VERSION[3], VERSION[4])
    return version
