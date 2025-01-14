from django.urls import path

from . import views


urlpatterns = [
    path("organization/", views.OrganizationEventView.as_view(), name="organization-search"),
    path("", views.SearchEventView.as_view(), name="search")
]
