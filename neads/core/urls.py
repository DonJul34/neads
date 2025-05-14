from django.urls import path
from . import views
from . import admin_views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('creators/register/', views.creator_registration_view, name='creator_register'),
    path('login/request/', views.temporary_login_request, name='temp_login_request'),
    path('login/temp/<str:token>/<str:email>/', views.temporary_login, name='temp_login'),

    # URLs pour la réinitialisation du mot de passe
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
            template_name='core/password_reset_form.html',
            email_template_name='core/emails/password_reset_email.html',
            subject_template_name='core/emails/password_reset_subject.txt',
            success_url='/password-reset/done/' # ou reverse_lazy('password_reset_done')
         ), 
         name='password_reset'),
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
            template_name='core/password_reset_done.html'
         ), 
         name='password_reset_done'),
    path('reset-password/<uidb64>/<token>/',  # Django s'attend à uidb64 et token pour cette vue
         auth_views.PasswordResetConfirmView.as_view(
            template_name='core/reset_password.html', # Votre template existant, à vérifier
            success_url='/reset-password/complete/' # ou reverse_lazy('password_reset_complete')
         ), 
         name='password_reset_confirm'), # Nom standard utilisé par Django
    path('reset-password/complete/', 
         auth_views.PasswordResetCompleteView.as_view(
            template_name='core/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
    
    # Gestion pour admins et consultants
    path('gestion/', views.management_dashboard, name='management_dashboard'),
    path('gestion/createurs/', views.creator_list, name='creator_list'),
    path('gestion/clients/', views.client_list, name='client_list'),
    path('gestion/clients/create/', views.client_create_view, name='client_create_view'),
    
    # Contact créateur
    path('creators/<int:creator_id>/contact/', views.contact_creator, name='contact_creator'),
    
    # Panel admin (admins uniquement)
    path('admin/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('admin/users/', admin_views.user_list, name='admin_user_list'),
    path('admin/users/create/', admin_views.user_create, name='admin_user_create'),
    path('admin/users/<int:user_id>/edit/', admin_views.user_edit, name='admin_user_edit'),
    
    # Route alternative pour l'édition des utilisateurs (pour éviter le conflit avec l'admin Django)
    path('gestion-admin/users/<int:user_id>/edit/', admin_views.user_edit, name='gestion_user_edit'),
    
    path('admin/users/<int:user_id>/delete/', admin_views.delete_user, name='admin_delete_user'),
    path('admin/users/send-password/', admin_views.user_send_temp_password, name='admin_send_password'),
    path('admin/users/<int:user_id>/toggle-status/', admin_views.toggle_user_status, name='admin_toggle_user_status'),
    
    # Nouveaux formulaires frontend pour la création d'utilisateurs
    path('admin/clients/create/', admin_views.client_create, name='client_create'),
    path('admin/consultants/create/', admin_views.consultant_create, name='consultant_create'),
    path('upload-media/', views.upload_media, name='upload_media'),
] 