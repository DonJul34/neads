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
from .forms import AdminUserCreationForm, AdminUserEditForm, SendTempPasswordForm
from .decorators import role_required

from neads.creators.models import Creator, Domain, Location


@login_required
@role_required(['admin'])
def admin_dashboard(request):
    """
    Tableau de bord principal de l'administration
    """
    # Stats utilisateurs
    user_stats = {
        'total': User.objects.count(),
        'admins': User.objects.filter(role='admin').count(),
        'consultants': User.objects.filter(role='consultant').count(),
        'clients': User.objects.filter(role='client').count(),
        'creators': User.objects.filter(role='creator').count(),
        'active': User.objects.filter(is_active=True).count(),
        'inactive': User.objects.filter(is_active=False).count(),
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
    recent_users = User.objects.all().order_by('-date_joined')[:5]
    
    context = {
        'user_stats': user_stats,
        'creator_stats': creator_stats,
        'recent_users': recent_users,
    }
    
    return render(request, 'admin/dashboard.html', context)


@login_required
@role_required(['admin'])
def user_list(request):
    """
    Liste de tous les utilisateurs pour l'administration
    """
    # Filtres
    role_filter = request.GET.get('role', '')
    query = request.GET.get('q', '')
    
    # Base de la requête
    users = User.objects.all().order_by('-date_joined')
    
    # Filtrer par rôle si spécifié
    if role_filter and role_filter in dict(User.ROLE_CHOICES):
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
    
    context = {
        'users': page_obj,
        'role_filter': role_filter,
        'query': query,
        'role_choices': User.ROLE_CHOICES,
        'total_users': paginator.count,
    }
    
    return render(request, 'admin/user_list.html', context)


@login_required
@role_required(['admin'])
def user_create(request):
    """
    Création d'un nouvel utilisateur
    """
    if request.method == 'POST':
        form = AdminUserCreationForm(request.POST)
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
        form = AdminUserCreationForm()
    
    context = {
        'form': form,
        'title': 'Créer un nouvel utilisateur',
    }
    
    return render(request, 'admin/user_form.html', context)


@login_required
@role_required(['admin'])
def user_edit(request, user_id):
    """
    Édition d'un utilisateur existant
    """
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = AdminUserEditForm(request.POST, instance=user)
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
    
    # Vérifier si l'utilisateur a un profil de créateur
    has_creator_profile = hasattr(user, 'creator_profile')
    creator_id = user.creator_profile.id if has_creator_profile else None
    
    context = {
        'form': form,
        'user_obj': user,
        'title': f"Modifier l'utilisateur {user.get_full_name()}",
        'has_creator_profile': has_creator_profile,
        'creator_id': creator_id,
    }
    
    return render(request, 'admin/user_form.html', context)


@login_required
@role_required(['admin'])
def user_send_temp_password(request):
    """
    Envoie un mot de passe temporaire à un utilisateur existant
    """
    if request.method == 'POST':
        form = SendTempPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = User.objects.get(email=email)
            
            temp_token = user.generate_temp_login_token()
            reset_url = f"{request.scheme}://{request.get_host()}/reset-password/{temp_token}/"
            
            # Envoyer l'email
            subject = "NEADS - Vos identifiants de connexion"
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
                messages.success(request, f"Un email avec les instructions de réinitialisation a été envoyé à {user.email}.")
            except Exception as e:
                messages.error(request, f"Erreur lors de l'envoi de l'email: {str(e)}")
            
            return redirect('admin_user_list')
    else:
        form = SendTempPasswordForm()
    
    context = {
        'form': form,
        'title': 'Envoyer un mot de passe temporaire',
    }
    
    return render(request, 'admin/password_form.html', context)


@login_required
@role_required(['admin'])
def toggle_user_status(request, user_id):
    """
    Active/désactive un utilisateur (AJAX)
    """
    if request.method == "POST" and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        user = get_object_or_404(User, id=user_id)
        
        # Ne pas désactiver son propre compte
        if user == request.user:
            return JsonResponse({
                'success': False,
                'message': "Vous ne pouvez pas désactiver votre propre compte."
            })
        
        # Inverser le statut
        user.is_active = not user.is_active
        user.save()
        
        status_text = "activé" if user.is_active else "désactivé"
        
        return JsonResponse({
            'success': True,
            'is_active': user.is_active,
            'message': f"L'utilisateur {user.get_full_name()} a été {status_text}."
        })
    
    return JsonResponse({'success': False, 'message': "Méthode non autorisée"}, status=405) 