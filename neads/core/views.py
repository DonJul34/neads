from django.shortcuts import render, redirect
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

from .models import User, UserProfile
from .forms import LoginForm, TemporaryLoginForm, UserProfileForm, SetPasswordForm
from .decorators import role_required


def home(request):
    """
    Page d'accueil du site.
    """
    return render(request, 'core/home.html')


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
    Vue pour demander un lien de connexion temporaire.
    """
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
