from django.urls import path, include

from . import views
from friend import views as friend_views
from pma import views as pma_views

urlpatterns = [
    path("myaccount/", views.my_account, name="myaccount"),
    path('', views.landing_page, name='landing_page'),
    path('auth/', include('social_django.urls', namespace='social')),
    path('auth/redirect/',views.redirect_after_login, name='auth-redirect'),
    path('account_setup/', views.account_setup, name='account_setup'),
    path('logout', views.handle_logout, name="logout"),
    path('friends/', friend_views.friends_page, name="friends"),
    path('pma/', pma_views.pma_page, name="pma"),
    path('update-profile/', views.update_profile, name='update_profile'),
    path('update-profile-info/', views.update_profile_info, name='update_profile_info'),
    path('notification-settings/', views.update_notification_settings, name='notification_settings'),
    path('verify-phone-number/', views.verify_phone_number, name ='verify_phone_number'),
    path('delete-account/', views.delete_account, name='delete_account'),
]