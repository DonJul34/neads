import pytest
import colorlog
import logging
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from neads.creators.tests.factories import (
    CreatorFactory, DomainFactory, ContentTypeFactory, LocationFactory,
    MediaFactory, RatingFactory, FavoriteFactory, UserFactory
)
from neads.creators.models import Creator, Media, Rating

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

logger = colorlog.getLogger('creators_tests')
logger.addHandler(handler)
logger.setLevel(logging.INFO)


@pytest.mark.django_db
class TestCreatorModel(TestCase):
    def setUp(self):
        logger.info("Initialisation des tests du modèle Creator")
        self.domain = DomainFactory()
        self.content_type = ContentTypeFactory()
        self.location = LocationFactory()
        self.creator = CreatorFactory(
            location=self.location,
            domains=[self.domain],
            content_types=[self.content_type]
        )

    def test_creator_creation(self):
        """Test la création basique d'un créateur."""
        logger.info("Test de création d'un créateur")
        self.assertIsNotNone(self.creator.id)
        self.assertEqual(self.creator.full_name, f"{self.creator.first_name} {self.creator.last_name}")
        self.assertEqual(self.creator.location, self.location)
        self.assertIn(self.domain, self.creator.domains.all())
        self.assertIn(self.content_type, self.creator.content_types.all())

    def test_age_validation(self):
        """Test la validation de l'âge (entre 13 et 100)."""
        logger.info("Test de validation de l'âge")
        
        # Âge trop bas (< 13)
        with self.assertRaises(ValidationError):
            creator = CreatorFactory.build(age=10)
            creator.full_clean()
        
        # Âge trop élevé (> 100)
        with self.assertRaises(ValidationError):
            creator = CreatorFactory.build(age=101)
            creator.full_clean()
        
        # Âges valides
        creator_min = CreatorFactory.build(age=13)
        creator_max = CreatorFactory.build(age=100)
        creator_mid = CreatorFactory.build(age=30)
        
        creator_min.full_clean()  # Ne devrait pas générer d'erreur
        creator_max.full_clean()  # Ne devrait pas générer d'erreur
        creator_mid.full_clean()  # Ne devrait pas générer d'erreur

    def test_str_method(self):
        """Test la méthode __str__ du modèle Creator."""
        logger.info("Test de la méthode __str__")
        self.assertEqual(str(self.creator), self.creator.full_name)

    def test_update_ratings(self):
        """Test la méthode update_ratings."""
        logger.info("Test de la méthode update_ratings")
        # Création de ratings pour le créateur
        RatingFactory(creator=self.creator, rating=5)
        RatingFactory(creator=self.creator, rating=4)
        RatingFactory(creator=self.creator, rating=3)
        
        # Mise à jour des notations
        self.creator.update_ratings()
        
        # Vérifier que la moyenne et le total ont été mis à jour correctement
        self.assertEqual(self.creator.total_ratings, 3)
        self.assertEqual(float(self.creator.average_rating), 4.0)  # (5+4+3)/3 = 4.0

    def test_get_image_count(self):
        """Test la méthode get_image_count."""
        logger.info("Test de la méthode get_image_count")
        # Créer des médias de type image
        MediaFactory(creator=self.creator, media_type='image')
        MediaFactory(creator=self.creator, media_type='image')
        # Créer un média de type vidéo
        MediaFactory(creator=self.creator, media_type='video')
        
        # Vérifier que le comptage est correct
        self.assertEqual(self.creator.get_image_count(), 2)

    def test_get_video_count(self):
        """Test la méthode get_video_count."""
        logger.info("Test de la méthode get_video_count")
        # Créer des médias de type vidéo
        MediaFactory(creator=self.creator, media_type='video')
        # Créer des médias de type image
        MediaFactory(creator=self.creator, media_type='image')
        MediaFactory(creator=self.creator, media_type='image')
        
        # Vérifier que le comptage est correct
        self.assertEqual(self.creator.get_video_count(), 1)

    def test_has_social_links(self):
        """Test la méthode has_social_links."""
        logger.info("Test de la méthode has_social_links")
        
        # Sans liens sociaux
        creator_no_links = CreatorFactory(
            youtube_link=None,
            tiktok_link=None,
            instagram_link=None
        )
        self.assertFalse(creator_no_links.has_social_links())
        
        # Avec lien YouTube
        creator_youtube = CreatorFactory(
            youtube_link='https://youtube.com/channel/123',
            tiktok_link=None,
            instagram_link=None
        )
        self.assertTrue(creator_youtube.has_social_links())
        
        # Avec plusieurs liens
        creator_multiple = CreatorFactory(
            youtube_link='https://youtube.com/channel/123',
            tiktok_link='https://tiktok.com/@user',
            instagram_link='https://instagram.com/user'
        )
        self.assertTrue(creator_multiple.has_social_links())


@pytest.mark.django_db
class TestMediaModel(TestCase):
    def setUp(self):
        logger.info("Initialisation des tests du modèle Media")
        self.creator = CreatorFactory()

    def test_media_creation(self):
        """Test la création basique d'un média."""
        logger.info("Test de création d'un média")
        media = MediaFactory(creator=self.creator, media_type='image')
        self.assertIsNotNone(media.id)
        self.assertEqual(media.creator, self.creator)
        self.assertEqual(media.media_type, 'image')

    def test_media_limit(self):
        """Test la limitation du nombre de médias par créateur."""
        logger.info("Test de limitation du nombre de médias")
        
        # Créer 10 images
        for _ in range(10):
            MediaFactory(creator=self.creator, media_type='image')
        
        # La 11ème devrait échouer
        with self.assertRaises(ValueError):
            MediaFactory(creator=self.creator, media_type='image')
        
        # Créer 10 vidéos
        for _ in range(10):
            MediaFactory(creator=self.creator, media_type='video')
        
        # La 11ème devrait échouer
        with self.assertRaises(ValueError):
            MediaFactory(creator=self.creator, media_type='video')


@pytest.mark.django_db
class TestRatingModel(TestCase):
    def setUp(self):
        logger.info("Initialisation des tests du modèle Rating")
        self.creator = CreatorFactory()
        self.user = UserFactory()

    def test_rating_creation(self):
        """Test la création basique d'une évaluation."""
        logger.info("Test de création d'une évaluation")
        rating = RatingFactory(creator=self.creator, user=self.user, rating=4)
        self.assertIsNotNone(rating.id)
        self.assertEqual(rating.creator, self.creator)
        self.assertEqual(rating.user, self.user)
        self.assertEqual(rating.rating, 4)

    def test_rating_update_creator(self):
        """Test que la création d'une évaluation met à jour les stats du créateur."""
        logger.info("Test de mise à jour des stats du créateur après évaluation")
        
        # Enregistrer les valeurs initiales
        initial_avg = self.creator.average_rating
        initial_count = self.creator.total_ratings
        
        # Créer une nouvelle évaluation
        rating = RatingFactory(creator=self.creator, user=self.user, rating=5)
        
        # Vérifier que les stats du créateur ont été mises à jour
        creator_updated = Creator.objects.get(id=self.creator.id)
        self.assertNotEqual(creator_updated.average_rating, initial_avg)
        self.assertEqual(creator_updated.total_ratings, initial_count + 1)

    def test_unique_rating_per_user(self):
        """Test qu'un utilisateur ne peut pas évaluer deux fois le même créateur."""
        logger.info("Test d'unicité des évaluations par utilisateur")
        
        # Première évaluation
        RatingFactory(creator=self.creator, user=self.user, rating=4)
        
        # Une deuxième évaluation du même utilisateur pour le même créateur devrait échouer
        with self.assertRaises(IntegrityError):
            RatingFactory(creator=self.creator, user=self.user, rating=5)


@pytest.mark.django_db
class TestFavoriteModel(TestCase):
    def setUp(self):
        logger.info("Initialisation des tests du modèle Favorite")
        self.creator = CreatorFactory()
        self.user = UserFactory()

    def test_favorite_creation(self):
        """Test la création basique d'un favori."""
        logger.info("Test de création d'un favori")
        favorite = FavoriteFactory(creator=self.creator, user=self.user)
        self.assertIsNotNone(favorite.id)
        self.assertEqual(favorite.creator, self.creator)
        self.assertEqual(favorite.user, self.user)

    def test_unique_favorite_per_user(self):
        """Test qu'un utilisateur ne peut pas mettre en favori deux fois le même créateur."""
        logger.info("Test d'unicité des favoris par utilisateur")
        
        # Premier favori
        FavoriteFactory(creator=self.creator, user=self.user)
        
        # Un deuxième favori du même utilisateur pour le même créateur devrait échouer
        with self.assertRaises(IntegrityError):
            FavoriteFactory(creator=self.creator, user=self.user) 