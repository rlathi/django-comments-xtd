#-*- coding: utf-8 -*-

from django.conf.urls import include, url
from django.views import generic

import django_comments.urls

from django_comments_xtd.views import sent, confirm, mute, reply
from django_comments_xtd.conf import settings


urlpatterns = [
    url(r'', include(django_comments.urls)),
    url(r'^sent/$', sent, name='comments-xtd-sent'),
    url(r'^confirm/(?P<key>[^/]+)$', confirm, name='comments-xtd-confirm'),
    url(r'^mute/(?P<key>[^/]+)$', mute, name='comments-xtd-mute'),
]

if settings.COMMENTS_XTD_MAX_THREAD_LEVEL > 0:
    urlpatterns.append(
        url(r'^reply/(?P<cid>[\d]+)$', reply, name='comments-xtd-reply'))
