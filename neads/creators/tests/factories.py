import factory
from factory.django import DjangoModelFactory
from django.utils import timezone
from neads.core.models import User
from neads.creators.models import Creator, Domain, ContentType, Location, Media, Rating, Favorite


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f'user{n}@example.com')
    password = factory.PostGenerationMethodCall('set_password', 'password')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    is_active = True
    role = 'client'


class DomainFactory(DjangoModelFactory):
    class Meta:
        model = Domain

    name = factory.Sequence(lambda n: f'Domain {n}')
    icon = factory.Faker('word')


class ContentTypeFactory(DjangoModelFactory):
    class Meta:
        model = ContentType

    name = factory.Sequence(lambda n: f'ContentType {n}')


class LocationFactory(DjangoModelFactory):
    class Meta:
        model = Location

    city = factory.Faker('city')
    country = factory.Faker('country')
    postal_code = factory.Faker('postcode')
    latitude = factory.Faker('latitude')
    longitude = factory.Faker('longitude')


class CreatorFactory(DjangoModelFactory):
    class Meta:
        model = Creator

    user = factory.SubFactory(UserFactory, role='creator')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    age = factory.Faker('random_int', min=18, max=70)
    gender = factory.Iterator(['M', 'F', 'O'])
    email = factory.Faker('email')
    location = factory.SubFactory(LocationFactory)
    bio = factory.Faker('paragraph')
    average_rating = factory.Faker('pyfloat', min_value=1, max_value=5)
    total_ratings = factory.Faker('random_int', min=0, max=100)
    total_clients = factory.Faker('random_int', min=0, max=50)
    verified_by_neads = factory.Faker('boolean')
    created_at = factory.LazyFunction(timezone.now)

    @factory.post_generation
    def domains(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for domain in extracted:
                self.domains.add(domain)
        else:
            # Ajouter 2 domaines par défaut
            self.domains.add(DomainFactory())
            self.domains.add(DomainFactory())

    @factory.post_generation
    def content_types(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for content_type in extracted:
                self.content_types.add(content_type)
        else:
            # Ajouter un type de contenu par défaut
            self.content_types.add(ContentTypeFactory())


class MediaFactory(DjangoModelFactory):
    class Meta:
        model = Media

    creator = factory.SubFactory(CreatorFactory)
    title = factory.Faker('sentence', nb_words=4)
    description = factory.Faker('paragraph')
    media_type = factory.Iterator(['image', 'video'])
    upload_date = factory.LazyFunction(timezone.now)
    is_verified = factory.Faker('boolean')
    order = factory.Sequence(lambda n: n)


class RatingFactory(DjangoModelFactory):
    class Meta:
        model = Rating

    creator = factory.SubFactory(CreatorFactory)
    user = factory.SubFactory(UserFactory)
    rating = factory.Faker('random_int', min=1, max=5)
    comment = factory.Faker('paragraph')
    created_at = factory.LazyFunction(timezone.now)
    is_verified = factory.Faker('boolean')
    has_experience = factory.Faker('boolean')


class FavoriteFactory(DjangoModelFactory):
    class Meta:
        model = Favorite

    creator = factory.SubFactory(CreatorFactory)
    user = factory.SubFactory(UserFactory)
    created_at = factory.LazyFunction(timezone.now)
    notes = factory.Faker('paragraph') 