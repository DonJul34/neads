# Generated by Django 5.2 on 2025-04-20 08:51

import django.core.validators
import django.db.models.deletion
import neads.creators.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Domain',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('icon', models.CharField(blank=True, max_length=50, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Location',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('city', models.CharField(max_length=100)),
                ('country', models.CharField(max_length=100)),
                ('postal_code', models.CharField(blank=True, max_length=20, null=True)),
                ('latitude', models.FloatField(blank=True, null=True)),
                ('longitude', models.FloatField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Creator',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=50)),
                ('last_name', models.CharField(max_length=50)),
                ('full_name', models.CharField(blank=True, max_length=100)),
                ('age', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(13), django.core.validators.MaxValueValidator(100)])),
                ('gender', models.CharField(choices=[('M', 'Homme'), ('F', 'Femme'), ('O', 'Autre')], max_length=1)),
                ('email', models.EmailField(max_length=254)),
                ('phone', models.CharField(blank=True, max_length=20, null=True)),
                ('bio', models.TextField(blank=True, null=True)),
                ('equipment', models.CharField(blank=True, max_length=255, null=True)),
                ('delivery_time', models.CharField(blank=True, max_length=50, null=True)),
                ('content_types', models.CharField(blank=True, choices=[('video', 'Vidéo'), ('image', 'Image'), ('audio', 'Audio'), ('ugc_duo', 'UGC Duo'), ('animal', 'Animal')], max_length=100, null=True)),
                ('mobility', models.BooleanField(default=False)),
                ('can_invoice', models.BooleanField(default=False)),
                ('previous_clients', models.TextField(blank=True, null=True)),
                ('average_rating', models.DecimalField(decimal_places=2, default=0.0, max_digits=3)),
                ('total_ratings', models.PositiveIntegerField(default=0)),
                ('verified_by_neads', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('last_activity', models.DateTimeField(blank=True, null=True)),
                ('user', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='creator_profile', to=settings.AUTH_USER_MODEL)),
                ('domains', models.ManyToManyField(related_name='creators', to='creators.domain')),
                ('location', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='creators', to='creators.location')),
            ],
        ),
        migrations.CreateModel(
            name='Media',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(blank=True, max_length=100, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('media_type', models.CharField(choices=[('image', 'Image'), ('video', 'Vidéo')], max_length=5)),
                ('file', models.FileField(blank=True, null=True, upload_to=neads.creators.models.image_upload_path)),
                ('video_file', models.FileField(blank=True, null=True, upload_to=neads.creators.models.video_upload_path)),
                ('thumbnail', models.ImageField(blank=True, null=True, upload_to=neads.creators.models.image_upload_path)),
                ('duration', models.PositiveIntegerField(blank=True, null=True)),
                ('upload_date', models.DateTimeField(auto_now_add=True)),
                ('order', models.PositiveIntegerField(default=0)),
                ('is_verified', models.BooleanField(default=False)),
                ('creator', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='media', to='creators.creator')),
            ],
            options={
                'ordering': ['order', '-upload_date'],
            },
        ),
        migrations.CreateModel(
            name='Favorite',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('creator', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favorites', to='creators.creator')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favorites', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('creator', 'user')},
            },
        ),
        migrations.CreateModel(
            name='Rating',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ('comment', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_verified', models.BooleanField(default=False)),
                ('creator', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ratings', to='creators.creator')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ratings', to=settings.AUTH_USER_MODEL)),
                ('verified_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='verified_ratings', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('creator', 'user')},
            },
        ),
    ]
