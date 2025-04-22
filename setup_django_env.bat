@echo off
REM Créer un nouvel environnement virtuel Python
python -m venv venv

REM Activer l'environnement virtuel
call venv\Scripts\activate.bat

REM Installer les dépendances principales
pip install django==4.2.7
pip install djangorestframework
pip install psycopg2-binary
pip install pillow
pip install python-dotenv
pip install django-cors-headers

REM Créer le projet Django
django-admin startproject neads .

REM Créer les applications principales
mkdir neads\core
mkdir neads\creators
mkdir neads\map

python manage.py startapp core neads\core
python manage.py startapp creators neads\creators
python manage.py startapp map neads\map

REM Créer un requirements.txt avec les dépendances
pip freeze > requirements.txt

REM Message de confirmation
echo.
echo L'environnement Django est configuré avec succès!
echo Pour démarrer le projet:
echo 1. Activez l'environnement: venv\Scripts\activate.bat
echo 2. Lancez le serveur: python manage.py runserver
echo. 