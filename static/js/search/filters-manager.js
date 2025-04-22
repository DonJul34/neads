/**
 * Module de gestion des filtres de recherche de créateurs
 * Gère les interactions avec les filtres et leur application
 */
const FiltersManager = (function () {
    // Variables privées
    let filterForm;
    let mainSearchForm;
    let advancedFiltersContainer;
    let activeFiltersContainer;

    /**
     * Initialise le gestionnaire de filtres
     * @param {string} filterFormId - ID du formulaire de filtres avancés
     * @param {string} mainSearchFormId - ID du formulaire de recherche principal
     * @param {string} advancedFiltersContainerId - ID du conteneur de filtres avancés
     * @param {string} activeFiltersContainerId - ID du conteneur de filtres actifs (optionnel)
     */
    function initialize(filterFormId, mainSearchFormId, advancedFiltersContainerId, activeFiltersContainerId) {
        filterForm = document.getElementById(filterFormId);
        mainSearchForm = document.getElementById(mainSearchFormId);
        advancedFiltersContainer = document.getElementById(advancedFiltersContainerId);
        activeFiltersContainer = document.getElementById(activeFiltersContainerId);

        if (!filterForm || !mainSearchForm) {
            console.error("Formulaires de filtres introuvables");
            return;
        }

        // Attacher les gestionnaires d'événements
        attachEventListeners();

        // Récupérer et afficher les filtres actifs
        if (activeFiltersContainer) {
            renderActiveFilters();
        }
    }

    /**
     * Attache les gestionnaires d'événements aux éléments du formulaire
     */
    function attachEventListeners() {
        // Événement de changement pour tous les inputs du formulaire de filtres
        const filterInputs = filterForm.querySelectorAll('input, select');
        filterInputs.forEach(input => {
            input.addEventListener('change', function () {
                // Pour les checkboxes, on soumet le formulaire immédiatement
                if (input.type === 'checkbox' || input.tagName === 'SELECT') {
                    if (window.SearchConfig && window.SearchConfig.autoSubmit) {
                        filterForm.dispatchEvent(new Event('submit'));
                    }
                }
            });
        });

        // Événement de soumission du formulaire principal
        mainSearchForm.addEventListener('submit', function (e) {
            // Synchroniser la requête de recherche entre les deux formulaires
            const mainSearchQuery = mainSearchForm.querySelector('input[name="query"]').value;
            const filterFormQuery = filterForm.querySelector('input[name="query"]');
            if (filterFormQuery) {
                filterFormQuery.value = mainSearchQuery;
            }
        });

        // Événement de soumission du formulaire de filtres
        filterForm.addEventListener('submit', function (e) {
            // Synchroniser la requête de recherche entre les deux formulaires
            const filterFormQuery = filterForm.querySelector('input[name="query"]').value;
            const mainSearchQuery = mainSearchForm.querySelector('input[name="query"]');
            if (mainSearchQuery) {
                mainSearchQuery.value = filterFormQuery;
            }
        });
    }

    /**
     * Extrait et formate les filtres actifs à partir de l'URL
     * @return {Array} Liste des filtres actifs avec leurs valeurs
     */
    function getActiveFilters() {
        const urlParams = new URLSearchParams(window.location.search);
        const activeFilters = [];

        // Parcourir tous les paramètres de l'URL
        for (const [key, value] of urlParams.entries()) {
            if (key === 'page' || !value) continue;  // Ignorer la pagination et les valeurs vides

            // Trouver le label correspondant au filtre
            let label = key;
            let displayValue = value;

            // Obtenir le label depuis le formulaire
            const formElement = filterForm.querySelector(`[name="${key}"]`);
            if (formElement) {
                const labelElement = filterForm.querySelector(`label[for="${formElement.id}"]`);
                if (labelElement) {
                    label = labelElement.textContent.trim();
                }

                // Traitement spécial pour les selects
                if (formElement.tagName === 'SELECT') {
                    const selectedOption = formElement.querySelector(`option[value="${value}"]`);
                    if (selectedOption) {
                        displayValue = selectedOption.textContent.trim();
                    }
                }
            }

            activeFilters.push({
                key: key,
                label: label,
                value: value,
                displayValue: displayValue
            });
        }

        return activeFilters;
    }

    /**
     * Affiche les filtres actifs dans le conteneur dédié
     */
    function renderActiveFilters() {
        if (!activeFiltersContainer) return;

        const activeFilters = getActiveFilters();

        // Ne rien afficher s'il n'y a pas de filtres actifs
        if (activeFilters.length === 0) {
            activeFiltersContainer.style.display = 'none';
            return;
        }

        // Construire le HTML des filtres actifs
        let filtersHtml = `
            <div class="active-filters-header">
                <h6 class="mb-2">Filtres actifs:</h6>
            </div>
            <div class="active-filters-list">
        `;

        activeFilters.forEach(filter => {
            filtersHtml += `
                <span class="badge bg-primary me-2 mb-2">
                    ${filter.label}: ${filter.displayValue}
                    <a href="#" class="text-white ms-1 remove-filter" data-filter-key="${filter.key}" data-filter-value="${filter.value}">
                        <i class="fas fa-times"></i>
                    </a>
                </span>
            `;
        });

        filtersHtml += `
            </div>
            <div class="mt-2">
                <a href="/creators/search/" class="btn btn-sm btn-outline-danger">
                    <i class="fas fa-times me-1"></i> Réinitialiser tous les filtres
                </a>
            </div>
        `;

        // Mettre à jour le conteneur
        activeFiltersContainer.innerHTML = filtersHtml;
        activeFiltersContainer.style.display = 'block';

        // Attacher les gestionnaires d'événements pour la suppression de filtres
        const removeButtons = activeFiltersContainer.querySelectorAll('.remove-filter');
        removeButtons.forEach(button => {
            button.addEventListener('click', function (e) {
                e.preventDefault();
                removeFilter(this.dataset.filterKey, this.dataset.filterValue);
            });
        });
    }

    /**
     * Supprime un filtre et recharge la page
     * @param {string} key - Clé du filtre à supprimer
     * @param {string} value - Valeur du filtre à supprimer (pour les filtres multi-valeurs)
     */
    function removeFilter(key, value) {
        const urlParams = new URLSearchParams(window.location.search);

        // Pour les filtres multi-valeurs (comme les domaines), on doit traiter différemment
        if (key === 'domains') {
            const domains = urlParams.getAll('domains');
            urlParams.delete('domains');

            // Réajouter tous les domaines sauf celui à supprimer
            domains.forEach(domain => {
                if (domain !== value) {
                    urlParams.append('domains', domain);
                }
            });
        } else {
            // Supprimer simplement le paramètre
            urlParams.delete(key);
        }

        // Recharger la page avec les nouveaux paramètres
        window.location.href = `${window.location.pathname}?${urlParams.toString()}`;
    }

    /**
     * Réinitialise tous les filtres
     */
    function resetAllFilters() {
        window.location.href = '/creators/search/';
    }

    /**
     * Ouvre ou ferme la section des filtres avancés
     * @param {boolean} show - True pour ouvrir, false pour fermer
     */
    function toggleAdvancedFilters(show) {
        if (!advancedFiltersContainer) return;

        if (show) {
            advancedFiltersContainer.classList.add('show');
        } else {
            advancedFiltersContainer.classList.remove('show');
        }
    }

    // API publique
    return {
        initialize,
        getActiveFilters,
        renderActiveFilters,
        resetAllFilters,
        toggleAdvancedFilters
    };
})(); 