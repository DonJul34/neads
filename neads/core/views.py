from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from django.urls import reverse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
import datetime
import logging

from .models import User, UserProfile
from .forms import LoginForm, TemporaryLoginForm, UserProfileForm, SetPasswordForm, ClientCreationForm
from .decorators import role_required
from neads.creators.models import Creator


def home(request):
    """
    Page d'accueil du site.
    """
    return render(request, 'core/home.html')


@login_required
@role_required(['admin', 'consultant'])
def management_dashboard(request):
    """
    Tableau de bord de gestion pour les administrateurs et consultants.
    Centralise l'accès aux différentes fonctionnalités de gestion.
    """
    # Vérifier si on a demandé d'ajouter un utilisateur spécifique
    add_consultant = request.GET.get('add_consultant')
    add_client = request.GET.get('add_client')
    add_creator = request.GET.get('add_creator')
    
    # Rediriger vers le formulaire d'ajout d'utilisateur dans l'admin Django
    if add_consultant or add_client or add_creator:
        # Pour les consultants, on ne peut rediriger que si c'est pour créer un client ou un créateur
        if not request.user.role == 'admin' and add_consultant:
            messages.error(request, "Vous n'avez pas les droits pour créer un consultant.")
            return redirect('management_dashboard')
            
        # Rediriger vers le formulaire d'ajout d'utilisateur dans l'admin Django
        return redirect('/admin/core/user/add/')
    
    # Statistiques de base
    user_stats = {
        'total': User.objects.count(),
        'clients': User.objects.filter(role='client').count(),
        'creators': Creator.objects.count(),
    }
    
    # Statistiques spécifiques aux créateurs
    creator_stats = {
        'total': Creator.objects.count(),
        'verified': Creator.objects.filter(verified_by_neads=True).count(),
        'with_media': Creator.objects.filter(media__isnull=False).distinct().count(),
    }
    
    # Récents créateurs
    recent_creators = Creator.objects.all().order_by('-created_at')[:5]
    
    # Récents utilisateurs
    recent_users = User.objects.filter(role='client').order_by('-date_joined')[:5]
    
    context = {
        'user_stats': user_stats,
        'creator_stats': creator_stats,
        'recent_creators': recent_creators,
        'recent_users': recent_users,
        'user': request.user,
    }
    
    return render(request, 'core/management_dashboard.html', context)


@login_required
@role_required(['admin', 'consultant'])
def creator_list(request):
    """
    Vue pour la gestion des créateurs (pour consultants et admins).
    """
    # Récupérer tous les créateurs
    creators = Creator.objects.all().order_by('-created_at')
    
    # Filtres
    verified_filter = request.GET.get('verified')
    if verified_filter == 'true':
        creators = creators.filter(verified_by_neads=True)
    elif verified_filter == 'false':
        creators = creators.filter(verified_by_neads=False)
    
    # Recherche par nom/email
    search_query = request.GET.get('query')
    if search_query:
        creators = creators.filter(
            Q(first_name__icontains=search_query) | 
            Q(last_name__icontains=search_query) | 
            Q(email__icontains=search_query) |
            Q(full_name__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(creators, 15)  # 15 créateurs par page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'creators': page_obj,
        'search_query': search_query,
        'verified_filter': verified_filter,
        'total_creators': paginator.count,
    }
    
    return render(request, 'core/creator_list.html', context)


def login_view(request):
    """
    Vue de connexion standard.
    """
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            
            try:
                user = User.objects.get(email=email)
                if user.check_password(password):
                    login(request, user)
                    
                    # Redirection après connexion en fonction du rôle
                    if user.has_role('creator'):
                        try:
                            # Vérifier si le profil de créateur existe
                            if hasattr(user, 'creator_profile') and user.creator_profile:
                                # Vérifier si le profil est complet
                                if not user.creator_profile.bio or not user.creator_profile.domains.exists():
                                    messages.warning(request, "Votre profil de créateur n'est pas complet. Veuillez le compléter pour être visible dans la galerie.")
                                return redirect('creator_detail', creator_id=user.creator_profile.id)
                            else:
                                # Rediriger vers la page de création de profil si pas de profil de créateur
                                messages.warning(request, "Votre profil de créateur n'est pas encore configuré. Veuillez le créer pour être visible dans la galerie.")
                                return redirect('creator_add')
                        except Exception as e:
                            # En cas d'erreur, rediriger vers la page de création de profil
                            messages.error(request, f"Erreur d'accès au profil de créateur: {str(e)}")
                            return redirect('creator_add')
                    else:
                        return redirect('gallery_view')
                else:
                    form.add_error('password', 'Mot de passe incorrect')
            except User.DoesNotExist:
                form.add_error('email', 'Aucun compte avec cet email')
    else:
        form = LoginForm()
        
    return render(request, 'core/login.html', {'form': form})


def temporary_login_request(request):
    """
    Vue pour demander un lien de connexion temporaire ou s'inscrire en tant que créateur.
    Cette vue gère deux cas d'usage:
    1. Demande de lien de connexion temporaire pour les clients existants (par défaut)
    2. Inscription des nouveaux créateurs (avec le paramètre ?creator=1)
    """
    # Vérifier si nous sommes dans le contexte d'inscription créateur
    is_creator_signup = request.GET.get('creator', '0') == '1'
    
    if is_creator_signup:
        from neads.creators.forms import CreatorRegistrationForm
        from neads.creators.models import Creator, Location, Media
        
        if request.method == 'POST':
            form = CreatorRegistrationForm(request.POST, request.FILES)
            if form.is_valid():
                # Récupérer les données du formulaire
                data = form.cleaned_data
                
                # 1. Créer l'utilisateur
                from neads.core.models import User
                user = User.objects.create(
                    email=data['email'],
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    role='creator',  # Rôle créateur
                    is_active=True,  # Compte actif immédiatement
                )
                
                # 2. Créer la localisation
                location = Location.objects.create(
                    full_address=data['full_address'],
                    latitude=data.get('latitude'),
                    longitude=data.get('longitude')
                )
                
                # 3. Créer le profil créateur
                creator = Creator.objects.create(
                    user=user,
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    age=datetime.date.today().year - data['birth_year'],
                    gender=data['gender'],
                    email=data['email'],
                    phone=data['phone'],
                    location=location,
                    youtube_link=data.get('youtube_link', ''),
                    tiktok_link=data.get('tiktok_link', ''),
                    instagram_link=data.get('instagram_link', ''),
                    bio=data['bio'],
                    equipment=data['equipment'],
                    can_invoice=data['can_invoice'] == 'True',
                    previous_clients=data['previous_clients'],
                    featured_image=data['featured_image'],
                    verified_by_neads=False,  # Non vérifié par défaut
                )
                
                # 4. Ajouter les domaines
                creator.domains.set(data['domains'])
                
                # 5. Traiter les uploads du portfolio
                # Traiter les vidéos individuelles
                for i in range(1, 6):
                    field_name = f'video_file{i}'
                    if field_name in request.FILES:
                        video_file = request.FILES[field_name]
                        media = Media.objects.create(
                            creator=creator,
                            title=f"Vidéo {i}",
                            media_type='video',
                            video_file=video_file,
                            is_verified=False
                        )
                
                # Traiter les images individuelles
                for i in range(1, 4):
                    field_name = f'image_file{i}'
                    if field_name in request.FILES:
                        image_file = request.FILES[field_name]
                        media = Media.objects.create(
                            creator=creator,
                            title=f"Image {i}",
                            media_type='image',
                            file=image_file,
                            is_verified=False
                        )
                
                # 6. Générer un token temporaire pour la connexion
                token = user.generate_temp_login_token()
                
                # 7. Envoyer un email de confirmation
                temp_login_url = request.build_absolute_uri(
                    reverse('temp_login', kwargs={'token': token, 'email': user.email})
                )
                
                subject = 'Bienvenue sur NEADS ! Confirmez votre profil créateur'
                message = render_to_string('core/emails/creator_confirmation_email.html', {
                    'user': user,
                    'creator': creator,
                    'temp_login_url': temp_login_url,
                    'expiry_hours': 24,
                })
                
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    html_message=message,
                )
                
                # 8. Journaliser
                logger = logging.getLogger(__name__)
                logger.info(f"Nouveau créateur inscrit: {creator.full_name} (ID: {creator.id}, Email: {user.email})")
                
                # 9. Rediriger vers une page de confirmation
                messages.success(request, "Votre profil créateur a été créé avec succès ! Un email de confirmation vous a été envoyé.")
                return redirect('home')
        else:
            form = CreatorRegistrationForm()
        
        context = {
            'form': form,
            'is_creator_signup': True,
            'google_api_key': settings.GOOGLE_PLACES_API_KEY,
        }
        
        return render(request, 'core/creator_signup.html', context)
    
    else:
        # Code existant pour le login temporaire
        if request.method == 'POST':
            form = TemporaryLoginForm(request.POST)
            if form.is_valid():
                email = form.cleaned_data['email']
                
                # Récupérer ou créer l'utilisateur
                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        'role': 'client',  # Défaut pour les nouveaux utilisateurs
                    }
                )
                
                # Générer un token temporaire
                token = user.generate_temp_login_token()
                
                # Construire le lien de connexion
                temp_login_url = request.build_absolute_uri(
                    reverse('temp_login', kwargs={'token': token, 'email': email})
                )
                
                # Envoyer l'email
                subject = 'Votre lien de connexion NEADS'
                message = render_to_string('core/emails/temp_login_email.html', {
                    'user': user,
                    'temp_login_url': temp_login_url,
                    'expiry_hours': 24,
                })
                
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    html_message=message,
                )
                
                return render(request, 'core/temp_login_sent.html', {'email': email})
        else:
            form = TemporaryLoginForm()
        
        return render(request, 'core/temp_login_request.html', {'form': form, 'is_creator_signup': False})


def temporary_login(request, token, email):
    """
    Vue pour se connecter avec un token temporaire.
    """
    try:
        user = User.objects.get(email=email)
        if user.is_temp_token_valid(token):
            # Réinitialiser le token après utilisation
            user.temp_login_token = None
            user.temp_login_expiry = None
            user.save()
            
            # Connecter l'utilisateur
            login(request, user)
            
            # Redirection après connexion
            if user.has_role('creator'):
                try:
                    # Vérifier si le profil de créateur existe
                    if hasattr(user, 'creator_profile') and user.creator_profile:
                        return redirect('creator_detail', creator_id=user.creator_profile.id)
                    else:
                        # Rediriger vers la page d'accueil si pas de profil de créateur
                        messages.warning(request, "Votre profil de créateur n'est pas encore configuré.")
                        return redirect('gallery_view')
                except Exception as e:
                    # En cas d'erreur, rediriger vers la page d'accueil
                    messages.error(request, f"Erreur d'accès au profil de créateur: {str(e)}")
                    return redirect('gallery_view')
            else:
                return redirect('gallery_view')
        else:
            return render(request, 'core/temp_login_invalid.html', {
                'reason': 'Le lien de connexion a expiré ou est invalide.'
            })
    except User.DoesNotExist:
        return render(request, 'core/temp_login_invalid.html', {
            'reason': 'Aucun utilisateur trouvé avec cet email.'
        })


@login_required
def logout_view(request):
    """
    Vue de déconnexion.
    """
    logout(request)
    return redirect('home')


@login_required
def profile_view(request):
    """
    Vue du profil utilisateur.
    """
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile(user=request.user)
        profile.save()
        
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            
            # Mettre à jour les champs de l'utilisateur
            user = request.user
            user.first_name = form.cleaned_data.get('first_name', user.first_name)
            user.last_name = form.cleaned_data.get('last_name', user.last_name)
            user.save()
            
            return redirect('profile')
    else:
        # Préremplir avec les données utilisateur
        initial_data = {
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
        }
        form = UserProfileForm(instance=profile, initial=initial_data)
        
    return render(request, 'core/profile.html', {'form': form, 'profile': profile})


def reset_password(request, token):
    """
    Vue pour réinitialiser le mot de passe avec un token temporaire.
    """
    # Chercher l'utilisateur avec le token temporaire valide
    try:
        user = User.objects.get(temp_login_token=token, temp_login_expiry__gt=timezone.now())
    except User.DoesNotExist:
        return render(request, 'core/temp_login_invalid.html', {
            'reason': 'Le lien de réinitialisation a expiré ou est invalide.'
        })
    
    if request.method == 'POST':
        form = SetPasswordForm(request.POST)
        if form.is_valid():
            # Vérifier que les mots de passe correspondent
            password = form.cleaned_data.get('password1')
            
            # Mettre à jour le mot de passe et réinitialiser le token
            user.set_password(password)
            user.temp_login_token = None
            user.temp_login_expiry = None
            user.save()
            
            # Connecter l'utilisateur
            login(request, user)
            
            messages.success(request, "Votre mot de passe a été mis à jour avec succès.")
            
            # Redirection en fonction du rôle
            if user.has_role('creator'):
                return redirect('creator_detail', creator_id=user.creator_profile.id)
            else:
                return redirect('gallery_view')
    else:
        form = SetPasswordForm()
    
    context = {
        'form': form,
        'token': token,
    }
    
    return render(request, 'core/reset_password.html', context)


@login_required
@role_required(['admin', 'consultant'])
def client_list(request):
    """
    Vue pour la gestion des clients (pour consultants et admins).
    """
    # Filtrer uniquement les clients
    clients = User.objects.filter(role='client').order_by('last_name', 'first_name')
    
    # Recherche par nom/email
    search_query = request.GET.get('query')
    if search_query:
        clients = clients.filter(
            Q(first_name__icontains=search_query) | 
            Q(last_name__icontains=search_query) | 
            Q(email__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(clients, 15)  # 15 clients par page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'clients': page_obj,
        'search_query': search_query,
        'total_clients': paginator.count,
    }
    
    return render(request, 'core/client_list.html', context)


@login_required
@role_required(['admin', 'consultant'])
def client_create_view(request):
    """
    Vue pour permettre aux consultants de créer des clients.
    Cette vue est accessible depuis la section de gestion, contrairement à celle dans admin_views.
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
            return redirect('client_list')
    else:
        form = ClientCreationForm()
    
    context = {
        'form': form,
        'title': 'Ajouter un nouveau client',
    }
    
    return render(request, 'core/client_form.html', context)


@login_required
def contact_creator(request, creator_id):
    """
    Vue pour envoyer un email à un créateur via le formulaire de contact.
    """
    creator = get_object_or_404(Creator, id=creator_id)
    
    if request.method == 'POST':
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        copy_me = request.POST.get('copy_me') == 'on'
        
        # Préparation du message avec les informations du client
        html_message = render_to_string('core/emails/contact_creator_email.html', {
            'creator': creator,
            'user': request.user,
            'subject': subject,
            'message': message,
        })
        
        # Envoi de l'email au créateur
        send_mail(
            subject=f"NEADS - Contact: {subject}",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[creator.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        # Copie à l'expéditeur si demandée
        if copy_me and request.user.email:
            send_mail(
                subject=f"NEADS - Copie de votre message à {creator.full_name}",
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[request.user.email],
                html_message=html_message,
                fail_silently=False,
            )
        
        messages.success(request, f"Votre message a été envoyé à {creator.full_name}")
        return redirect('creator_detail', creator_id=creator_id)
        
    return redirect('creator_detail', creator_id=creator_id)
