/**
 * Script de test pour les fonctionnalités de géolocalisation et de recherche
 * À inclure temporairement pour déboguer les problèmes de localisation
 */
document.addEventListener('DOMContentLoaded', function () {
    console.log('🔄 Location Test Script Loaded');

    // Vérifier si les modules nécessaires sont chargés
    if (typeof UserLocation === 'undefined') {
        console.error('❌ UserLocation module is not loaded!');
        return;
    }

    if (typeof MapManager === 'undefined') {
        console.error('❌ MapManager module is not loaded!');
        return;
    }

    // Éléments UI
    const locationInput = document.getElementById('location-search');
    const searchButton = document.getElementById('location-search-btn');
    const clearButton = document.getElementById('clear-location-btn');
    const resultsContainer = document.getElementById('location-results');
    const geolocBtn = document.getElementById('geoloc-button');

    // Fonction pour créer une zone de test dans la page
    const createTestPanel = () => {
        const panel = document.createElement('div');
        panel.id = 'location-test-panel';
        panel.style.position = 'fixed';
        panel.style.bottom = '10px';
        panel.style.right = '10px';
        panel.style.zIndex = '1000';
        panel.style.background = 'white';
        panel.style.padding = '10px';
        panel.style.borderRadius = '5px';
        panel.style.boxShadow = '0 0 10px rgba(0,0,0,0.2)';
        panel.style.maxWidth = '300px';

        panel.innerHTML = `
            <h5>Déboguer localisation</h5>
            <div class="mb-2">
                <button id="test-nominatim" class="btn btn-sm btn-outline-primary">Tester API Nominatim</button>
            </div>
            <div class="mb-2">
                <button id="test-update-map" class="btn btn-sm btn-outline-primary">Tester mise à jour carte</button>
            </div>
            <div class="mb-2">
                <button id="test-paris" class="btn btn-sm btn-outline-primary">Centrer sur Paris</button>
            </div>
            <div id="test-results" style="max-height: 100px; overflow-y: auto; font-size: 12px; margin-top: 10px;"></div>
            <div class="mt-2">
                <button id="close-test-panel" class="btn btn-sm btn-outline-secondary">Fermer</button>
            </div>
        `;

        document.body.appendChild(panel);

        // Enregistrer les événements
        document.getElementById('test-nominatim').addEventListener('click', testNominatim);
        document.getElementById('test-update-map').addEventListener('click', testUpdateMap);
        document.getElementById('test-paris').addEventListener('click', testCenterParis);
        document.getElementById('close-test-panel').addEventListener('click', () => panel.remove());
    };

    // Fonction pour tester l'API Nominatim
    const testNominatim = () => {
        const testResults = document.getElementById('test-results');
        testResults.innerHTML = '<div>⏳ Test de l\'API Nominatim en cours...</div>';

        // Tester avec Paris
        const testQuery = 'Paris';

        fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(testQuery)}&limit=1`, {
            headers: {
                'Accept': 'application/json'
            }
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                testResults.innerHTML += `<div style="color: green;">✅ API Nominatim fonctionne!</div>`;
                testResults.innerHTML += `<div>Résultat pour "${testQuery}": ${data.length} trouvés</div>`;

                if (data.length > 0) {
                    const result = data[0];
                    testResults.innerHTML += `<div>Premier résultat: ${result.display_name}</div>`;
                    testResults.innerHTML += `<div>Coordonnées: ${result.lat}, ${result.lon}</div>`;
                }
            })
            .catch(error => {
                testResults.innerHTML += `<div style="color: red;">❌ Erreur API Nominatim: ${error.message}</div>`;
                testResults.innerHTML += `<div>Essai avec proxy CORS...</div>`;

                // Essai avec proxy CORS
                fetch(`https://cors-anywhere.herokuapp.com/https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(testQuery)}&limit=1`, {
                    headers: {
                        'Accept': 'application/json',
                        'Origin': window.location.origin
                    }
                })
                    .then(response => response.json())
                    .then(data => {
                        testResults.innerHTML += `<div style="color: green;">✅ API via proxy fonctionne!</div>`;
                    })
                    .catch(proxyError => {
                        testResults.innerHTML += `<div style="color: red;">❌ Erreur proxy: ${proxyError.message}</div>`;
                    });
            });
    };

    // Fonction pour tester la mise à jour de la carte
    const testUpdateMap = () => {
        const testResults = document.getElementById('test-results');
        testResults.innerHTML = '<div>⏳ Test de mise à jour de la carte en cours...</div>';

        try {
            // Tester avec une position fixe (Lyon)
            const testCoords = {
                latitude: 45.7640,
                longitude: 4.8357
            };

            testResults.innerHTML += `<div>Tentative de mise à jour avec: ${testCoords.latitude}, ${testCoords.longitude}</div>`;

            // Appel direct à MapManager
            MapManager.updateUserPosition(testCoords);
            MapManager.reloadData();

            testResults.innerHTML += `<div style="color: green;">✅ Mise à jour de la carte réussie!</div>`;
        } catch (error) {
            testResults.innerHTML += `<div style="color: red;">❌ Erreur mise à jour carte: ${error.message}</div>`;
            testResults.innerHTML += `<div>${error.stack}</div>`;
        }
    };

    // Fonction pour centrer sur Paris
    const testCenterParis = () => {
        const testResults = document.getElementById('test-results');
        testResults.innerHTML = '<div>⏳ Centrage sur Paris en cours...</div>';

        try {
            const parisCoords = {
                latitude: 48.8566,
                longitude: 2.3522
            };

            if (locationInput) {
                locationInput.value = 'Paris, France';
            }

            testResults.innerHTML += `<div>Tentative de centrage sur Paris: ${parisCoords.latitude}, ${parisCoords.longitude}</div>`;

            // Appel direct à MapManager
            MapManager.updateUserPosition(parisCoords);
            MapManager.reloadData();

            testResults.innerHTML += `<div style="color: green;">✅ Centrage sur Paris réussi!</div>`;
        } catch (error) {
            testResults.innerHTML += `<div style="color: red;">❌ Erreur centrage sur Paris: ${error.message}</div>`;
        }
    };

    // Ajouter un bouton pour activer le panneau de test
    const addTestButton = () => {
        const button = document.createElement('button');
        button.id = 'activate-location-test';
        button.className = 'btn btn-sm btn-primary';
        button.style.position = 'fixed';
        button.style.bottom = '70px';
        button.style.right = '20px';
        button.style.zIndex = '999';
        button.innerHTML = '🔍 Tester localisation';

        button.addEventListener('click', () => {
            button.remove();
            createTestPanel();
        });

        document.body.appendChild(button);
    };

    // Ajouter le bouton de test après un court délai
    setTimeout(addTestButton, 1000);
}); 