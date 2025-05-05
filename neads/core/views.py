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
from django.contrib.auth.hashers import make_password
from django.core.files.storage import FileSystemStorage
import os
import uuid
from django.views.decorators.csrf import csrf_exempt

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
        import json
        
        # Vérifier si c'est la première ou la deuxième étape
        step = request.GET.get('step', '1')
        creator_id = request.GET.get('creator_id')
        
        if request.method == 'POST':
            form = CreatorRegistrationForm(request.POST, request.FILES)
            if form.is_valid():
                # Récupérer les données du formulaire
                data = form.cleaned_data
                
                # Vérifier l'étape depuis le formulaire
                form_step = request.POST.get('step', '1')
                
                if form_step == '1':
                    # On ignore les erreurs des champs de médias pour l'étape 1
                    media_fields = ['video_file1', 'video_file2', 'video_file3', 'video_file4', 'video_file5', 'image_file1', 'image_file2', 'image_file3']
                    for field in media_fields:
                        if field in form.errors:
                            del form.errors[field]
                    
                    # Si le formulaire est valide (après suppression des erreurs de médias)
                    if not form.errors:
                        # 1. Créer l'utilisateur
                        from neads.core.models import User
                        user = User.objects.create(
                            email=data['email'],
                            first_name=data['first_name'],
                            last_name=data['last_name'],
                            role='creator',  # Rôle créateur
                            is_active=True,  # Compte actif immédiatement
                            password=make_password(data['password'])  # Hasher le mot de passe
                        )
                        
                        # 2. Créer la localisation
                        location = Location.objects.create(
                            full_address=data['full_address'],
                            latitude=data.get('latitude'),
                            longitude=data.get('longitude')
                        )
                        
                        # 3. Créer le profil créateur
                        # Calculer l'âge à partir de l'année de naissance
                        current_year = datetime.date.today().year
                        age = current_year - data['birth_year']
                        
                        # Créer le créateur avec les champs qui existent dans le modèle
                        creator = Creator.objects.create(
                            user=user,
                            first_name=data['first_name'],
                            last_name=data['last_name'],
                            gender=data['gender'],
                            age=age,  # Âge calculé à partir de birth_year
                            email=data['email'],
                            phone=data['phone'],
                            location=location,
                            bio=data['bio'],
                            equipment=data['equipment'],
                            previous_clients=data['previous_clients'],
                            can_invoice=data['can_invoice'] == 'true',  # Convertir la chaîne en booléen
                        )
                        
                        # 4. Ajouter les domaines d'expertise
                        creator.domains.set(data['domains'])
                        
                        # 5. Traiter la photo de profil
                        if 'featured_image' in request.FILES:
                            creator.featured_image = request.FILES['featured_image']
                            creator.save()
                        
                        # 6. Connecter l'utilisateur
                        login(request, user)
                        
                        # 7. Ajouter des logs pour déboguer
                        print(f"Créateur créé avec succès: ID={creator.id}, Email={creator.email}")
                        
                        # 8. Rediriger vers l'étape 2 avec l'ID du créateur
                        redirect_url = f"{reverse('temp_login_request')}?creator=1&step=2&creator_id={creator.id}"
                        print(f"Redirection vers: {redirect_url}")
                        
                        # 9. Utiliser JsonResponse pour afficher un message de succès et l'ID du créateur
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return JsonResponse({
                                'success': True,
                                'creator_id': creator.id,
                                'email': creator.email,
                                'redirect_url': redirect_url
                            })
                        
                        return redirect(redirect_url)
                else:
                    # Étape 2 - Traiter les médias
                    if creator_id:
                        creator = Creator.objects.get(id=creator_id)
                        print(f"Traitement des médias pour le créateur ID={creator.id}")
                        
                        # Traiter les vidéos
                        for i in range(1, 6):
                            field_name = f'video_file{i}'
                            if field_name in request.FILES:
                                video_file = request.FILES[field_name]
                                media = Media.objects.create(
                                    creator=creator,
                                    title=f"Vidéo {i}",
                                    media_type='video',
                                    file=video_file,
                                    is_verified=False
                                )
                                print(f"Vidéo {i} ajoutée: {media.id}")
                        
                        # Traiter les images
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
                                print(f"Image {i} ajoutée: {media.id}")
                        
                        messages.success(request, "Votre profil créateur a été créé avec succès !")
                        return redirect('creator_detail', creator_id=creator.id)
                    else:
                        print("Erreur: Aucun creator_id trouvé pour l'étape 2")
                        return redirect(f"{reverse('temp_login_request')}?creator=1")
            else:
                print(f"Erreurs de formulaire: {json.dumps(form.errors.as_json())}")
        else:
            form = CreatorRegistrationForm()
        
        if step == '1':
            template = 'core/creator_signup_step1.html'
            context = {
                'form': form,
                'is_creator_signup': True,
                'nominatim_url': settings.NOMINATIM_URL,
            }
            print(f"Rendu du template étape 1")
        else:
            template = 'core/creator_signup_step2.html'
            if creator_id:
                try:
                    creator = Creator.objects.get(id=creator_id)
                    context = {
                        'form': form,
                        'is_creator_signup': True,
                        'nominatim_url': settings.NOMINATIM_URL,
                        'creator': creator,
                    }
                    print(f"Rendu du template étape 2 pour créateur ID={creator_id}")
                except Creator.DoesNotExist:
                    print(f"Créateur avec ID={creator_id} non trouvé")
                    return redirect(f"{reverse('temp_login_request')}?creator=1")
            else:
                # Si pas d'ID dans l'URL, rediriger vers l'étape 1
                print("Pas de creator_id fourni pour l'étape 2, redirection vers étape 1")
                return redirect(f"{reverse('temp_login_request')}?creator=1")
        
        return render(request, template, context)
    
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


@csrf_exempt
def upload_media(request):
    """
    Vue pour gérer l'upload asynchrone des médias (vidéos et images).
    """
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        
        # Vérification de la taille du fichier (max 100MB)
        if file.size > 100 * 1024 * 1024:
            return JsonResponse({'success': False, 'error': 'Le fichier est trop volumineux. Maximum 100MB autorisé.'})
        
        # Vérification du type de fichier
        if file.content_type.startswith('video/'):
            media_type = 'video'
        elif file.content_type.startswith('image/'):
            media_type = 'image'
        else:
            return JsonResponse({'success': False, 'error': 'Type de fichier non supporté.'})
        
        # Génération d'un nom de fichier unique
        file_extension = os.path.splitext(file.name)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        
        # Sauvegarde du fichier
        try:
            fs = FileSystemStorage()
            filename = fs.save(unique_filename, file)
            file_url = fs.url(filename)
            
            return JsonResponse({
                'success': True,
                'file_url': file_url,
                'media_type': media_type,
                'filename': filename
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Aucun fichier n\'a été envoyé.'})
