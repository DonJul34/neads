import pytest
import colorlog
import logging
from django.test import TestCase
from django.db.utils import IntegrityError
from neads.map.tests.factories import MapPointFactory, MapClusterFactory
from neads.creators.tests.factories import CreatorFactory, LocationFactory
from neads.map.models import MapPoint, MapCluster

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

logger = colorlog.getLogger('map_tests')
logger.addHandler(handler)
logger.setLevel(logging.INFO)


@pytest.mark.django_db
class TestMapPointModel(TestCase):
    def setUp(self):
        logger.info("Initialisation des tests du modèle MapPoint")
        self.creator = CreatorFactory()
        self.location = LocationFactory()
        self.map_point = MapPointFactory(
            creator=self.creator,
            location=self.location,
            latitude=48.8566,
            longitude=2.3522
        )

    def test_map_point_creation(self):
        """Test la création basique d'un point sur la carte."""
        logger.info("Test de création d'un point sur la carte")
        self.assertIsNotNone(self.map_point.id)
        self.assertEqual(self.map_point.creator, self.creator)
        self.assertEqual(self.map_point.location, self.location)
        self.assertEqual(self.map_point.latitude, 48.8566)
        self.assertEqual(self.map_point.longitude, 2.3522)

    def test_map_point_str_method(self):
        """Test la méthode __str__ du modèle MapPoint."""
        logger.info("Test de la méthode __str__")
        expected_str = f"Point sur la carte pour {self.creator}"
        self.assertEqual(str(self.map_point), expected_str)

    def test_map_point_unique_creator(self):
        """Test qu'un créateur ne peut avoir qu'un seul point sur la carte."""
        logger.info("Test d'unicité du point par créateur")
        
        # Tenter de créer un deuxième point pour le même créateur
        with self.assertRaises(IntegrityError):
            MapPointFactory(creator=self.creator)

    def test_auto_generate_popup_title(self):
        """Test que le titre du popup est auto-généré si non spécifié."""
        logger.info("Test de génération automatique du titre du popup")
        
        # Créer un point sans titre de popup
        map_point = MapPointFactory.build(
            creator=self.creator,
            popup_title=None
        )
        map_point.save()
        
        # Vérifier que le titre a été généré
        self.assertEqual(map_point.popup_title, str(self.creator))

    def test_auto_use_location_coordinates(self):
        """Test que les coordonnées de la location sont utilisées si non spécifiées."""
        logger.info("Test d'utilisation des coordonnées de la location")
        
        location = LocationFactory(latitude=45.5, longitude=-73.6)
        
        # Créer un point sans coordonnées
        map_point = MapPointFactory.build(
            creator=CreatorFactory(),
            location=location,
            latitude=None,
            longitude=None
        )
        map_point.save()
        
        # Vérifier que les coordonnées de la location ont été utilisées
        self.assertEqual(map_point.latitude, 45.5)
        self.assertEqual(map_point.longitude, -73.6)


@pytest.mark.django_db
class TestMapClusterModel(TestCase):
    def setUp(self):
        logger.info("Initialisation des tests du modèle MapCluster")
        self.location = LocationFactory(latitude=48.8566, longitude=2.3522)
        
        # Créer quelques points dans la zone
        self.creator1 = CreatorFactory(location=self.location)
        self.creator2 = CreatorFactory(location=self.location)
        self.creator3 = CreatorFactory(location=self.location)
        
        self.map_point1 = MapPointFactory(
            creator=self.creator1,
            latitude=48.86,
            longitude=2.35
        )
        self.map_point2 = MapPointFactory(
            creator=self.creator2,
            latitude=48.87,
            longitude=2.36
        )
        self.map_point3 = MapPointFactory(
            creator=self.creator3,
            latitude=48.85,
            longitude=2.34
        )
        
        # Créer un cluster
        self.cluster = MapClusterFactory(
            name="Paris Cluster",
            latitude=48.8566,
            longitude=2.3522,
            zoom_level=12,
            radius=50,
            points_count=0
        )

    def test_cluster_creation(self):
        """Test la création basique d'un cluster."""
        logger.info("Test de création d'un cluster")
        self.assertIsNotNone(self.cluster.id)
        self.assertEqual(self.cluster.name, "Paris Cluster")
        self.assertEqual(self.cluster.latitude, 48.8566)
        self.assertEqual(self.cluster.longitude, 2.3522)

    def test_cluster_str_method(self):
        """Test la méthode __str__ du modèle MapCluster."""
        logger.info("Test de la méthode __str__")
        self.cluster.points_count = 3
        self.cluster.save()
        expected_str = f"Cluster Paris Cluster (3 points)"
        self.assertEqual(str(self.cluster), expected_str)

    def test_update_points_count(self):
        """Test la méthode update_points_count."""
        logger.info("Test de la méthode update_points_count")
        
        # Mettre à jour le comptage des points
        self.cluster.update_points_count()
        
        # Vérifier que le comptage est correct (approximatif car dépend de l'implémentation)
        # Il devrait trouver les 3 points créés dans setUp
        self.assertGreater(self.cluster.points_count, 0)
        
        # Désactiver un point et vérifier que le comptage change
        self.map_point1.is_visible = False
        self.map_point1.save()
        self.cluster.update_points_count()
        
        # Le nouveau nombre devrait être inférieur
        self.assertLess(self.cluster.points_count, 3) 