@echo off
echo ===== NEADS - Configuration des données de test =====

REM Vérifier si Python est installé
python --version >NUL 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERREUR] Python n'est pas installé ou n'est pas dans le PATH.
    echo Veuillez installer Python (version 3.8+) et réessayer.
    exit /b 1
)

REM Installer les dépendances
echo.
echo Installation des dépendances...
pip install faker
if %ERRORLEVEL% NEQ 0 (
    echo [ERREUR] Impossible d'installer les dépendances requises.
    exit /b 1
)

REM Exécuter le script de génération de données
echo.
echo Démarrage de la génération des données...
python generate_mock_data.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERREUR] La génération des données a échoué.
    exit /b 1
)

echo.
echo ===== Configuration terminée =====
echo Vous pouvez maintenant vous connecter à l'application.
echo.
echo Comptes utilisateurs:
echo - Admin: admin@neads.com / neads2025
echo - Consultants: consultant1@neads.com à consultant5@neads.com / neads2025
echo - Clients: client1@example.com à client15@example.com / neads2025
echo.
echo Appuyez sur une touche pour fermer cette fenêtre...
pause >NUL 