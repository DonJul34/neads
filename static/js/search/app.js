/**
 * Script principal pour la page de recherche de créateurs
 * Configure et initialise tous les modules
 */

// Configuration globale pour la recherche
window.SearchConfig = {
    autoSubmit: false,         // Soumettre automatiquement les filtres lors des changements
    enableAjaxSearch: false,   // Utiliser AJAX pour les recherches (sans rechargement de page)
    resultsPerPage: 15,        // Nombre de résultats par page
    highlightMatches: true     // Mettre en surbrillance les termes de recherche dans les résultats
};

document.addEventListener('DOMContentLoaded', function () {
    // Initialiser la gestion des filtres
    if (typeof FiltersManager !== 'undefined') {
        FiltersManager.initialize(
            'filter-form',              // ID du formulaire de filtres
            'main-search-form',         // ID du formulaire principal
            'advancedFilters',          // ID du conteneur de filtres avancés
            'active-filters-container'  // ID du conteneur de filtres actifs
        );
    }

    // Initialiser le rendu des résultats
    if (typeof ResultsRenderer !== 'undefined') {
        ResultsRenderer.initialize(
            'search-results',       // ID du conteneur de résultats
            'pagination-container', // ID du conteneur de pagination
            'total-count'           // ID de l'élément affichant le nombre total
        );
    }

    // Focus automatique sur le champ de recherche
    const searchInput = document.querySelector('input[name="query"].main-search-input');
    if (searchInput && !searchInput.value) {
        searchInput.focus();
    }

    // Gérer les clics sur le bouton pour afficher/masquer les filtres avancés
    const advancedFiltersToggle = document.querySelector('[data-bs-toggle="collapse"][href="#advancedFilters"]');
    if (advancedFiltersToggle) {
        advancedFiltersToggle.addEventListener('click', function () {
            // La fonctionnalité de bascule est gérée par Bootstrap
            // On peut ajouter des comportements supplémentaires ici si nécessaire
        });
    }

    // Réinitialisation des filtres
    const resetButton = document.querySelector('a[href*="search_view"].btn-outline-danger');
    if (resetButton) {
        resetButton.addEventListener('click', function (e) {
            // Afficher une confirmation avant de réinitialiser
            if (window.SearchConfig.confirmReset && !confirm('Êtes-vous sûr de vouloir réinitialiser tous les filtres?')) {
                e.preventDefault();
            }
        });
    }

    // Détection du mode de recherche avancée
    const urlParams = new URLSearchParams(window.location.search);
    const hasAdvancedFilters = Array.from(urlParams.keys()).some(key =>
        key !== 'query' && key !== 'page'
    );

    // Ouvrir automatiquement les filtres avancés si des filtres sont actifs
    if (hasAdvancedFilters && typeof bootstrap !== 'undefined') {
        const advancedFiltersCollapse = document.getElementById('advancedFilters');
        if (advancedFiltersCollapse) {
            const bsCollapse = new bootstrap.Collapse(advancedFiltersCollapse, {
                show: true
            });
        }
    }

    console.log('Module de recherche initialisé avec succès');
}); 