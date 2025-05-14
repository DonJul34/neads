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
    if not request.user.is_authenticated:
        return redirect('login')
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


def creator_registration_view(request):
    """
    Vue pour l'inscription des nouveaux créateurs en plusieurs étapes.
    """
    from neads.creators.forms import CreatorRegistrationForm
    from neads.creators.models import Creator, Location, Media # Assurez-vous que Media est bien utilisé ici ou dans le form
    import json # Si vous utilisez json.dumps pour les erreurs

    step = request.GET.get('step', '1')
    creator_id = request.GET.get('creator_id')

    if request.method == 'POST':
        form = CreatorRegistrationForm(request.POST, request.FILES)
        # Récupérer l'étape du formulaire soumis pour s'assurer qu'on traite la bonne logique
        form_step = request.POST.get('step', '1') 

        if form_step == '1':
            # Logique de l'étape 1 de CreatorRegistrationForm
            # On ignore les erreurs des champs de médias pour l'étape 1
            media_fields = [
                'video_file1', 'video_file2', 'video_file3', 'video_file4', 'video_file5',
                'image_file1', 'image_file2', 'image_file3'
            ]
            # On ne supprime les erreurs que si le formulaire est invalide à cause de ces champs
            # et qu'on est bien en train de traiter une soumission de l'étape 1.
            if not form.is_valid():
                current_errors = form.errors.copy()
                for field in media_fields:
                    if field in current_errors:
                        del current_errors[field]
                # Si après suppression des erreurs médias, il n'y a plus d'erreurs, c'est une validation partielle pour l'étape 1
                if not current_errors and form.is_valid(skip_media_fields=True): # Vous devrez ajouter un argument à is_valid dans le form
                    pass # On continue le traitement de l'étape 1
                elif not current_errors:
                     # Si le form n'est toujours pas valide même en ignorant les champs media, 
                     # ou si form.is_valid() est appelé sans skip_media_fields, on rend le form avec erreurs
                    pass # Laisser le form.is_valid() plus bas gérer les erreurs

            if form.is_valid(): # Ce is_valid doit gérer la logique de skip_media_fields ou être appelé conditionnellement
                data = form.cleaned_data
                user = User.objects.create(
                    email=data['email'],
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    role='creator',
                    is_active=True,
                    password=make_password(data['password'])
                )
                location = Location.objects.create(
                    full_address=data['full_address'],
                    latitude=data.get('latitude'),
                    longitude=data.get('longitude')
                )
                current_year = datetime.date.today().year
                age = current_year - data['birth_year']
                creator = Creator.objects.create(
                    user=user,
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    gender=data['gender'],
                    age=age,
                    email=data['email'],
                    phone=data['phone'],
                    location=location,
                    bio=data['bio'],
                    equipment=data['equipment'],
                    previous_clients=data['previous_clients'],
                    can_invoice=data['can_invoice'] == 'true'
                )
                creator.domains.set(data['domains'])
                if 'featured_image' in request.FILES:
                    creator.featured_image = request.FILES['featured_image']
                    creator.save()
                login(request, user)
                
                # Redirection vers l'étape 2
                # Il faut s'assurer que creator.id est disponible ici
                redirect_url = reverse('creator_register') + f'?step=2&creator_id={creator.id}'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'creator_id': creator.id,
                        'redirect_url': redirect_url
                    })
                return redirect(redirect_url)
            else:
                # Si le formulaire de l'étape 1 n'est pas valide (même après avoir potentiellement ignoré les champs médias)
                step = '1' # S'assurer qu'on retourne au template de l'étape 1
        
        elif form_step == '2':
            # Logique de l'étape 2 : traitement des médias
            # Il faut récupérer creator_id du POST ou de la session/GET
            creator_id_from_post = request.POST.get('creator_id') 
            if creator_id_from_post:
                try:
                    creator = Creator.objects.get(id=creator_id_from_post)
                    # Assurez-vous que l'utilisateur connecté est bien celui qui a créé ce profil
                    if request.user.is_authenticated and request.user == creator.user:
                        # Le form.is_valid() ici devrait se concentrer sur les champs médias
                        # Il faudrait peut-être un form distinct ou une logique de validation adaptée pour l'étape 2.
                        # Pour l'instant, on suppose que CreatorRegistrationForm peut gérer cela.
                        if form.is_valid(): # Ce is_valid devrait vérifier les champs médias
                            # Traiter les vidéos
                            for i in range(1, 6):
                                field_name = f'video_file{i}'
                                if field_name in request.FILES:
                                    Media.objects.create(
                                        creator=creator, title=f"Vidéo {i}", media_type='video',
                                        file=request.FILES[field_name], is_verified=False
                                    )
                            # Traiter les images
                            for i in range(1, 4):
                                field_name = f'image_file{i}'
                                if field_name in request.FILES:
                                    Media.objects.create(
                                        creator=creator, title=f"Image {i}", media_type='image',
                                        file=request.FILES[field_name], is_verified=False
                                    )
                            messages.success(request, "Votre profil créateur a été créé avec succès !")
                            return redirect('creator_detail', creator_id=creator.id)
                        else:
                            step = '2' # Rester sur l'étape 2 si le formulaire média n'est pas valide
                    else:
                        messages.error(request, "Action non autorisée.")
                        return redirect(reverse('creator_register') + '?step=1')
                except Creator.DoesNotExist:
                    messages.error(request, "Profil créateur non trouvé.")
                    return redirect(reverse('creator_register') + '?step=1')
            else:
                messages.error(request, "ID Créateur manquant pour l'étape 2.")
                step = '1' # Rediriger vers l'étape 1 si pas d'ID
    else:
        # Logique GET pour afficher le formulaire vide de l'étape appropriée
        initial_data = {}
        if step == '2' and creator_id:
            try:
                creator = Creator.objects.get(id=creator_id)
                # S'assurer que l'utilisateur est autorisé à voir cette étape
                if not (request.user.is_authenticated and request.user == creator.user):
                    messages.error(request, "Vous devez être connecté avec le bon compte pour accéder à cette étape.")
                    return redirect(reverse('creator_register') + '?step=1')
                initial_data['creator_id'] = creator.id # Passer l'ID au template si besoin
            except Creator.DoesNotExist:
                messages.error(request, "Profil créateur non trouvé pour l'étape 2.")
                return redirect(reverse('creator_register') + '?step=1')
        
        form = CreatorRegistrationForm(initial=initial_data)

    # Déterminer le template à rendre en fonction de l'étape
    if step == '1':
        template_name = 'core/creator_signup_step1.html'
    elif step == '2' and creator_id: # S'assurer que creator_id existe pour l'étape 2
        template_name = 'core/creator_signup_step2.html'
    else: # Cas par défaut ou erreur, rediriger vers l'étape 1
        messages.error(request, "Étape d'inscription invalide.")
        return redirect(reverse('creator_register') + '?step=1')

    context = {
        'form': form,
        'step': step,
        'creator_id': creator_id, # Passer creator_id au contexte pour l'étape 2
        'nominatim_url': settings.NOMINATIM_URL,
    }
    # Pour l'étape 2, on pourrait vouloir passer l'objet creator au template
    if step == '2' and 'creator' not in context and creator_id:
        try: context['creator'] = Creator.objects.get(id=creator_id)
        except Creator.DoesNotExist: pass

    return render(request, template_name, context)


def temporary_login_request(request):
    """
    Vue pour demander un lien de connexion temporaire pour les clients existants.
    L'inscription créateur est maintenant gérée par creator_registration_view.
    """
    if request.method == 'POST':
        form = TemporaryLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user, created = User.objects.get_or_create(
                email=email,
                defaults={'role': 'client'}
            )
            token = user.generate_temp_login_token()
            temp_login_url = request.build_absolute_uri(
                reverse('temp_login', kwargs={'token': token, 'email': email})
            )
            subject = 'Votre lien de connexion NEADS'
            message = render_to_string('core/emails/temp_login_email.html', {
                'user': user,
                'temp_login_url': temp_login_url,
                'expiry_hours': 24,
            })
            send_mail(
                subject=subject, message=message, from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email], html_message=message,
            )
            return render(request, 'core/temp_login_sent.html', {'email': email})
    else:
        form = TemporaryLoginForm()
    
    # is_creator_signup n'est plus nécessaire ici
    return render(request, 'core/temp_login_request.html', {'form': form})


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
