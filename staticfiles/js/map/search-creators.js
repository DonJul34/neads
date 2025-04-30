/**
 * Module SearchCreators
 * Gère l'intégration entre la carte et la recherche de créateurs
 */
const SearchCreators = (function () {
    // Dépendances
    const mapManager = MapManager;
    const userLocation = UserLocation;

    // Configuration
    const API_URL = '/creators/api/creators/map-search/'; // URL path to match Django URL config
    const DEFAULT_RADIUS = 50; // km

    // État
    let isLoading = false;
    let currentFilters = {};
    let creators = [];
    let lastQueryString = '';

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
        console.log('🔄 SearchCreators.init called');

        // Récupérer les éléments DOM
        searchForm = document.getElementById('map-search-form');
        radiusSelector = document.getElementById('radius-selector');
        loadingIndicator = document.getElementById('map-loading-indicator');
        resultsCounter = document.getElementById('results-counter');
        filtersContainer = document.getElementById('map-filters');

        // Vérifier si les éléments nécessaires existent
        if (!searchForm || !mapManager) {
            console.error('❌ Éléments nécessaires non trouvés pour SearchCreators');
            return;
        }

        // Initialiser les événements
        bindEvents();

        // Écouter les événements de la carte
        setupMapListeners();

        // Charger les créateurs initiaux immédiatement après l'initialisation
        console.log('🔄 Loading initial creators');
        setTimeout(() => {
            loadCreators(true); // Force le chargement initial
        }, 500); // Petit délai pour s'assurer que tout est initialisé

        console.log('✅ SearchCreators initialized');
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
                // Remplacer updateRadius (qui n'existe pas) par la méthode correcte
                const radius = parseInt(radiusSelector.value);
                // Mise à jour du cercle de recherche
                mapManager.updateSearchArea();

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
     * @param {boolean} forceRefresh - Si true, force le rechargement des créateurs même si les filtres n'ont pas changé
     */
    function loadCreators(forceRefresh = false) {
        // Si déjà en chargement, ne rien faire
        if (isLoading) return;

        // Récupérer la position actuelle de l'utilisateur
        let userCoords = userLocation.getSavedLocation();
        if (!userCoords || !userCoords.latitude || !userCoords.longitude) {
            console.warn('📍 Position utilisateur non disponible, utilisation de la position par défaut');
            // Utiliser une position par défaut (Montpellier)
            userCoords = { latitude: 43.6109, longitude: 3.8772 };
        }

        // Construire l'URL avec les filtres
        const searchParams = new URLSearchParams(window.location.search);

        // Ajouter la position et le rayon
        searchParams.set('lat', userCoords.latitude);
        searchParams.set('lng', userCoords.longitude);
        searchParams.set('radius', document.getElementById('radius-selector')?.value || DEFAULT_RADIUS);

        // Log domains param for debugging
        const domainsParam = searchParams.get('domains');
        if (domainsParam) {
            console.log('🔍 Domain filter detected:', domainsParam);
        }

        // Vérifier si les filtres ont changé
        const queryString = searchParams.toString();
        if (queryString === lastQueryString && !forceRefresh) {
            console.log('ℹ️ Filtres inchangés, pas de rechargement nécessaire');
            return;
        }

        // Mettre à jour l'état
        lastQueryString = queryString;
        isLoading = true;

        // Afficher l'indicateur de chargement
        if (loadingIndicator) {
            loadingIndicator.style.display = 'block';
        }

        console.log('🔄 Chargement des créateurs avec filtres:', queryString);

        // Appeler l'API
        const url = `${API_URL}?${queryString}`;
        console.log('🔄 Fetching data from:', url);

        fetch(url)
            .then(response => {
                if (!response.ok) {
                    console.error('❌ API Error:', response.status, response.statusText);
                    throw new Error(`Erreur lors de la récupération des créateurs (${response.status})`);
                }
                return response.json();
            })
            .then(data => {
                console.log('✅ Données reçues:', data);
                creators = data.creators || [];

                if (creators.length === 0) {
                    console.log('⚠️ Aucun créateur trouvé avec ces filtres');
                } else {
                    console.log(`✅ ${creators.length} créateurs trouvés`);
                }

                // Mettre à jour la carte
                mapManager.renderCreators(creators);

                // Mettre à jour le compteur de résultats
                if (resultsCounter) {
                    resultsCounter.textContent = creators.length;
                }

                isLoading = false;

                // Cacher l'indicateur de chargement
                if (loadingIndicator) {
                    loadingIndicator.style.display = 'none';
                }
            })
            .catch(error => {
                console.error('❌ Erreur:', error);
                // Afficher un message d'erreur
                const creatorsListContent = document.getElementById('creators-list-content');
                if (creatorsListContent) {
                    creatorsListContent.innerHTML = `
                        <div class="alert alert-danger">
                            <h5><i class="fas fa-exclamation-triangle me-2"></i>Erreur</h5>
                            <p>${error.message || 'Impossible de charger les créateurs'}</p>
                            <button class="btn btn-sm btn-outline-danger mt-2" onclick="SearchCreators.reload(true)">
                                <i class="fas fa-sync-alt me-1"></i>Réessayer
                            </button>
                        </div>
                    `;
                }

                isLoading = false;

                // Cacher l'indicateur de chargement
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

        // Récupérer les domaines sélectionnés
        const domainCheckboxes = document.querySelectorAll('input[name="domains"]:checked');
        if (domainCheckboxes && domainCheckboxes.length > 0) {
            const domainIds = Array.from(domainCheckboxes).map(cb => cb.value);
            filters.domains = domainIds.join(',');
        }

        // Récupérer le filtre de genre
        const genderFilter = document.getElementById('map-gender-filter');
        if (genderFilter && genderFilter.value) {
            filters.gender = genderFilter.value;
        }

        // Récupérer le filtre de type de contenu
        const contentTypeFilter = document.getElementById('map-content-type-filter');
        if (contentTypeFilter && contentTypeFilter.value) {
            filters.content_type = contentTypeFilter.value;
        }

        // Récupérer les filtres d'âge
        const minAgeInput = document.getElementById('min-age-input');
        const maxAgeInput = document.getElementById('max-age-input');
        if (minAgeInput && minAgeInput.value) {
            filters.min_age = minAgeInput.value;
        }
        if (maxAgeInput && maxAgeInput.value) {
            filters.max_age = maxAgeInput.value;
        }

        // Récupérer les options additionnelles
        const canInvoiceFilter = document.getElementById('map-can-invoice');
        if (canInvoiceFilter && canInvoiceFilter.checked) {
            filters.can_invoice = 'on';
        }

        const verifiedOnlyFilter = document.getElementById('map-verified-only');
        if (verifiedOnlyFilter && verifiedOnlyFilter.checked) {
            filters.verified_only = 'on';
        }

        // Récupérer la note minimale
        const minRatingRadios = document.querySelectorAll('input[name="min_rating"]:checked');
        if (minRatingRadios && minRatingRadios.length > 0) {
            filters.min_rating = minRatingRadios[0].value;
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
     * Réinitialise tous les filtres
     */
    function resetFilters() {
        // Réinitialiser la recherche
        const searchQuery = document.getElementById('map-search-query');
        if (searchQuery) {
            searchQuery.value = '';
        }

        // Réinitialiser les domaines
        const domainCheckboxes = document.querySelectorAll('input[name="domains"]');
        if (domainCheckboxes) {
            domainCheckboxes.forEach(cb => cb.checked = false);
        }

        // Réinitialiser le genre
        const genderFilter = document.getElementById('map-gender-filter');
        if (genderFilter) {
            genderFilter.value = '';
        }

        // Réinitialiser le type de contenu
        const contentTypeFilter = document.getElementById('map-content-type-filter');
        if (contentTypeFilter) {
            contentTypeFilter.value = '';
        }

        // Réinitialiser les âges
        // Nous devons également réinitialiser le slider noUiSlider si disponible
        const ageSlider = document.getElementById('age-slider');
        if (ageSlider && ageSlider.noUiSlider) {
            ageSlider.noUiSlider.set([18, 80]);
        }
        const minAgeInput = document.getElementById('min-age-input');
        const maxAgeInput = document.getElementById('max-age-input');
        if (minAgeInput) minAgeInput.value = '18';
        if (maxAgeInput) maxAgeInput.value = '80';

        // Réinitialiser les options additionnelles
        const canInvoiceFilter = document.getElementById('map-can-invoice');
        if (canInvoiceFilter) {
            canInvoiceFilter.checked = false;
        }

        const verifiedOnlyFilter = document.getElementById('map-verified-only');
        if (verifiedOnlyFilter) {
            verifiedOnlyFilter.checked = false;
        }

        // Réinitialiser la note minimale
        const minRatingRadios = document.querySelectorAll('input[name="min_rating"]');
        if (minRatingRadios) {
            minRatingRadios.forEach(radio => radio.checked = false);
        }

        // Réinitialiser le rayon
        const radiusSelector = document.getElementById('radius-selector');
        if (radiusSelector) {
            radiusSelector.value = DEFAULT_RADIUS;
            const radiusValue = document.getElementById('radius-value');
            if (radiusValue) {
                radiusValue.textContent = DEFAULT_RADIUS;
            }
        }

        // Mettre à jour la carte
        if (mapManager) {
            mapManager.updateRadius(DEFAULT_RADIUS);
        }

        // Recharger les créateurs
        loadCreators();
    }

    /**
     * Recharge les créateurs avec les filtres actuels
     * @param {boolean} forceRefresh - Si true, force le rechargement des créateurs même si les filtres n'ont pas changé
     */
    function reload(forceRefresh = false) {
        console.log('SearchCreators.reload called with forceRefresh =', forceRefresh);
        loadCreators(forceRefresh);
    }

    // Exposer l'API publique
    return {
        init: init,
        reload: reload,
        getCreators: function () { return creators; },
        reset: resetFilters
    };
})(); 