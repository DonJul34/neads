import pytest
import colorlog
import logging
from django.test import TestCase, Client
from django.urls import reverse
from neads.core.models import User

# Configuration de colorlog
handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s%(levelname)s:%(name)s:%(message)s',
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    }
))

logger = colorlog.getLogger('core_view_tests')
logger.addHandler(handler)
logger.setLevel(logging.INFO)


@pytest.mark.django_db
class TestLoginView(TestCase):
    def setUp(self):
        logger.info("Initialisation des tests des vues d'authentification")
        self.client = Client()
        self.login_url = reverse('login')
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpassword123',
            role='client'
        )

    def test_login_page_load(self):
        """Test que la page de connexion se charge correctement."""
        logger.info("Test du chargement de la page de connexion")
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/login.html')

    def test_login_success(self):
        """Test qu'un utilisateur peut se connecter avec succès."""
        logger.info("Test de connexion réussie")
        response = self.client.post(self.login_url, {
            'username': 'testuser@example.com',
            'password': 'testpassword123'
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Vérifier que l'utilisateur est connecté
        self.assertTrue(response.context['user'].is_authenticated)
        self.assertEqual(response.context['user'].email, 'testuser@example.com')

    def test_login_wrong_credentials(self):
        """Test qu'un utilisateur ne peut pas se connecter avec des mauvaises informations."""
        logger.info("Test de connexion avec mauvaises informations")
        response = self.client.post(self.login_url, {
            'username': 'testuser@example.com',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)
        
        # Vérifier que le formulaire contient une erreur
        self.assertFalse(response.context['user'].is_authenticated)
        self.assertTrue(response.context['form'].errors)


@pytest.mark.django_db
class TestCreatorRedirectMiddleware(TestCase):
    def setUp(self):
        logger.info("Initialisation des tests du middleware de redirection des créateurs")
        self.client = Client()
        self.home_url = reverse('home')
        
        # Créer un utilisateur avec le rôle creator
        self.creator_user = User.objects.create_user(
            email='creator@example.com',
            password='creatorpass',
            role='creator'
        )
        
        # Créer un utilisateur client normal
        self.client_user = User.objects.create_user(
            email='client@example.com',
            password='clientpass',
            role='client'
        )

    def test_creator_redirect(self):
        """
        Test que le middleware redirige les utilisateurs avec le rôle creator
        vers leur profil ou la création de profil.
        """
        logger.info("Test de redirection des créateurs")
        
        # Connecter l'utilisateur creator
        self.client.login(username='creator@example.com', password='creatorpass')
        
        # Accéder à la page d'accueil - devrait rediriger vers la création de profil
        # puisque l'utilisateur n'a pas encore de profil creator
        response = self.client.get(self.home_url, follow=True)
        
        # Vérifier que la redirection a eu lieu (le code peut varier selon l'implémentation)
        # On vérifie ici uniquement qu'il y a eu une redirection
        self.assertGreater(len(response.redirect_chain), 0)

    def test_non_creator_no_redirect(self):
        """
        Test que le middleware ne redirige pas les utilisateurs qui n'ont pas
        le rôle creator.
        """
        logger.info("Test qu'il n'y a pas de redirection pour les non-créateurs")
        
        # Connecter l'utilisateur client
        self.client.login(username='client@example.com', password='clientpass')
        
        # Accéder à la page d'accueil - ne devrait pas rediriger
        response = self.client.get(self.home_url)
        
        # Vérifier qu'il n'y a pas eu de redirection
        self.assertEqual(response.status_code, 200) 