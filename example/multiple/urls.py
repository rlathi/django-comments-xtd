from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from django_comments.feeds import LatestCommentFeed

import multiple.views


admin.autodiscover()

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^blog/', include('multiple.blog.urls')),
    url(r'^projects/', include('multiple.projects.urls')),
    url(r'^comments/', include('django_comments_xtd.urls')),
    url(r'^$', multiple.views.homepage_v, name='homepage'),
    url(r'^feeds/comments/$', LatestCommentFeed(), name='comments-feed'),
]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
