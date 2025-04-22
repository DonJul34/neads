#!/bin/bash

# Créer un nouvel environnement virtuel Python
python3.11 -m venv venv

# Activer l'environnement virtuel (Linux)
source venv/bin/activate

# Installer les dépendances principales
pip install --upgrade pip
pip install django==4.2.7
pip install djangorestframework
pip install psycopg2-binary
pip install pillow
pip install python-dotenv
pip install django-cors-headers

# Vérifier l'installation de Django
python -c "import django; print(django.get_version())"

# Créer le projet Django (uniquement si manage.py n'existe pas)
if [ ! -f manage.py ]; then
    django-admin startproject neads .
fi

# Créer les applications principales (style Linux avec /)
mkdir -p neads/core
mkdir -p neads/creators
mkdir -p neads/map

python manage.py startapp core neads/core
python manage.py startapp creators neads/creators
python manage.py startapp map neads/map

# Générer un requirements.txt avec les dépendances
pip freeze > requirements.txt

# Créer la base de données et effectuer les migrations
python manage.py makemigrations
python manage.py migrate

echo "L'environnement Django est configuré avec succès!"
echo "Pour démarrer le serveur de développement:"
echo "  source venv/bin/activate"
echo "  python manage.py runserver 0.0.0.0:8000" 