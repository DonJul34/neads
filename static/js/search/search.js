/**
 * Script pour la page de recherche de créateurs
 * Gère les interactions et fonctionnalités AJAX
 */
document.addEventListener('DOMContentLoaded', function () {
    // Initialiser les tooltips Bootstrap
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Récupérer les éléments du DOM
    const mainSearchForm = document.getElementById('main-search-form');
    const filterForm = document.getElementById('filter-form');
    const advancedFiltersToggle = document.querySelector('[data-bs-toggle="collapse"][href="#advancedFilters"]');
    const resetButton = document.querySelector('a[href="{% url \'search_view\' %}"].btn-outline-danger');
    const searchInput = document.querySelector('input[name="query"]');
    const creatorsGrid = document.querySelector('.creators-grid');
    const loader = document.querySelector('.loader');

    /**
     * Affiche ou masque le loader pendant les requêtes AJAX
     * @param {boolean} show - True pour afficher, false pour masquer
     */
    function toggleLoader(show) {
        if (loader) {
            loader.style.display = show ? 'block' : 'none';
        }
    }

    /**
     * Effectue une recherche AJAX et met à jour les résultats
     * @param {FormData} formData - Données du formulaire
     */
    function performSearch(formData) {
        toggleLoader(true);

        // Construire l'URL avec les paramètres
        const params = new URLSearchParams(formData);
        const url = `${window.location.pathname}?${params.toString()}`;

        // Mise à jour de l'URL pour permettre le partage et l'historique
        window.history.pushState({}, '', url);

        // Effectuer la requête AJAX
        fetch(url, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json',
            }
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Erreur réseau');
                }
                return response.json();
            })
            .then(data => {
                updateResults(data);
                toggleLoader(false);
            })
            .catch(error => {
                console.error('Erreur lors de la recherche:', error);
                toggleLoader(false);
                // En cas d'erreur, recharger simplement la page
                window.location.reload();
            });
    }

    /**
     * Met à jour l'affichage des résultats avec les données reçues
     * @param {Object} data - Données reçues du serveur
     */
    function updateResults(data) {
        // Cette fonction serait à implémenter pour mettre à jour dynamiquement 
        // les résultats sans rechargement de page
        // Pour l'instant, on recharge la page pour simplicité
        window.location.reload();
    }

    // Gérer la soumission du formulaire principal
    if (mainSearchForm) {
        mainSearchForm.addEventListener('submit', function (e) {
            // Pour la version initiale, on laisse le comportement par défaut
            // qui recharge la page avec les résultats
            // À l'avenir, on pourrait intercepter la soumission pour AJAX
        });
    }

    // Gérer la soumission du formulaire de filtres avancés
    if (filterForm) {
        filterForm.addEventListener('submit', function (e) {
            // Pour la version initiale, on laisse le comportement par défaut
            // qui recharge la page avec les résultats filtrés
        });
    }

    // Focus automatique sur le champ de recherche lors du chargement
    if (searchInput && !searchInput.value) {
        searchInput.focus();
    }

    // Ajout de la classe active aux filtres sélectionnés
    const activeFilters = document.querySelectorAll('input[type="checkbox"]:checked, select option:selected');
    activeFilters.forEach(filter => {
        const filterGroup = filter.closest('.filter-group');
        if (filterGroup) {
            filterGroup.classList.add('has-active-filter');
        }
    });
}); 