/**
 * Module SearchCreators
 * Gère l'intégration entre la carte et la recherche de créateurs
 */
const SearchCreators = (function () {
    // Dépendances
    const mapManager = MapManager;
    const userLocation = UserLocation;

    // Configuration
    const API_URL = '/api/creators/map-search';
    const DEFAULT_RADIUS = 50; // km

    // État
    let isLoading = false;
    let currentFilters = {};
    let creators = [];

    // Éléments DOM
    let searchForm;
    let radiusSelector;
    let loadingIndicator;
    let resultsCounter;
    let filtersContainer;

    /**
     * Initialise le module
     */
    function init() {
        // Récupérer les éléments DOM
        searchForm = document.getElementById('map-search-form');
        radiusSelector = document.getElementById('radius-selector');
        loadingIndicator = document.getElementById('map-loading-indicator');
        resultsCounter = document.getElementById('results-counter');
        filtersContainer = document.getElementById('map-filters');

        // Vérifier si les éléments nécessaires existent
        if (!searchForm || !mapManager) {
            console.error('Éléments nécessaires non trouvés pour SearchCreators');
            return;
        }

        // Initialiser les événements
        bindEvents();

        // Écouter les événements de la carte
        setupMapListeners();

        // Charger les créateurs initiaux
        loadCreators();

        console.log('SearchCreators initialized');
    }

    /**
     * Attache les gestionnaires d'événements
     */
    function bindEvents() {
        // Soumission du formulaire de recherche
        searchForm.addEventListener('submit', function (e) {
            e.preventDefault();
            loadCreators();
        });

        // Changement de rayon
        if (radiusSelector) {
            radiusSelector.addEventListener('change', function () {
                // Mettre à jour le rayon sur la carte
                mapManager.updateRadius(parseInt(radiusSelector.value));

                // Recharger les créateurs
                loadCreators();
            });
        }

        // Filtres
        if (filtersContainer) {
            const filterInputs = filtersContainer.querySelectorAll('input, select');
            filterInputs.forEach(input => {
                input.addEventListener('change', loadCreators);
            });
        }
    }

    /**
     * Configure les écouteurs d'événements pour la carte
     */
    function setupMapListeners() {
        // Écouter le changement de position utilisateur
        document.addEventListener('user-location-changed', function (e) {
            if (e.detail && e.detail.lat && e.detail.lng) {
                // Recharger les créateurs avec la nouvelle position
                loadCreators();
            }
        });

        // Écouter le changement de rayon
        document.addEventListener('radius-changed', function (e) {
            if (e.detail && e.detail.radius) {
                // Mettre à jour le sélecteur de rayon si nécessaire
                if (radiusSelector && radiusSelector.value != e.detail.radius) {
                    radiusSelector.value = e.detail.radius;
                }

                // Recharger les créateurs
                loadCreators();
            }
        });
    }

    /**
     * Charge les créateurs depuis l'API
     */
    function loadCreators() {
        // Si déjà en chargement, ne rien faire
        if (isLoading) return;

        // Récupérer la position actuelle
        const userPos = userLocation.getCurrentLocation();
        if (!userPos.lat || !userPos.lng) {
            console.warn('Position utilisateur non disponible pour la recherche');
            return;
        }

        // Récupérer le rayon de recherche
        const radius = radiusSelector ? parseInt(radiusSelector.value) : DEFAULT_RADIUS;

        // Récupérer les filtres
        currentFilters = getFilters();

        // Indiquer le chargement
        isLoading = true;
        if (loadingIndicator) {
            loadingIndicator.style.display = 'block';
        }

        // Construire l'URL avec les paramètres
        const queryParams = new URLSearchParams();
        queryParams.append('lat', userPos.lat);
        queryParams.append('lng', userPos.lng);
        queryParams.append('radius', radius);

        // Ajouter les filtres
        for (const [key, value] of Object.entries(currentFilters)) {
            if (value) {
                queryParams.append(key, value);
            }
        }

        // Effectuer la requête API
        fetch(`${API_URL}?${queryParams.toString()}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Erreur lors de la récupération des créateurs');
                }
                return response.json();
            })
            .then(data => {
                // Mettre à jour les données
                creators = data.creators || [];

                // Mettre à jour la carte
                mapManager.renderCreators(creators);

                // Mettre à jour le compteur de résultats
                if (resultsCounter) {
                    resultsCounter.textContent = creators.length;
                }

                console.log(`${creators.length} créateurs trouvés dans un rayon de ${radius}km`);
            })
            .catch(error => {
                console.error('Erreur:', error);
                showError('Une erreur est survenue lors de la recherche.');
            })
            .finally(() => {
                isLoading = false;
                if (loadingIndicator) {
                    loadingIndicator.style.display = 'none';
                }
            });
    }

    /**
     * Récupère les valeurs des filtres
     * @return {Object} - Objet contenant les filtres
     */
    function getFilters() {
        const filters = {};

        // Récupérer la requête de recherche
        const searchQuery = document.getElementById('map-search-query');
        if (searchQuery && searchQuery.value.trim()) {
            filters.query = searchQuery.value.trim();
        }

        // Récupérer le filtre de domaine
        const domainFilter = document.getElementById('map-domain-filter');
        if (domainFilter && domainFilter.value && domainFilter.value !== 'all') {
            filters.domain = domainFilter.value;
        }

        // Récupérer le filtre de plateforme
        const platformFilter = document.getElementById('map-platform-filter');
        if (platformFilter && platformFilter.value && platformFilter.value !== 'all') {
            filters.platform = platformFilter.value;
        }

        // Filtre de followers minimum
        const minFollowersFilter = document.getElementById('map-min-followers');
        if (minFollowersFilter && minFollowersFilter.value) {
            filters.min_followers = minFollowersFilter.value;
        }

        return filters;
    }

    /**
     * Affiche un message d'erreur
     * @param {string} message - Message d'erreur
     */
    function showError(message) {
        // Vérifier si la div d'erreur existe
        let errorContainer = document.getElementById('map-error-container');

        if (!errorContainer) {
            // Créer le conteneur d'erreur
            errorContainer = document.createElement('div');
            errorContainer.id = 'map-error-container';
            errorContainer.className = 'alert alert-danger';
            errorContainer.style.position = 'absolute';
            errorContainer.style.top = '10px';
            errorContainer.style.left = '50%';
            errorContainer.style.transform = 'translateX(-50%)';
            errorContainer.style.zIndex = '1000';
            errorContainer.style.boxShadow = '0 2px 4px rgba(0,0,0,0.3)';
            document.querySelector('.map-container').appendChild(errorContainer);
        }

        // Définir le message
        errorContainer.textContent = message;
        errorContainer.style.display = 'block';

        // Masquer après 5 secondes
        setTimeout(() => {
            errorContainer.style.display = 'none';
        }, 5000);
    }

    /**
     * Réinitialise les filtres et recharge les créateurs
     */
    function resetFilters() {
        // Réinitialiser la recherche
        const searchQuery = document.getElementById('map-search-query');
        if (searchQuery) {
            searchQuery.value = '';
        }

        // Réinitialiser les sélecteurs
        const selectors = filtersContainer.querySelectorAll('select');
        selectors.forEach(select => {
            select.value = select.options[0].value;
        });

        // Réinitialiser les inputs numériques
        const numInputs = filtersContainer.querySelectorAll('input[type="number"]');
        numInputs.forEach(input => {
            input.value = input.defaultValue || '';
        });

        // Réinitialiser le rayon
        if (radiusSelector) {
            radiusSelector.value = DEFAULT_RADIUS;
            mapManager.updateRadius(DEFAULT_RADIUS);
        }

        // Recharger les créateurs
        loadCreators();
    }

    // API publique
    return {
        init: init,
        reload: loadCreators,
        reset: resetFilters
    };
})(); 