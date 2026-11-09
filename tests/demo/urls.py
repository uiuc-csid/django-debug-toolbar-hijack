from django.urls import path

from tests.urls import page, urlpatterns

urlpatterns = [path("", page), *urlpatterns]
