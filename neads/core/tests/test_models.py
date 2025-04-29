import pytest
import colorlog
import logging
from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta
from freezegun import freeze_time
from neads.core.models import User, UserProfile

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

logger = colorlog.getLogger('core_tests')
logger.addHandler(handler)
logger.setLevel(logging.INFO)


@pytest.mark.django_db
class TestUserModel(TestCase):
    def setUp(self):
        logger.info("Initialisation des tests du modèle User")
        self.user_data = {
            'email': 'test@example.com',
            'password': 'securepassword',
            'first_name': 'John',
            'last_name': 'Doe',
            'role': 'client'
        }
        self.user = User.objects.create_user(**self.user_data)

    def test_user_creation(self):
        """Test la création basique d'un utilisateur."""
        logger.info("Test de création d'un utilisateur")
        self.assertEqual(self.user.email, self.user_data['email'])
        self.assertEqual(self.user.first_name, self.user_data['first_name'])
        self.assertEqual(self.user.last_name, self.user_data['last_name'])
        self.assertTrue(self.user.is_active)
        self.assertFalse(self.user.is_staff)
        self.assertEqual(self.user.role, 'client')

    def test_user_str_method(self):
        """Test la méthode __str__ du modèle User."""
        logger.info("Test de la méthode __str__")
        self.assertEqual(str(self.user), self.user_data['email'])

    def test_get_full_name(self):
        """Test la méthode get_full_name."""
        logger.info("Test de la méthode get_full_name")
        expected_full_name = f"{self.user_data['first_name']} {self.user_data['last_name']}"
        self.assertEqual(self.user.get_full_name(), expected_full_name)

    def test_has_role(self):
        """Test la méthode has_role."""
        logger.info("Test de la méthode has_role")
        self.assertTrue(self.user.has_role('client'))
        self.assertFalse(self.user.has_role('admin'))

    def test_create_superuser(self):
        """Test la création d'un superutilisateur."""
        logger.info("Test de création d'un superutilisateur")
        admin = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpassword'
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertEqual(admin.role, 'admin')

    @freeze_time("2023-01-01 12:00:00")
    def test_temp_login_token(self):
        """Test la génération et validation de token temporaire."""
        logger.info("Test du système de token temporaire")
        token = self.user.generate_temp_login_token()
        self.assertIsNotNone(token)
        self.assertEqual(self.user.temp_login_token, token)
        
        # Le token doit être valide maintenant
        self.assertTrue(self.user.is_temp_token_valid(token))
        
        # Le token ne doit pas être valide avec une mauvaise valeur
        self.assertFalse(self.user.is_temp_token_valid('wrong_token'))
        
        # Avancer le temps de 25 heures pour tester l'expiration
        with freeze_time("2023-01-02 13:00:00"):
            self.assertFalse(self.user.is_temp_token_valid(token))


@pytest.mark.django_db
class TestUserProfileModel(TestCase):
    def setUp(self):
        logger.info("Initialisation des tests du modèle UserProfile")
        self.user = User.objects.create_user(
            email='test@example.com',
            password='securepassword',
            first_name='John',
            last_name='Doe'
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            phone_number='1234567890',
            company_name='Test Company'
        )

    def test_profile_creation(self):
        """Test la création d'un profil utilisateur."""
        logger.info("Test de création d'un profil utilisateur")
        self.assertEqual(self.profile.user, self.user)
        self.assertEqual(self.profile.phone_number, '1234567890')
        self.assertEqual(self.profile.company_name, 'Test Company')
        self.assertFalse(self.profile.verified_email)
        self.assertFalse(self.profile.verified_phone)

    def test_profile_str_method(self):
        """Test la méthode __str__ du profil."""
        logger.info("Test de la méthode __str__ du profil")
        expected_str = f"Profil de {self.user.email}"
        self.assertEqual(str(self.profile), expected_str)

    def test_profile_cascade_delete(self):
        """Test que le profil est supprimé en cascade si l'utilisateur est supprimé."""
        logger.info("Test de suppression en cascade du profil")
        profile_id = self.profile.id
        self.user.delete()
        with self.assertRaises(UserProfile.DoesNotExist):
            UserProfile.objects.get(id=profile_id) 