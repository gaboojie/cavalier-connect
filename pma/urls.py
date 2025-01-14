from django.urls import path
from . import views

urlpatterns = [
    path('pma/', views.pma_page, name='pma'),
    path('pma/edit_event/<int:user_id>/', views.edit_event, name='edit_event'),
    path('pma/delete_event/', views.delete_event, name='delete_event'),
]