from django.urls import path
from . import views
from . import admin_views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('login/request/', views.temporary_login_request, name='temp_login_request'),
    path('login/temp/<str:token>/<str:email>/', views.temporary_login, name='temp_login'),
    path('reset-password/<str:token>/', views.reset_password, name='reset_password'),
    path('admin/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('admin/users/', admin_views.user_list, name='admin_user_list'),
    path('admin/users/create/', admin_views.user_create, name='admin_user_create'),
    path('admin/users/<int:user_id>/edit/', admin_views.user_edit, name='admin_user_edit'),
    path('admin/users/send-password/', admin_views.user_send_temp_password, name='admin_send_password'),
    path('admin/users/<int:user_id>/toggle-status/', admin_views.toggle_user_status, name='admin_toggle_user_status'),
] 