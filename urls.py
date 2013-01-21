from django.conf.urls.defaults import *
from django.conf import settings
import os
# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('psh_manager_online',
    # Example:
    # (r'^psh_manager_online/', include('psh_manager_online.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/', include(admin.site.urls)),
    #(r'^index$', 'views.index'),
    (r'^suggest$', 'views.suggest'),
    (r'^(!#\d+)*$', 'views.index'),
    (r'^getConcept$', 'views.getConcept'),
    (r'^getID$', 'views.getID'),
    (r'^getSearchResult$', 'views.getSearchResult'),
    (r'^concept/(?P<subjectID>PSH\d+)$', 'views.getSubjectByHash'),
    (r'^wikipedia$', 'views.getWikipediaLink'),
    (r'^saveWikipediaLink$', 'views.saveWikipediaLink'),
    (r'^update$', 'views.update'),
    # (r'^psh_csv$', 'views.get_csv'),
    #(r'^updateTree$', 'handler.updateTree'),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        url(r'^static/(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': os.path.join(settings.ROOT, 'static').replace('\\','/')
        }),
)
