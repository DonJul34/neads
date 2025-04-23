from django.shortcuts import redirect
from django.urls import reverse
from django.http import HttpResponseForbidden
import logging
import re

from neads.creators.models import Creator, Location

logger = logging.getLogger(__name__)

class CreatorRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Liste des URLs qui ne nécessitent pas de redirection
        excluded_urls = [
            '/login/',
            '/logout/',
            '/creators/edit/',
            '/creators/upload-media/',
            '/admin/',
            '/static/',
            '/media/',
        ]
        
        # Si l'URL correspond à /creators/detail/{id}/, ne pas rediriger
        if re.match(r'^/creators/detail/\d+/$', request.path):
            # On laisse passer la requête vers creator_detail
            return self.get_response(request)

        # Vérifier si l'utilisateur est un créateur et est connecté
        if request.user.is_authenticated and request.user.has_role('creator'):
            logger.info(f"Middleware: Utilisateur créateur {request.user.email} accède à {request.path}")
            
            # Vérifier si l'utilisateur a un profil créateur
            has_profile = hasattr(request.user, 'creator_profile') and request.user.creator_profile
            if has_profile:
                logger.info(f"Middleware: Le créateur a un profil existant (ID: {request.user.creator_profile.id})")
            else:
                logger.info(f"Middleware: Le créateur n'a pas encore de profil")
                
                # Si on est en train d'accéder à la page de création de profil, laisser passer la requête
                if request.path == '/creators/add/':
                    logger.info(f"Middleware: Accès à la page de création de profil autorisé")
                    return self.get_response(request)
                    
                # Sinon, créer un profil vide pour le créateur
                try:
                    logger.info(f"Middleware: Création automatique d'un profil vide pour le créateur {request.user.email}")
                    location = Location.objects.create()
                    creator = Creator.objects.create(
                        user=request.user,
                        email=request.user.email,
                        first_name=request.user.first_name or "",
                        last_name=request.user.last_name or "",
                        full_name=f"{request.user.first_name} {request.user.last_name}".strip() or request.user.email,
                        location=location,
                        age=18,  # Age minimum par défaut
                        gender='M',  # Genre par défaut, à modifier par l'utilisateur
                        bio="",  # Biographie vide par défaut
                    )
                    logger.info(f"Middleware: Profil créateur créé avec succès (ID: {creator.id})")
                    
                    # Rediriger vers la page d'édition du profil
                    logger.info(f"Middleware: Redirection vers la page d'édition du profil")
                    if request.path != f'/creators/edit/{creator.id}/':
                        return redirect('creator_edit', creator_id=creator.id)
                except Exception as e:
                    logger.error(f"Middleware: Erreur lors de la création du profil: {str(e)}")
                    # En cas d'erreur, continuer vers la page de création
                    if request.path != '/creators/add/':
                        return redirect('creator_add')
            
            # Vérifier si l'utilisateur essaie d'accéder à une page de détail d'un autre créateur
            if request.path.startswith('/creators/detail/'):
                try:
                    # Extraire l'ID du créateur de l'URL
                    creator_id = int(request.path.split('/')[-2])
                    # Vérifier si c'est bien son profil
                    if has_profile:
                        if request.user.creator_profile.id != creator_id:
                            logger.warning(f"Middleware: Tentative d'accès non autorisée au profil {creator_id} par {request.user.email}")
                            return HttpResponseForbidden("Vous n'avez pas accès à ce profil.")
                        else:
                            logger.info(f"Middleware: Accès autorisé au profil {creator_id}")
                            # Laisser passer la requête
                            return self.get_response(request)
                    else:
                        # Cela ne devrait plus arriver car nous créons automatiquement un profil
                        logger.info(f"Middleware: Redirection vers la page de création de profil car le créateur n'a pas de profil")
                        return redirect('creator_add')
                except (ValueError, IndexError) as e:
                    logger.error(f"Middleware: Erreur lors de l'extraction de l'ID du créateur: {str(e)}")

            # Vérifier si l'URL actuelle n'est pas dans la liste des URLs exclues
            should_redirect = not any(request.path.startswith(url) for url in excluded_urls)
            if should_redirect:
                logger.info(f"Middleware: Redirection nécessaire pour {request.path}")
                try:
                    # Vérifier si le créateur a un profil
                    if has_profile:
                        # Rediriger vers la page de profil du créateur
                        logger.info(f"Middleware: Redirection vers le profil {request.user.creator_profile.id}")
                        return redirect('creator_detail', creator_id=request.user.creator_profile.id)
                    else:
                        # Rediriger vers la page de création de profil
                        # (Ce cas ne devrait plus arriver car nous créons automatiquement un profil)
                        logger.info(f"Middleware: Redirection vers la page de création de profil")
                        return redirect('creator_add')
                except Exception as e:
                    # En cas d'erreur, rediriger vers la page de création de profil
                    logger.error(f"Middleware: Erreur lors de la redirection: {str(e)}")
                    return redirect('creator_add')

        response = self.get_response(request)
        return response 