/**
 * Gère l'autocomplétion des adresses avec l'API Nominatim (OpenStreetMap)
 */
document.addEventListener('DOMContentLoaded', function () {
    const addressInput = document.getElementById('id_full_address');
    const latitudeInput = document.getElementById('id_latitude');
    const longitudeInput = document.getElementById('id_longitude');
    const mapPreview = document.getElementById('map-preview');

    if (!addressInput || !latitudeInput || !longitudeInput) return;

    // Débounce pour limiter les appels API
    let debounceTimer;
    const debounceDelay = 500; // 500ms de délai

    // Fonction pour récupérer les suggestions d'adresse
    async function fetchAddressSuggestions(query) {
        if (!query || query.length < 3) return [];

        try {
            const response = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&countrycodes=fr&limit=5`);
            if (!response.ok) throw new Error('Erreur lors de la récupération des suggestions');

            const data = await response.json();
            return data.map(item => ({
                display: item.display_name,
                lat: item.lat,
                lon: item.lon
            }));
        } catch (error) {
            console.error('Erreur lors de la récupération des suggestions:', error);
            return [];
        }
    }

    // Fonction pour afficher les suggestions
    function displaySuggestions(suggestions) {
        // Supprimer les suggestions existantes
        const existingSuggestions = document.querySelector('.address-suggestions');
        if (existingSuggestions) existingSuggestions.remove();

        if (suggestions.length === 0) return;

        // Créer le conteneur de suggestions
        const suggestionsContainer = document.createElement('div');
        suggestionsContainer.className = 'address-suggestions';

        // Ajouter chaque suggestion
        suggestions.forEach(suggestion => {
            const suggestionItem = document.createElement('div');
            suggestionItem.className = 'suggestion-item';
            suggestionItem.textContent = suggestion.display;

            suggestionItem.addEventListener('click', () => {
                addressInput.value = suggestion.display;
                latitudeInput.value = suggestion.lat;
                longitudeInput.value = suggestion.lon;

                // Afficher la carte
                if (mapPreview) {
                    mapPreview.style.display = 'block';
                    const map = L.map('map-preview').setView([suggestion.lat, suggestion.lon], 13);
                    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    }).addTo(map);
                }

                // Supprimer les suggestions
                suggestionsContainer.remove();
            });

            suggestionsContainer.appendChild(suggestionItem);
        });

        // Ajouter le conteneur de suggestions après le champ d'adresse
        addressInput.parentNode.appendChild(suggestionsContainer);
    }

    // Écouter les changements dans le champ d'adresse
    addressInput.addEventListener('input', function () {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(async () => {
            const suggestions = await fetchAddressSuggestions(this.value);
            displaySuggestions(suggestions);
        }, debounceDelay);
    });

    // Cacher les suggestions lors du clic en dehors
    document.addEventListener('click', function (e) {
        if (!addressInput.contains(e.target) && !e.target.closest('.address-suggestions')) {
            const suggestions = document.querySelector('.address-suggestions');
            if (suggestions) suggestions.remove();
        }
    });

    // Empêcher la soumission du formulaire avec Entrée dans le champ d'adresse
    addressInput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            return false;
        }
    });
}); 