from django.conf.urls.defaults import *


urlpatterns = patterns(
    'babelsearch.views',

    url(regex=r'^vocabulary/$',
        view='edit_vocabulary',
        name='babelsearch-edit-vocabulary'),

    url(regex=(r'^vocabulary/'
               r'(?P<app_name>[a-z.]+)/'
               r'(?P<model_name>[a-z.]+)/'
               r'(?P<instance_pk>\d+)/$'),
        view='edit_vocabulary',
        name='babelsearch-edit-vocabulary'),
)
