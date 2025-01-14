from django.urls import path

from . import views


urlpatterns = [
    path("create/", views.CreateEventView.as_view(), name="create_event"),
    path("submit/", views.submit_event, name="create_event"),
    path("<int:pk>/", views.EventView.as_view(), name="view_event"),
    path('<int:pk>/file/<int:file_id>/delete/', views.delete_event_file, name='delete_event_file'),
]