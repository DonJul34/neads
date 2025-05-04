/**
 * Script principal de l'application Map
 * Initialise les composants et configure les événements
 */
document.addEventListener('DOMContentLoaded', function () {
    'use strict';

    console.log('📱 Map app starting...');
    console.log('ℹ️ Window dimensions:', window.innerWidth + 'x' + window.innerHeight);
    console.log('ℹ️ User agent:', navigator.userAgent);

    // Fonction pour afficher des messages toast
    const showToast = (message, type = 'info') => {
        // Créer l'élément toast s'il n'existe pas déjà
        let toastContainer = document.getElementById('map-toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'map-toast-container';
            toastContainer.style.position = 'fixed';
            toastContainer.style.bottom = '20px';
            toastContainer.style.right = '20px';
            toastContainer.style.zIndex = '9999';
            document.body.appendChild(toastContainer);
        }

        // Créer le toast
        const toast = document.createElement('div');
        toast.className = `toast show`;
        toast.role = 'alert';
        toast.ariaLive = 'assertive';
        toast.ariaAtomic = 'true';

        // Déterminer la classe de couleur en fonction du type
        let bgColor = 'bg-info';
        if (type === 'success') bgColor = 'bg-success';
        if (type === 'warning') bgColor = 'bg-warning';
        if (type === 'error') bgColor = 'bg-danger';

        // Contenu du toast
        toast.innerHTML = `
            <div class="toast-header ${bgColor} text-white">
                <strong class="me-auto">
                    <i class="fas ${type === 'success' ? 'fa-check-circle' : (type === 'warning' ? 'fa-exclamation-triangle' : 'fa-info-circle')}"></i>
                    Carte
                </strong>
                <small>à l'instant</small>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Fermer"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        `;

        // Ajouter le toast au conteneur
        toastContainer.appendChild(toast);

        // Supprimer après 5 secondes
        setTimeout(() => {
            toast.className = toast.className.replace('show', 'hide');
            setTimeout(() => {
                toast.remove();
            }, 500);
        }, 5000);

        // Gérer le bouton de fermeture
        const closeBtn = toast.querySelector('.btn-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                toast.className = toast.className.replace('show', 'hide');
                setTimeout(() => {
                    toast.remove();
                }, 500);
            });
        }
    };

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

        // Vérifier si des coordonnées sont passées dans l'URL
        const urlParams = new URLSearchParams(window.location.search);
        const urlLat = urlParams.get('lat');
        const urlLng = urlParams.get('lng');
        const urlRadius = urlParams.get('radius');
        const urlCity = urlParams.get('city');

        // Initialiser le sélecteur de rayon si spécifié dans l'URL
        if (urlRadius && radiusSelector) {
            console.log('🔄 Initialisation du rayon depuis l\'URL:', urlRadius, 'km');
            // Sélectionner l'option correspondante
            Array.from(radiusSelector.options).forEach(option => {
                if (option.value === urlRadius) {
                    option.selected = true;
                }
            });
        }

        // Initialiser la carte avec les paramètres de base
        MapManager.initialize(
            'map',
            'radius-selector',
            'creator-count',
            'map-loading'
        );

        // Définir explicitement le rayon si spécifié dans l'URL
        if (urlRadius && typeof MapManager.setRadius === 'function') {
            console.log('🔄 Application du rayon depuis l\'URL:', urlRadius, 'km');
            MapManager.setRadius(parseInt(urlRadius));
        }

        // Si des coordonnées sont spécifiées dans l'URL, les utiliser
        if (urlLat && urlLng) {
            const lat = parseFloat(urlLat);
            const lng = parseFloat(urlLng);

            console.log('🔄 Utilisation des coordonnées depuis l\'URL:', lat, lng);

            // Mettre à jour la position utilisateur avec ces coordonnées
            setTimeout(() => {
                try {
                    MapManager.updateUserPosition({
                        latitude: lat,
                        longitude: lng
                    }, 12);
                } catch (e) {
                    console.error('❌ Erreur lors de l\'initialisation avec les coordonnées URL:', e);
                }
            }, 500); // Court délai pour s'assurer que la carte est bien initialisée
        }
        // Si une ville est spécifiée dans l'URL mais pas de coordonnées, rechercher la ville
        else if (urlCity && !urlLat && !urlLng) {
            console.log('🔄 Recherche de la ville depuis l\'URL:', urlCity);

            // Vérifier d'abord dans les villes courantes (si UserLocation.COMMON_CITIES est accessible)
            let commonCityFound = false;
            if (typeof UserLocation !== 'undefined') {
                const normalizedQuery = urlCity.trim().toLowerCase();
                // Essayer d'accéder aux villes courantes, avec une vérification de sécurité
                const commonCities = UserLocation.COMMON_CITIES || window.COMMON_CITIES || {};

                const commonCity = Object.keys(commonCities).find(city => {
                    return normalizedQuery === city ||
                        normalizedQuery.includes(city) ||
                        city.includes(normalizedQuery);
                });

                if (commonCity) {
                    console.log('✅ Ville trouvée dans le dictionnaire:', commonCity);
                    const coords = commonCities[commonCity];

                    // Mettre à jour l'URL avec les coordonnées
                    const currentUrl = new URL(window.location.href);
                    currentUrl.searchParams.set('lat', coords.latitude);
                    currentUrl.searchParams.set('lng', coords.longitude);
                    history.replaceState(null, '', currentUrl.toString());

                    // Mettre à jour la position sur la carte
                    setTimeout(() => {
                        MapManager.updateUserPosition(coords, 12);
                        showToast(`Position réglée sur ${commonCity.charAt(0).toUpperCase() + commonCity.slice(1)}`, 'success');
                    }, 500);

                    commonCityFound = true;
                }
            }

            // Si la ville n'est pas trouvée dans les villes courantes, rechercher la ville via le module UserLocation
            if (!commonCityFound) {
                setTimeout(() => {
                    if (typeof UserLocation !== 'undefined' && UserLocation.searchLocation) {
                        UserLocation.searchLocation(urlCity, (results) => {
                            if (results && results.length > 0) {
                                const firstResult = results[0];
                                console.log('✅ Ville trouvée:', firstResult.display_name);

                                // Mettre à jour la position utilisateur avec ces coordonnées
                                const lat = parseFloat(firstResult.lat);
                                const lng = parseFloat(firstResult.lon);

                                // Mettre à jour l'URL avec les coordonnées trouvées
                                const currentUrl = new URL(window.location.href);
                                currentUrl.searchParams.set('lat', lat);
                                currentUrl.searchParams.set('lng', lng);
                                history.replaceState(null, '', currentUrl.toString());

                                // Mettre à jour la position sur la carte
                                MapManager.updateUserPosition({
                                    latitude: lat,
                                    longitude: lng
                                }, 12);

                                // Afficher un message de confirmation
                                showToast(`Position réglée sur ${firstResult.display_name}`, 'success');
                            } else {
                                console.error('❌ Ville non trouvée:', urlCity);
                                showToast(`Impossible de localiser "${urlCity}"`, 'error');
                            }
                        });
                    }
                }, 1000);
            }
        }

        console.log('✅ Map initialization complete');
    } else {
        console.error('❌ Map initialization failed - map element not found');
    }

    // Gestionnaire pour le formulaire de filtres
    if (filterForm) {
        filterForm.addEventListener('submit', function (e) {
            e.preventDefault();
            console.log('🔄 Filter form submitted');

            const formData = new FormData(filterForm);
            const searchParams = new URLSearchParams(window.location.search);

            // Préserver les paramètres de géolocalisation existants
            const lat = searchParams.get('lat');
            const lng = searchParams.get('lng');
            const city = searchParams.get('city');

            console.log('📊 Current filter values:');
            for (const [key, value] of formData.entries()) {
                console.log(`- ${key}: ${value}`);
                if (value) {
                    searchParams.set(key, value);
                } else {
                    // Ne pas supprimer lat, lng ou city
                    if (key !== 'lat' && key !== 'lng' && key !== 'city') {
                        searchParams.delete(key);
                    }
                }
            }

            // Restaurer les coordonnées si elles existaient
            if (lat && lng) {
                searchParams.set('lat', lat);
                searchParams.set('lng', lng);
            }

            // Restaurer le nom de la ville
            if (city) {
                searchParams.set('city', city);
            }

            // Forcer un rechargement complet de la page pour s'assurer que tout est bien appliqué
            const newUrl = `${window.location.pathname}?${searchParams.toString()}`;
            console.log('🔄 Reloading page with filters:', newUrl);
            window.location.href = newUrl;
            return;
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

        // Gestionnaire pour le bouton de recherche de ville depuis les filtres
        const cityFilterInput = document.getElementById('city-filter');
        const citySearchBtn = document.getElementById('city-search-btn');

        if (cityFilterInput && citySearchBtn) {
            console.log('🔍 Configuration du gestionnaire de recherche de ville depuis les filtres');

            // Fonction pour rechercher la ville et mettre à jour la carte
            const searchCityFromFilter = () => {
                const cityName = cityFilterInput.value.trim();
                if (cityName.length < 2) return;

                console.log('🔄 Recherche de ville depuis les filtres:', cityName);

                // Désactiver le bouton pendant la recherche
                citySearchBtn.disabled = true;
                citySearchBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';

                // Recherche via l'API Nominatim
                UserLocation.searchLocation(cityName, (results) => {
                    // Réactiver le bouton
                    citySearchBtn.disabled = false;
                    citySearchBtn.innerHTML = '<i class="fas fa-search"></i>';

                    if (results.length > 0) {
                        const firstResult = results[0];
                        console.log('✅ Résultat de recherche trouvé:', firstResult);

                        // Mettre à jour la position sur la carte
                        const coords = {
                            lat: parseFloat(firstResult.lat),
                            lng: parseFloat(firstResult.lon)
                        };

                        // Mettre à jour la carte avec ces coordonnées
                        MapManager.updateUserPosition(coords, 12);

                        // Afficher un message de succès
                        showToast(`Position mise à jour: ${firstResult.display_name}`, 'success');
                    } else {
                        console.log('❌ Aucun résultat trouvé pour:', cityName);
                        showToast(`Aucun résultat trouvé pour "${cityName}"`, 'warning');
                    }
                });
            };

            // Écouter les clics sur le bouton de recherche
            citySearchBtn.addEventListener('click', searchCityFromFilter);

            // Écouter les appuis sur la touche Entrée dans le champ
            cityFilterInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    searchCityFromFilter();
                }
            });
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
                            latitude: place.lat,
                            longitude: place.lon
                        });

                        // Mettre à jour la carte avec cette position
                        MapManager.updateUserPosition({
                            latitude: place.lat,
                            longitude: place.lon
                        });

                        // Recharger les données des créateurs
                        MapManager.reloadData();

                        // Mettre à jour l'entrée de recherche et masquer les résultats
                        locationSearchInput.value = place.name;
                        locationResults.style.display = 'none';
                        if (clearLocationBtn) {
                            clearLocationBtn.style.display = 'block';
                        }
                    });

                    locationResults.appendChild(resultItem);
                });

                locationResults.style.display = 'block';
            });
        };

        // Gérer la saisie dans le champ de recherche
        locationSearchInput.addEventListener('input', (e) => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                performLocationSearch(e.target.value.trim());
            }, 300);
        });

        // Gérer le clic sur le bouton de recherche
        if (locationSearchBtn) {
            locationSearchBtn.addEventListener('click', () => {
                performLocationSearch(locationSearchInput.value.trim());
            });
        }

        // Gérer la soumission du formulaire de recherche
        locationSearchInput.closest('form')?.addEventListener('submit', (e) => {
            e.preventDefault();
            performLocationSearch(locationSearchInput.value.trim());
        });

        // Gérer le bouton pour effacer la recherche
        if (clearLocationBtn) {
            clearLocationBtn.addEventListener('click', () => {
                locationSearchInput.value = '';
                clearLocationBtn.style.display = 'none';
                // Ne pas réinitialiser la carte lors de l'effacement du champ
            });

            // Afficher le bouton d'effacement si le champ a une valeur
            locationSearchInput.addEventListener('keyup', () => {
                clearLocationBtn.style.display = locationSearchInput.value ? 'block' : 'none';
            });

            // Initialiser l'état du bouton
            clearLocationBtn.style.display = locationSearchInput.value ? 'block' : 'none';
        }

        // Masquer les résultats lors d'un clic en dehors
        document.addEventListener('click', (e) => {
            if (!locationResults.contains(e.target) && e.target !== locationSearchInput) {
                locationResults.style.display = 'none';
            }
        });
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