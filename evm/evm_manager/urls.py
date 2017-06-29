from django.conf.urls import url

from .views import CheckState

urlpatterns = [
    url(r'^(?P<multisig_address>[a-zA-Z0-9]+)/(?P<tx_hash>[a-zA-Z0-9]+)', CheckState.as_view()),
]
