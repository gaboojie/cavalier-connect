from django.urls import path

from . import views

urlpatterns = [
    path("", views.UpcomingEventsView.as_view(), name="upcoming")
]
