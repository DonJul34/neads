from django.db import migrations, models

def create_initial_content_types(apps, schema_editor):
    ContentType = apps.get_model('creators', 'ContentType')
    
    # Créer les types de contenu de base
    content_types = [
        'Photos',
        'Vidéos',
        'Podcasts',
        'UGC',
        'Réseaux sociaux',
        'Portraits',
        'Événements',
        'Mode',
        'Produits',
        'Gastronomie',
        'Voyage',
        'Sport',
        'Animalier',
        'Beauté',
        'Lifestyle'
    ]
    
    for ct in content_types:
        ContentType.objects.create(name=ct)

class Migration(migrations.Migration):

    dependencies = [
        ('creators', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContentType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
            ],
        ),
        migrations.RemoveField(
            model_name='creator',
            name='content_types',
        ),
        migrations.AddField(
            model_name='creator',
            name='content_types',
            field=models.ManyToManyField(blank=True, related_name='creators', to='creators.ContentType'),
        ),
        migrations.RunPython(create_initial_content_types),
    ] 