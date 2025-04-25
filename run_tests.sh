#!/bin/bash
echo "Execution des tests avec pytest et colorlog"
echo "==================================="

echo "Installation des dependances de test..."
pip install -r requirements_test.txt

echo "Execution des tests..."
python -m pytest

echo "==================================="
echo "Rapport de couverture genere dans le dossier htmlcov/"
echo "Ouvrez htmlcov/index.html dans votre navigateur pour visualiser le rapport" 