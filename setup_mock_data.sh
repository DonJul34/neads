#!/bin/bash

echo "===== NEADS - Configuration des données de test ====="

# Vérifier si Python est installé
if ! command -v python3 &> /dev/null; then
    echo "[ERREUR] Python n'est pas installé."
    echo "Veuillez installer Python (version 3.8+) et réessayer."
    exit 1
fi

# Installer les dépendances
echo ""
echo "Installation des dépendances..."
pip3 install faker || pip install faker
if [ $? -ne 0 ]; then
    echo "[ERREUR] Impossible d'installer les dépendances requises."
    exit 1
fi

# Rendre le script exécutable
chmod +x generate_mock_data.py

# Exécuter le script de génération de données
echo ""
echo "Démarrage de la génération des données..."
python3 generate_mock_data.py || python generate_mock_data.py
if [ $? -ne 0 ]; then
    echo "[ERREUR] La génération des données a échoué."
    exit 1
fi

echo ""
echo "===== Configuration terminée ====="
echo "Vous pouvez maintenant vous connecter à l'application."
echo ""
echo "Comptes utilisateurs:"
echo "- Admin: admin@neads.com / neads2025"
echo "- Consultants: consultant1@neads.com à consultant5@neads.com / neads2025"
echo "- Clients: client1@example.com à client15@example.com / neads2025"
echo ""
echo "Appuyez sur Entrée pour fermer cette fenêtre..."
read 