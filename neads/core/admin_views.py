from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse

from .models import User, UserProfile
from .forms import AdminUserCreationForm, AdminUserEditForm, SendTempPasswordForm, ClientCreationForm, ConsultantCreationForm
from .decorators import role_required

from neads.creators.models import Creator, Domain, Location


@login_required
@role_required(['admin', 'consultant'])
def admin_dashboard(request):
    """
    Tableau de bord principal de l'administration
    """
    is_admin = request.user.role == 'admin'
    
    # Stats utilisateurs
    user_stats = {
        'total': User.objects.count(),
        'admins': User.objects.filter(role='admin').count() if is_admin else 0,
        'consultants': User.objects.filter(role='consultant').count() if is_admin else 0,
        'clients': User.objects.filter(role='client').count(),
        'creators': User.objects.filter(role='creator').count(),
        'active': User.objects.filter(is_active=True).count(),
        'inactive': User.objects.filter(is_active=False).count() if is_admin else 0,
    }
    
    # Stats créateurs
    creator_stats = {
        'total': Creator.objects.count(),
        'verified': Creator.objects.filter(verified_by_neads=True).count(),
        'unverified': Creator.objects.filter(verified_by_neads=False).count(),
        'with_ratings': Creator.objects.filter(total_ratings__gt=0).count(),
        'top_rated': Creator.objects.filter(average_rating__gte=4).count(),
    }
    
    # Derniers utilisateurs inscrits
    # Les consultants ne voient que les clients et les créateurs
    if is_admin:
        recent_users = User.objects.all().order_by('-date_joined')[:5]
    else:
        recent_users = User.objects.filter(role__in=['client', 'creator']).order_by('-date_joined')[:5]
    
    context = {
        'user_stats': user_stats,
        'creator_stats': creator_stats,
        'recent_users': recent_users,
        'is_admin': is_admin,
    }
    
    return render(request, 'admin/dashboard.html', context)


@login_required
@role_required(['admin', 'consultant'])
def user_list(request):
    """
    Liste de tous les utilisateurs pour l'administration
    """
    is_admin = request.user.role == 'admin'
    
    # Filtres
    role_filter = request.GET.get('role', '')
    query = request.GET.get('q', '')
    
    # Base de la requête - les consultants ne voient que les clients et créateurs
    if is_admin:
        users = User.objects.all().order_by('-date_joined')
    else:
        users = User.objects.filter(role__in=['client', 'creator']).order_by('-date_joined')
    
    # Filtrer par rôle si spécifié
    if role_filter and role_filter in dict(User.ROLE_CHOICES):
        # Pour les consultants, ignorer les filtres pour les rôles qu'ils ne peuvent pas voir
        if not is_admin and role_filter in ['admin', 'consultant']:
            pass
        else:
            users = users.filter(role=role_filter)
    
    # Recherche par nom, prénom ou email
    if query:
        users = users.filter(
            Q(first_name__icontains=query) | 
            Q(last_name__icontains=query) | 
            Q(email__icontains=query)
        )
    
    # Pagination
    paginator = Paginator(users, 20)  # 20 utilisateurs par page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Préparer les choix de rôles pour le filtre
    role_choices = User.ROLE_CHOICES
    if not is_admin:
        role_choices = [choice for choice in User.ROLE_CHOICES if choice[0] in ['client', 'creator']]
    
    context = {
        'users': page_obj,
        'role_filter': role_filter,
        'query': query,
        'role_choices': role_choices,
        'total_users': paginator.count,
        'is_admin': is_admin,
    }
    
    return render(request, 'admin/user_list.html', context)


@login_required
@role_required(['admin', 'consultant'])
def user_create(request):
    """
    Création d'un nouvel utilisateur
    """
    # Déterminer les rôles que l'utilisateur actuel peut créer
    is_admin = request.user.role == 'admin'
    
    # Récupérer un rôle prédéfini depuis les paramètres de l'URL
    preset_role = request.GET.get('role', '')
    
    if request.method == 'POST':
        form = AdminUserCreationForm(request.POST)
        
        # Vérifier si un consultant essaie de créer un autre consultant
        if not is_admin and form.data.get('role') == 'consultant':
            messages.error(request, "Seuls les administrateurs peuvent créer des consultants.")
            return redirect('admin_user_list')
            
        if form.is_valid():
            user = form.save()
            
            # Créer automatiquement un profil Creator si rôle = creator
            if user.role == 'creator':
                if not hasattr(user, 'creator_profile'):
                    try:
                        # Obtenir le premier domaine disponible
                        from neads.creators.models import Domain, Location, Creator
                        
                        # Créer d'abord une localisation par défaut
                        location = Location.objects.create(
                            city="Paris",
                            country="France",
                            postal_code="75000"
                        )
                        
                        # Créer le profil du créateur
                        creator = Creator.objects.create(
                            user=user,
                            first_name=user.first_name,
                            last_name=user.last_name,
                            email=user.email,
                            age=25,  # Valeur par défaut
                            gender='O',  # Valeur par défaut
                            verified_by_neads=False,  # Mode brouillon par défaut
                            location=location,
                            bio="Créateur en attente de configuration",
                            equipment="Smartphone",
                            content_types="video",
                        )
                        
                        # Ajouter au moins un domaine par défaut
                        default_domain = Domain.objects.first()
                        if default_domain:
                            creator.domains.add(default_domain)
                        
                        messages.info(request, f"Un profil de créateur en mode brouillon a été créé pour {user.get_full_name()}. Le profil devra être complété avant d'être visible publiquement.")
                    except Exception as e:
                        messages.error(request, f"Erreur lors de la création du profil créateur: {str(e)}")
            
            messages.success(request, f"L'utilisateur {user.get_full_name()} a été créé avec succès.")
            
            # Si option cochée, envoyer un email avec mot de passe temporaire
            if request.POST.get('send_credentials'):
                temp_token = user.generate_temp_login_token()
                reset_url = f"{request.scheme}://{request.get_host()}/reset-password/{temp_token}/"
                
                # Envoyer l'email
                subject = "Bienvenue sur NEADS - Vos identifiants de connexion"
                html_message = render_to_string('emails/welcome_user.html', {
                    'user': user,
                    'reset_url': reset_url,
                    'role': dict(User.ROLE_CHOICES)[user.role],
                })
                
                try:
                    send_mail(
                        subject=subject,
                        message="",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        html_message=html_message,
                        fail_silently=False,
                    )
                    messages.success(request, f"Un email avec les instructions de connexion a été envoyé à {user.email}.")
                except Exception as e:
                    messages.error(request, f"Erreur lors de l'envoi de l'email: {str(e)}")
            
            return redirect('admin_user_list')
    else:
        # Initialiser le formulaire avec le rôle prédéfini si spécifié et valide
        initial_data = {}
        
        # Vérifier que le rôle demandé est valide et que l'utilisateur a le droit de le créer
        if preset_role in dict(User.ROLE_CHOICES):
            # Un consultant ne peut pas créer d'admin ou de consultant
            if not is_admin and preset_role in ['admin', 'consultant']:
                messages.warning(request, "Vous n'avez pas l'autorisation de créer ce type d'utilisateur.")
            else:
                initial_data['role'] = preset_role
        
        form = AdminUserCreationForm(initial=initial_data)
    
    # Limiter les choix de rôles pour les consultants
    if not is_admin:
        form.fields['role'].choices = [
            choice for choice in User.ROLE_CHOICES 
            if choice[0] not in ['admin', 'consultant']
        ]
    
    context = {
        'form': form,
        'title': 'Créer un nouvel utilisateur',
        'is_admin': is_admin,
    }
    
    return render(request, 'admin/user_form.html', context)


@login_required
@role_required(['admin', 'consultant'])
def user_edit(request, user_id):
    """
    Édition d'un utilisateur existant
    """
    user = get_object_or_404(User, id=user_id)
    is_admin = request.user.role == 'admin'
    
    # Empêcher un consultant de modifier un admin ou un autre consultant
    if not is_admin and (user.role == 'admin' or user.role == 'consultant'):
        messages.error(request, "Vous n'avez pas les droits pour modifier cet utilisateur.")
        return redirect('admin_user_list')
    
    if request.method == 'POST':
        form = AdminUserEditForm(request.POST, instance=user)
        
        # Vérifier si un consultant essaie de transformer un utilisateur en consultant
        new_role = request.POST.get('role')
        if not is_admin and new_role == 'consultant':
            messages.error(request, "Seuls les administrateurs peuvent attribuer le rôle de consultant.")
            return redirect('admin_user_list')
            
        if form.is_valid():
            original_role = user.role
            user = form.save()
            
            # Si rôle modifié de/vers Creator, gérer le profil créateur
            if original_role != 'creator' and user.role == 'creator':
                # Créer un profil Creator si n'existe pas
                if not hasattr(user, 'creator_profile'):
                    try:
                        # Obtenir le premier domaine disponible
                        from neads.creators.models import Domain, Location, Creator
                        
                        # Créer d'abord une localisation par défaut
                        location = Location.objects.create(
                            city="Paris",
                            country="France",
                            postal_code="75000"
                        )
                        
                        # Créer le profil du créateur
                        creator = Creator.objects.create(
                            user=user,
                            first_name=user.first_name,
                            last_name=user.last_name,
                            email=user.email,
                            age=25,  # Valeur par défaut
                            gender='O',  # Valeur par défaut
                            verified_by_neads=False,  # Mode brouillon par défaut
                            location=location,
                            bio="Créateur en attente de configuration",
                            equipment="Smartphone",
                            content_types="video",
                        )
                        
                        # Ajouter au moins un domaine par défaut
                        default_domain = Domain.objects.first()
                        if default_domain:
                            creator.domains.add(default_domain)
                        
                        messages.info(request, f"Un profil de créateur en mode brouillon a été créé pour {user.get_full_name()}. Le profil devra être complété avant d'être visible publiquement.")
                    except Exception as e:
                        messages.error(request, f"Erreur lors de la création du profil créateur: {str(e)}")
            
            messages.success(request, f"L'utilisateur {user.get_full_name()} a été mis à jour avec succès.")
            return redirect('admin_user_list')
    else:
        form = AdminUserEditForm(instance=user)
    
    # Limiter les choix de rôles pour les consultants
    if not is_admin:
        form.fields['role'].choices = [
            choice for choice in User.ROLE_CHOICES 
            if choice[0] not in ['admin', 'consultant']
        ]
    
    # Vérifier si l'utilisateur a un profil de créateur
    has_creator_profile = hasattr(user, 'creator_profile')
    creator_id = user.creator_profile.id if has_creator_profile else None
    
    context = {
        'form': form,
        'user_obj': user,
        'title': f"Modifier l'utilisateur {user.get_full_name()}",
        'has_creator_profile': has_creator_profile,
        'creator_id': creator_id,
        'is_admin': is_admin,
    }
    
    return render(request, 'admin/user_form.html', context)


@login_required
@role_required(['admin', 'consultant'])
def user_send_temp_password(request):
    """
    Envoyer un mot de passe temporaire à un utilisateur
    """
    is_admin = request.user.role == 'admin'
    
    if request.method == 'POST':
        form = SendTempPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = User.objects.get(email=email)
            
            # Empêcher un consultant d'envoyer un mot de passe à un admin ou consultant
            if not is_admin and user.role in ['admin', 'consultant']:
                messages.error(request, "Vous n'avez pas les droits pour cette action")
                return redirect('admin_dashboard')
            
            # Générer un token temporaire
            temp_token = user.generate_temp_login_token()
            reset_url = f"{request.scheme}://{request.get_host()}/reset-password/{temp_token}/"
            
            # Envoyer l'email
            subject = "NEADS - Réinitialisation de votre mot de passe"
            html_message = render_to_string('emails/reset_password.html', {
                'user': user,
                'reset_url': reset_url,
            })
            
            try:
                send_mail(
                    subject=subject,
                    message="",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    html_message=html_message,
                    fail_silently=False,
                )
                messages.success(request, f"Un email de réinitialisation de mot de passe a été envoyé à {user.email}.")
            except Exception as e:
                messages.error(request, f"Erreur lors de l'envoi de l'email: {str(e)}")
            
            return redirect('admin_user_list')
    else:
        form = SendTempPasswordForm()
    
    context = {
        'form': form,
        'title': 'Envoyer un mot de passe temporaire',
        'is_admin': is_admin,
    }
    
    return render(request, 'admin/password_form.html', context)


@login_required
@role_required(['admin', 'consultant'])
def toggle_user_status(request, user_id):
    """
    Activer/désactiver un utilisateur
    """
    user = get_object_or_404(User, id=user_id)
    is_admin = request.user.role == 'admin'
    
    # Empêcher un consultant de modifier un admin ou un autre consultant
    if not is_admin and (user.role == 'admin' or user.role == 'consultant'):
        messages.error(request, "Vous n'avez pas les droits pour modifier cet utilisateur.")
        return redirect('admin_user_list')
    
    # Empêcher la désactivation de son propre compte
    if user == request.user:
        messages.error(request, "Vous ne pouvez pas désactiver votre propre compte.")
        return redirect('admin_user_list')
    
    user.is_active = not user.is_active
    user.save()
    
    status = "activé" if user.is_active else "désactivé"
    messages.success(request, f"L'utilisateur {user.get_full_name()} a été {status}.")
    
    return redirect('admin_user_list')


@login_required
@role_required(['admin', 'consultant'])
def delete_user(request, user_id):
    """
    Supprimer définitivement un utilisateur
    """
    user = get_object_or_404(User, id=user_id)
    is_admin = request.user.role == 'admin'
    
    # Empêcher un consultant de supprimer un admin ou un autre consultant
    if not is_admin and (user.role == 'admin' or user.role == 'consultant'):
        messages.error(request, "Vous n'avez pas les droits pour supprimer cet utilisateur.")
        return redirect('admin_user_list')
    
    # Empêcher la suppression de son propre compte
    if user == request.user:
        messages.error(request, "Vous ne pouvez pas supprimer votre propre compte.")
        return redirect('admin_user_list')
    
    # Récupérer les informations pour le message de confirmation
    username = user.get_full_name()
    email = user.email
    
    try:
        # Supprimer l'utilisateur
        user.delete()
        messages.success(request, f"L'utilisateur {username} ({email}) a été définitivement supprimé.")
    except Exception as e:
        messages.error(request, f"Erreur lors de la suppression : {str(e)}")
    
    return redirect('admin_user_list')


@login_required
@role_required(['admin', 'consultant'])
def client_create(request):
    """
    Vue frontend pour la création d'un client par un consultant ou un admin.
    """
    if request.method == 'POST':
        form = ClientCreationForm(request.POST)
        if form.is_valid():
            client = form.save()
            
            # Si option cochée, envoyer un email avec mot de passe temporaire
            if form.cleaned_data.get('send_credentials'):
                temp_token = client.generate_temp_login_token()
                reset_url = f"{request.scheme}://{request.get_host()}/reset-password/{temp_token}/"
                
                # Envoyer l'email
                subject = "Bienvenue sur NEADS - Vos identifiants de connexion"
                html_message = render_to_string('emails/welcome_user.html', {
                    'user': client,
                    'reset_url': reset_url,
                    'role': 'Client',
                })
                
                try:
                    send_mail(
                        subject=subject,
                        message="",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[client.email],
                        html_message=html_message,
                        fail_silently=False,
                    )
                    messages.success(request, f"Un email avec les instructions de connexion a été envoyé à {client.email}.")
                except Exception as e:
                    messages.error(request, f"Erreur lors de l'envoi de l'email: {str(e)}")
            
            messages.success(request, f"Le client {client.get_full_name()} a été créé avec succès.")
            return redirect('admin_user_list')
    else:
        form = ClientCreationForm()
    
    context = {
        'form': form,
        'title': 'Ajouter un nouveau client',
    }
    
    return render(request, 'admin/user_frontend_form.html', context)


@login_required
@role_required(['admin'])
def consultant_create(request):
    """
    Vue frontend pour la création d'un consultant par un admin.
    """
    # Vérifier que l'utilisateur est bien un admin
    if request.user.role != 'admin':
        messages.error(request, "Seuls les administrateurs peuvent créer des consultants.")
        return redirect('admin_dashboard')
    
    if request.method == 'POST':
        form = ConsultantCreationForm(request.POST)
        if form.is_valid():
            consultant = form.save()
            
            # Si option cochée, envoyer un email avec mot de passe temporaire
            if form.cleaned_data.get('send_credentials'):
                temp_token = consultant.generate_temp_login_token()
                reset_url = f"{request.scheme}://{request.get_host()}/reset-password/{temp_token}/"
                
                # Envoyer l'email
                subject = "Bienvenue sur NEADS - Vos identifiants de connexion"
                html_message = render_to_string('emails/welcome_user.html', {
                    'user': consultant,
                    'reset_url': reset_url,
                    'role': 'Consultant',
                })
                
                try:
                    send_mail(
                        subject=subject,
                        message="",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[consultant.email],
                        html_message=html_message,
                        fail_silently=False,
                    )
                    messages.success(request, f"Un email avec les instructions de connexion a été envoyé à {consultant.email}.")
                except Exception as e:
                    messages.error(request, f"Erreur lors de l'envoi de l'email: {str(e)}")
            
            messages.success(request, f"Le consultant {consultant.get_full_name()} a été créé avec succès.")
            return redirect('admin_user_list')
    else:
        form = ConsultantCreationForm()
    
    context = {
        'form': form,
        'title': 'Ajouter un nouveau consultant',
    }
    
    return render(request, 'admin/user_frontend_form.html', context) 