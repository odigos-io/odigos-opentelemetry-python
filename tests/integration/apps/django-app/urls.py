from django.urls import path

from views import rolldice

urlpatterns = [
    path("rolldice", rolldice),
]
