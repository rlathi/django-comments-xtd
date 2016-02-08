from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from django_comments.feeds import LatestCommentFeed

from simple_threads.views import homepage_v


admin.autodiscover()


urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^articles/', include('simple_threads.articles.urls')),
    url(r'^comments/', include('django_comments_xtd.urls')),
    url(r'^$', homepage_v, name='homepage'),
    url(r'^feeds/comments/$', LatestCommentFeed(), name='comments-feed'),    
]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
