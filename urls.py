from django.conf.urls.defaults import patterns, include, url
import swap
from swap import views

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'cssswap.views.home', name='home'),
    # url(r'^cssswap/', include('cssswap.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    url(r'^/?$', swap.views.index),
    url(r'^getpage/?$', swap.views.getpage),
    url(r'^editpage/(?P<page_id>\d+)/?', swap.views.editpage),
    url(r'^savepage/(?P<page_id>\d+)/?', swap.views.savepage),
    url(r'^previewpage/(?P<page_id>\d+)/?', swap.views.previewpage),
    url(r'^showpage/(?P<page_id>\d+)/?', swap.views.showpage),

    #get CSS by UUID
    url(r'^css/(?P<uuid>[0-f]+)/?', swap.views.getCSS),
    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)
