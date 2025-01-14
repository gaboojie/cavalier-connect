from django.urls import path
from . import views

urlpatterns = [
    path('friends/', views.friends_page, name='friends'),
]