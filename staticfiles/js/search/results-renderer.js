/**
 * Module pour le rendu des résultats de recherche de créateurs
 * Gère la création dynamique des cartes de créateurs et pagination
 */
const ResultsRenderer = (function () {
    // Éléments DOM référencés
    let resultsContainer;
    let paginationContainer;
    let totalCountElement;

    /**
     * Initialise le module avec les éléments DOM nécessaires
     * @param {string} resultContainerId - ID du conteneur de résultats
     * @param {string} paginationContainerId - ID du conteneur de pagination
     * @param {string} countElementId - ID de l'élément affichant le nombre total
     */
    function initialize(resultContainerId, paginationContainerId, countElementId) {
        resultsContainer = document.getElementById(resultContainerId);
        paginationContainer = document.getElementById(paginationContainerId);
        totalCountElement = document.getElementById(countElementId);

        if (!resultsContainer) {
            console.error("Conteneur de résultats introuvable");
        }
    }

    /**
     * Génère le HTML pour une carte de créateur
     * @param {Object} creator - Données du créateur
     * @return {string} HTML de la carte
     */
    function createCreatorCard(creator) {
        // Génération des étoiles de notation
        const stars = renderStars(creator.rating);

        // Génération des badges de domaines
        const domainBadges = creator.domains.map(domain =>
            `<span class="domain-badge">${domain.name}</span>`
        ).join('');

        // Construction du HTML de la carte
        return `
        <div class="col">
            <div class="card h-100 shadow-sm creator-card">
                <div class="creator-img-container">
                    ${creator.thumbnail
                ? `<img src="${creator.thumbnail}" alt="${creator.full_name}" class="card-img-top">`
                : `<img src="https://via.placeholder.com/300x200?text=Pas+d'image" alt="Placeholder" class="card-img-top">`
            }
                </div>
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start">
                        <h3 class="card-title h5 mb-1">${creator.full_name}</h3>
                        ${creator.verified
                ? `<span class="verified-icon" data-bs-toggle="tooltip" title="Vérifié par NEADS">
                                <i class="fas fa-check-circle"></i>
                               </span>`
                : ''
            }
                    </div>
                    
                    <p class="card-text text-muted small mb-2">
                        ${creator.age} ans - ${creator.gender}
                        ${creator.location ? `<br>${creator.location}` : ''}
                    </p>
                    
                    <div class="mb-2">
                        <span class="star-rating">${stars}</span>
                        <small class="text-muted">(${creator.total_ratings})</small>
                    </div>
                    
                    <div class="domain-badges mb-3">
                        ${domainBadges}
                    </div>
                    
                    <a href="/creators/creator/${creator.id}/" class="btn btn-sm btn-outline-primary stretched-link">
                        Voir le profil
                    </a>
                </div>
            </div>
        </div>
        `;
    }

    /**
     * Génère le HTML pour les étoiles de notation
     * @param {number} rating - Note (de 0 à 5)
     * @return {string} HTML des étoiles
     */
    function renderStars(rating) {
        let stars = '';
        for (let i = 1; i <= 5; i++) {
            if (i <= rating) {
                stars += '<i class="fas fa-star"></i>';
            } else if (i <= rating + 0.5) {
                stars += '<i class="fas fa-star-half-alt"></i>';
            } else {
                stars += '<i class="far fa-star"></i>';
            }
        }
        return stars;
    }

    /**
     * Génère le HTML pour la pagination
     * @param {number} currentPage - Page actuelle
     * @param {number} totalPages - Nombre total de pages
     * @param {string} urlParams - Paramètres d'URL à conserver (sans le paramètre page)
     * @return {string} HTML de la pagination
     */
    function createPagination(currentPage, totalPages, urlParams) {
        if (totalPages <= 1) return '';

        let paginationHtml = `
        <nav aria-label="Pagination des résultats" class="mt-5">
            <ul class="pagination justify-content-center">
        `;

        // Bouton précédent
        if (currentPage > 1) {
            paginationHtml += `
                <li class="page-item">
                    <a class="page-link" href="?${urlParams}&page=${currentPage - 1}" aria-label="Précédent">
                        <span aria-hidden="true">&laquo;</span>
                    </a>
                </li>
            `;
        } else {
            paginationHtml += `
                <li class="page-item disabled">
                    <span class="page-link">&laquo;</span>
                </li>
            `;
        }

        // Pages numérotées
        for (let i = 1; i <= totalPages; i++) {
            if (i === currentPage) {
                paginationHtml += `<li class="page-item active"><span class="page-link">${i}</span></li>`;
            } else {
                paginationHtml += `
                    <li class="page-item">
                        <a class="page-link" href="?${urlParams}&page=${i}">${i}</a>
                    </li>
                `;
            }
        }

        // Bouton suivant
        if (currentPage < totalPages) {
            paginationHtml += `
                <li class="page-item">
                    <a class="page-link" href="?${urlParams}&page=${currentPage + 1}" aria-label="Suivant">
                        <span aria-hidden="true">&raquo;</span>
                    </a>
                </li>
            `;
        } else {
            paginationHtml += `
                <li class="page-item disabled">
                    <span class="page-link">&raquo;</span>
                </li>
            `;
        }

        paginationHtml += `
            </ul>
        </nav>
        `;

        return paginationHtml;
    }

    /**
     * Affiche les créateurs dans le conteneur de résultats
     * @param {Array} creators - Liste des créateurs à afficher
     * @param {Object} paginationData - Données de pagination
     */
    function renderResults(creators, paginationData) {
        if (!resultsContainer) return;

        // Vider le conteneur
        resultsContainer.innerHTML = '';

        if (creators.length === 0) {
            // Afficher un message si aucun résultat
            resultsContainer.innerHTML = `
                <div class="empty-state">
                    <div class="search-icon">
                        <i class="fas fa-search"></i>
                    </div>
                    <h3>Aucun créateur ne correspond à vos critères</h3>
                    <p class="text-muted">Essayez d'élargir votre recherche ou de modifier vos filtres.</p>
                    <a href="/creators/search/" class="btn btn-outline-primary mt-2">
                        <i class="fas fa-redo me-1"></i> Réinitialiser la recherche
                    </a>
                </div>
            `;
        } else {
            // Créer la grille de résultats
            let resultsHtml = '<div class="row row-cols-1 row-cols-md-2 row-cols-lg-3 g-4">';

            // Ajouter chaque carte de créateur
            creators.forEach(creator => {
                resultsHtml += createCreatorCard(creator);
            });

            resultsHtml += '</div>';

            // Ajouter au conteneur
            resultsContainer.innerHTML = resultsHtml;

            // Réinitialiser les tooltips
            const tooltips = new bootstrap.Tooltip(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        }

        // Mettre à jour la pagination si nécessaire
        if (paginationContainer && paginationData) {
            const paginationHtml = createPagination(
                paginationData.page,
                paginationData.total_pages,
                paginationData.url_params
            );
            paginationContainer.innerHTML = paginationHtml;
        }

        // Mettre à jour le compteur
        if (totalCountElement) {
            totalCountElement.textContent = creators.length;
        }
    }

    // API publique
    return {
        initialize,
        renderResults
    };
})(); 