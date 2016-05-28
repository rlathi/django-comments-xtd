import hashlib
import urllib

from django import template
from django.contrib.staticfiles.storage import staticfiles_storage
from django.utils.safestring import mark_safe


register = template.Library()


# return only the URL of the gravatar
# TEMPLATE USE:  {{ email|gravatar_url:150 }}
@register.filter
def gravatar_url(email, size=48):
    # default = staticfiles_storage.url("img/64x64.svg")
    return ("http://www.gravatar.com/avatar/%s?%s&d=mm" %
            (hashlib.md5(email.lower().encode('utf-8')).hexdigest(),
             urllib.parse.urlencode({'s':str(size)})))


# return an image tag with the gravatar
# TEMPLATE USE:  {{ email|gravatar:150 }}
@register.filter
def gravatar(email, size=48):
    url = gravatar_url(email, size)
    return mark_safe('<img src="%s" height="%d" width="%d">' %
                     (url, size, size))
