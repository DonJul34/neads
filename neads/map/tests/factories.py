import factory
from factory.django import DjangoModelFactory
from django.utils import timezone
from neads.map.models import MapPoint, MapCluster
from neads.creators.tests.factories import CreatorFactory, LocationFactory


class MapPointFactory(DjangoModelFactory):
    class Meta:
        model = MapPoint

    creator = factory.SubFactory(CreatorFactory)
    location = factory.SubFactory(LocationFactory)
    latitude = factory.Faker('latitude')
    longitude = factory.Faker('longitude')
    popup_title = factory.Faker('sentence', nb_words=4)
    popup_content = factory.Faker('paragraph')
    icon_type = factory.Iterator(['default', 'premium', 'featured'])
    is_visible = True
    created_at = factory.LazyFunction(timezone.now)


class MapClusterFactory(DjangoModelFactory):
    class Meta:
        model = MapCluster

    name = factory.Sequence(lambda n: f'Cluster {n}')
    latitude = factory.Faker('latitude')
    longitude = factory.Faker('longitude')
    zoom_level = factory.Iterator([8, 10, 12, 14])
    radius = factory.Iterator([25, 50, 100])
    points_count = factory.Faker('random_int', min=0, max=100)
    created_at = factory.LazyFunction(timezone.now)
    is_dynamic = factory.Faker('boolean') 