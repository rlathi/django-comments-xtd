#-*- coding: utf-8 -*-
from django.conf.urls import include, url
from django.views import generic

import django_comments.urls

from django_comments_xtd import views
from django_comments_xtd.conf import settings


urlpatterns = [
    url(r'', include(django_comments.urls)),
    url(r'^post/ajax$',
        views.post_comment_ajax, name='comments-xtd-post-ajax'),
    url(r'^sent/$',
        views.sent, name='comments-xtd-sent'),
    url(r'^confirm/(?P<key>[^/]+)$',
        views.confirm, name='comments-xtd-confirm'),
    url(r'^edit-followup/(?P<key>[^/]+)$',
        views.followup, name='comments-xtd-edit-followup'),
    url(r'^checkout/(?P<key>[^/]+)$',
        views.checkout, name='comments-xtd-checkout'),
    url(r'discarded/$',
        views.discarded, name='comments-xtd-discarded'),
]

if settings.COMMENTS_XTD_MAX_THREAD_LEVEL > 0:
    urlpatterns.extend([
        url(r'^reply/(?P<cid>[\d]+)$',
            views.reply, name='comments-xtd-reply'),
        url(r'^reply/(?P<cid>[\d]+)/ajax$',
            views.reply_ajax, name='comments-xtd-reply-ajax')])
