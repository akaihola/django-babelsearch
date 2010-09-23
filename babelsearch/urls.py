from django.conf.urls.defaults import *


urlpatterns = patterns(
    'babelsearch.views',

    url(regex=r'^vocabulary/',
        view='edit_vocabulary',
        name='babelsearch-edit-vocabulary'),
)
