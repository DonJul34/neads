/**
 * Script principal de l'application Map
 * Initialise les composants et configure les événements
 */
document.addEventListener('DOMContentLoaded', function () {
    'use strict';

    console.log('📱 Map app starting...');
    console.log('ℹ️ Window dimensions:', window.innerWidth + 'x' + window.innerHeight);
    console.log('ℹ️ User agent:', navigator.userAgent);

    // Éléments pour la géolocalisation
    const geolocButton = document.getElementById('geoloc-button');

    // Éléments pour la carte
    const mapContainer = document.getElementById('map-container');
    const mapElement = document.getElementById('map');
    const creatorCount = document.getElementById('creator-count');
    const radiusSelector = document.getElementById('radius-selector');
    const loadingIndicator = document.getElementById('map-loading');

    // Éléments pour le formulaire de filtres
    const filterForm = document.getElementById('filter-form');
    const filterToggle = document.getElementById('filter-toggle');
    const filterPanel = document.getElementById('filter-panel');
    const resetFiltersBtn = document.getElementById('reset-filters-btn');

    // Éléments pour la recherche de localisation
    const locationSearchInput = document.getElementById('location-search');
    const locationSearchBtn = document.getElementById('location-search-btn');
    const locationResults = document.getElementById('location-results');
    const clearLocationBtn = document.getElementById('clear-location-btn');

    console.log('🔍 DOM elements status:');
    console.log(`- Map container: ${mapElement ? mapElement.parentNode ? '✅ Found' : '❌ Found but no parent' : '❌ Missing'}`);
    console.log(`- Map element: ${mapElement ? '✅ Found' : '❌ Missing'}`);
    console.log(`- Creator count: ${creatorCount ? '✅ Found' : '❌ Missing'}`);
    console.log(`- Radius selector: ${radiusSelector ? '✅ Found' : '❌ Missing'}`);
    console.log(`- Loading indicator: ${loadingIndicator ? '✅ Found' : '❌ Missing'}`);
    console.log(`- Geolocation button: ${geolocButton ? '✅ Found' : '❌ Missing'}`);
    console.log(`- Filter form: ${filterForm ? '✅ Found' : '❌ Missing'}`);
    console.log(`- Location search input: ${locationSearchInput ? '✅ Found' : '❌ Missing'}`);
    console.log(`- Location search button: ${locationSearchBtn ? '✅ Found' : '❌ Missing'}`);

    // Vérifier si le module UserLocation est chargé
    if (typeof UserLocation === 'undefined') {
        console.error('❌ UserLocation module is not loaded!');
    } else {
        console.log('✅ UserLocation module is loaded');
    }

    // Vérifier si le module MapManager est chargé
    if (typeof MapManager === 'undefined') {
        console.error('❌ MapManager module is not loaded!');
    } else {
        console.log('✅ MapManager module is loaded');
    }

    // Initialiser la carte
    if (mapElement) {
        console.log('🗺️ Initializing map manager...');
        MapManager.initialize(
            'map',
            'radius-selector',
            'creator-count',
            'map-loading'
        );
        console.log('✅ Map initialization complete');
    } else {
        console.error('❌ Map initialization failed - map element not found');
    }

    // Gestionnaire pour le bouton de géolocalisation
    if (geolocButton) {
        geolocButton.addEventListener('click', function () {
            console.log('🔄 Geolocation button clicked');
            geolocButton.disabled = true;
            geolocButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Localisation...';

            UserLocation.getUserLocation(
                function (coords) {
                    console.log('✅ Geolocation successful:', coords);
                    console.log('📊 Coordinates precision:', {
                        latitude: coords.latitude,
                        longitude: coords.longitude,
                        accuracy: coords.accuracy ? coords.accuracy + 'm' : 'N/A'
                    });

                    MapManager.updateUserPosition(coords);

                    console.log('🔄 Reloading creators data with new location');
                    MapManager.reloadData();

                    geolocButton.disabled = false;
                    geolocButton.innerHTML = '<i class="fas fa-location-arrow"></i> Ma position';
                    console.log('✅ Geolocation process complete');
                },
                function (error) {
                    console.error('❌ Geolocation error:', error);
                    console.error('📊 Error details:', {
                        code: error.code,
                        message: error.message
                    });

                    let errorMsg = '';
                    switch (error.code) {
                        case 1:
                            errorMsg = 'Vous avez refusé la géolocalisation';
                            break;
                        case 2:
                            errorMsg = 'Position non disponible';
                            break;
                        case 3:
                            errorMsg = 'Délai d\'attente dépassé';
                            break;
                        default:
                            errorMsg = 'Erreur inconnue';
                    }

                    // Afficher l'erreur
                    const alertEl = document.createElement('div');
                    alertEl.className = 'alert alert-danger';
                    alertEl.innerHTML = `<strong>Erreur de géolocalisation</strong><p>${errorMsg}</p>`;
                    if (mapElement && mapElement.parentNode) {
                        mapElement.parentNode.insertBefore(alertEl, mapElement);
                    } else if (mapContainer) {
                        mapContainer.insertBefore(alertEl, mapElement);
                    } else {
                        document.body.appendChild(alertEl);
                    }

                    setTimeout(function () {
                        alertEl.remove();
                        console.log('ℹ️ Geolocation error message removed');
                    }, 5000);

                    geolocButton.disabled = false;
                    geolocButton.innerHTML = '<i class="fas fa-location-arrow"></i> Ma position';
                    console.log('❌ Geolocation process failed');
                }
            );
        });
        console.log('✅ Geolocation button event listener attached');
    }

    // Gestionnaire pour le formulaire de filtres
    if (filterForm) {
        filterForm.addEventListener('submit', function (e) {
            e.preventDefault();
            console.log('🔄 Filter form submitted');

            const formData = new FormData(filterForm);
            const searchParams = new URLSearchParams(window.location.search);

            console.log('📊 Current filter values:');
            for (const [key, value] of formData.entries()) {
                console.log(`- ${key}: ${value}`);
                if (value) {
                    searchParams.set(key, value);
                } else {
                    searchParams.delete(key);
                }
            }

            // Mettre à jour l'URL sans recharger la page
            const newUrl = `${window.location.pathname}?${searchParams.toString()}`;
            console.log('🔄 Updating URL with filters:', newUrl);
            window.history.pushState({}, '', newUrl);

            // Recharger les données avec les nouveaux filtres
            console.log('🔄 Reloading data with new filters');
            MapManager.reloadData();

            // Fermer le panneau sur mobile
            if (window.innerWidth < 768 && filterPanel && filterPanel.classList.contains('show')) {
                console.log('ℹ️ Closing filter panel on mobile');
                filterToggle.click();
            }

            console.log('✅ Filter application complete');
        });
        console.log('✅ Filter form event listener attached');

        // Gestionnaire pour le bouton de réinitialisation des filtres
        if (resetFiltersBtn) {
            resetFiltersBtn.addEventListener('click', function () {
                console.log('🔄 Resetting filters');

                // Réinitialiser tous les champs du formulaire
                filterForm.reset();

                // Décocher toutes les cases à cocher des domaines
                const domainCheckboxes = document.querySelectorAll('.domain-checkbox');
                domainCheckboxes.forEach(checkbox => {
                    checkbox.checked = false;
                });

                // Soumettre le formulaire pour appliquer la réinitialisation
                filterForm.dispatchEvent(new Event('submit'));
                console.log('✅ Filters reset complete');
            });
            console.log('✅ Reset filters button event listener attached');
        }
    }

    // Recherche de localisation avec autocomplete
    if (locationSearchInput && locationResults) {
        let debounceTimer;
        let selectedLocationCoords = null;

        // Fonction de recherche de localisation
        const performLocationSearch = (query) => {
            console.log('🔄 Searching for location:', query);

            if (query.length < 3) {
                locationResults.innerHTML = '';
                locationResults.style.display = 'none';
                return;
            }

            // Afficher un indicateur de chargement
            locationResults.innerHTML = '<div class="p-2 text-center"><div class="spinner-border spinner-border-sm" role="status"></div> Recherche...</div>';
            locationResults.style.display = 'block';

            // Vérifier si la fonction searchLocation existe
            if (typeof UserLocation.searchLocation !== 'function') {
                console.error('❌ UserLocation.searchLocation is not a function!');
                locationResults.innerHTML = '<div class="p-2 text-center text-danger">Erreur: Fonction de recherche non disponible</div>';
                return;
            }

            // Utiliser le module UserLocation pour la recherche
            UserLocation.searchLocation(query, (results) => {
                console.log(`✅ Location search results: ${results.length} places found`, results);

                locationResults.innerHTML = '';

                if (results.length === 0) {
                    locationResults.innerHTML = '<div class="p-2 text-center text-muted">Aucun résultat trouvé</div>';
                    return;
                }

                results.forEach(place => {
                    const resultItem = document.createElement('div');
                    resultItem.className = 'location-result';
                    resultItem.textContent = place.name;

                    resultItem.addEventListener('click', () => {
                        console.log('🔄 Location selected:', place.name);
                        console.log('🔄 Location coordinates:', {
                            latitude: place.latitude,
                            longitude: place.longitude
                        });

                        locationSearchInput.value = place.name;
                        selectedLocationCoords = {
                            latitude: place.latitude,
                            longitude: place.longitude
                        };
                        locationResults.style.display = 'none';

                        // Afficher le bouton de suppression
                        if (clearLocationBtn) {
                            clearLocationBtn.style.display = 'block';
                        }

                        try {
                            // Mettre à jour la carte immédiatement
                            console.log('🔄 Updating map position with coordinates:', selectedLocationCoords);
                            MapManager.updateUserPosition(selectedLocationCoords);
                            console.log('🔄 Reloading map data with new location');
                            MapManager.reloadData();
                            console.log('✅ Map updated with new location');
                        } catch (error) {
                            console.error('❌ Error updating map position:', error);
                            alert('Erreur lors de la mise à jour de la carte: ' + error.message);
                        }
                    });

                    locationResults.appendChild(resultItem);
                });

                locationResults.style.display = 'block';
            });
        };

        // Gestionnaire d'événements pour la saisie dans le champ de recherche
        locationSearchInput.addEventListener('input', function () {
            clearTimeout(debounceTimer);

            selectedLocationCoords = null;

            const query = this.value.trim();

            if (query.length < 3) {
                locationResults.innerHTML = '';
                locationResults.style.display = 'none';
                return;
            }

            // Débounce pour éviter trop de requêtes
            debounceTimer = setTimeout(() => {
                performLocationSearch(query);
            }, 500);
        });

        // Gestionnaire d'événements pour le bouton de recherche
        if (locationSearchBtn) {
            locationSearchBtn.addEventListener('click', function () {
                console.log('🔄 Location search button clicked');

                const query = locationSearchInput.value.trim();
                if (query.length < 3) {
                    console.log('ℹ️ Search query too short, ignoring click');
                    alert('Veuillez saisir au moins 3 caractères pour la recherche');
                    return;
                }

                if (selectedLocationCoords) {
                    console.log('🔄 Using already selected location:', selectedLocationCoords);
                    try {
                        // Mettre à jour la carte avec la position sélectionnée
                        MapManager.updateUserPosition(selectedLocationCoords);
                        MapManager.reloadData();
                        console.log('✅ Map updated with selected location');
                    } catch (error) {
                        console.error('❌ Error updating map with selected location:', error);
                        alert('Erreur lors de la mise à jour de la carte: ' + error.message);
                    }
                    return;
                }

                // Si l'utilisateur n'a pas sélectionné un lieu, effectuer la recherche
                locationSearchBtn.disabled = true;
                locationSearchBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

                if (typeof UserLocation.searchLocation !== 'function') {
                    console.error('❌ UserLocation.searchLocation is not a function!');
                    locationSearchBtn.disabled = false;
                    locationSearchBtn.innerHTML = '<i class="fas fa-search"></i>';
                    alert('Fonction de recherche non disponible');
                    return;
                }

                UserLocation.searchLocation(query, (results) => {
                    locationSearchBtn.disabled = false;
                    locationSearchBtn.innerHTML = '<i class="fas fa-search"></i>';

                    if (results.length > 0) {
                        // Utiliser le premier résultat
                        const place = results[0];
                        console.log('✅ Using first search result:', place.name);
                        console.log('🔄 Location coordinates:', {
                            latitude: place.latitude,
                            longitude: place.longitude
                        });

                        locationSearchInput.value = place.name;
                        selectedLocationCoords = {
                            latitude: place.latitude,
                            longitude: place.longitude
                        };

                        try {
                            // Mettre à jour la carte avec la position
                            MapManager.updateUserPosition(selectedLocationCoords);
                            MapManager.reloadData();
                            console.log('✅ Map updated with new location');
                        } catch (error) {
                            console.error('❌ Error updating map with search result:', error);
                            alert('Erreur lors de la mise à jour de la carte: ' + error.message);
                        }

                        // Afficher le bouton de suppression
                        if (clearLocationBtn) {
                            clearLocationBtn.style.display = 'block';
                        }
                    } else {
                        console.log('❌ No results found for query:', query);

                        // Montrer un message d'erreur
                        const alertEl = document.createElement('div');
                        alertEl.className = 'alert alert-warning';
                        alertEl.innerHTML = `<strong>Lieu introuvable</strong><p>Aucun résultat pour "${query}"</p>`;
                        mapElement.parentNode.insertBefore(alertEl, mapElement.nextSibling);

                        setTimeout(function () {
                            alertEl.remove();
                        }, 3000);
                    }
                });
            });
            console.log('✅ Location search button event listener attached');
        }

        // Gestionnaire d'événements pour le bouton de suppression
        if (clearLocationBtn) {
            clearLocationBtn.addEventListener('click', function () {
                console.log('🔄 Clearing location search');

                locationSearchInput.value = '';
                selectedLocationCoords = null;
                clearLocationBtn.style.display = 'none';
            });
            console.log('✅ Clear location button event listener attached');
        }

        // Fermer les résultats de recherche quand on clique ailleurs
        document.addEventListener('click', function (e) {
            if (e.target !== locationSearchInput && !locationResults.contains(e.target)) {
                locationResults.style.display = 'none';
            }
        });

        console.log('✅ Location search functionality initialized');
    }

    // Gestionnaire pour le toggle des filtres sur mobile
    if (filterToggle && filterPanel) {
        filterToggle.addEventListener('click', function () {
            console.log('🔄 Filter toggle clicked');
            filterPanel.classList.toggle('show');

            if (filterPanel.classList.contains('show')) {
                console.log('ℹ️ Filter panel opened');
                document.body.classList.add('filter-panel-open');
                filterToggle.innerHTML = '<i class="fas fa-times me-1"></i> Fermer';
            } else {
                console.log('ℹ️ Filter panel closed');
                document.body.classList.remove('filter-panel-open');
                filterToggle.innerHTML = '<i class="fas fa-filter me-1"></i> Filtres';
            }
        });

        // Fermer le panneau quand on clique sur le bouton Fermer
        const closeFiltersBtn = document.getElementById('close-filters');
        if (closeFiltersBtn) {
            closeFiltersBtn.addEventListener('click', function () {
                console.log('🔄 Close filters button clicked');
                filterPanel.classList.remove('show');
                document.body.classList.remove('filter-panel-open');
                filterToggle.innerHTML = '<i class="fas fa-filter me-1"></i> Filtres';
            });
        }

        console.log('✅ Filter toggle functionality initialized');
    }

    console.log('✅ Map application initialization complete');
}); 