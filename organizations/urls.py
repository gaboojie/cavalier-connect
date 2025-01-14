from django.urls import path
from . import views

app_name = 'organizations'

urlpatterns = [
    path('create/', views.create_organization, name='create_organization'),
    path('submit/', views.submit_organization, name='submit_organization'),
    
    path('<int:pk>/', views.OrganizationView.as_view(), name='view_organization'),  # View individual organization
    path('<int:pk>/edit/', views.edit_organization_view, name='edit_organization'),  # Edit individual organization
]