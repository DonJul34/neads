/**
 * Module DiscoverCreators
 * Gère la recherche et l'affichage des créateurs externes
 */
const DiscoverCreators = (function () {
    // Configuration
    const API_URL = '/api/creators/search';
    const ITEMS_PER_PAGE = 12;

    // État
    let currentPage = 1;
    let totalPages = 0;
    let currentFilters = {};
    let isLoading = false;

    // Éléments DOM
    let resultsContainer;
    let searchForm;
    let loadingIndicator;
    let emptyState;
    let filterElements;

    /**
     * Initialise le module
     */
    function init() {
        // Récupérer les éléments DOM
        resultsContainer = document.getElementById('results-container');
        searchForm = document.getElementById('search-form');
        loadingIndicator = document.getElementById('loading-indicator');
        emptyState = document.getElementById('empty-state');

        // Récupérer tous les éléments de filtre
        filterElements = {
            query: document.getElementById('search-query'),
            domain: document.getElementById('domain-filter'),
            platform: document.getElementById('platform-filter'),
            followers: document.getElementById('followers-filter'),
            location: document.getElementById('location-filter')
        };

        // Initialiser les événements
        bindEvents();

        // Charger les créateurs initiaux
        loadCreators();
    }

    /**
     * Attache les gestionnaires d'événements
     */
    function bindEvents() {
        // Soumission du formulaire de recherche
        searchForm.addEventListener('submit', function (e) {
            e.preventDefault();
            currentPage = 1;
            loadCreators();
        });

        // Changement dans les filtres
        Object.values(filterElements).forEach(element => {
            if (element) {
                element.addEventListener('change', function () {
                    currentPage = 1;
                    loadCreators();
                });
            }
        });

        // Scroll infini pour charger plus de créateurs
        window.addEventListener('scroll', debounce(function () {
            if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 500 && !isLoading && currentPage < totalPages) {
                currentPage++;
                loadCreators(true);
            }
        }, 200));
    }

    /**
     * Charge les créateurs depuis l'API
     * @param {boolean} append - Si true, ajoute les résultats aux existants
     */
    function loadCreators(append = false) {
        // Mettre à jour les filtres actuels
        currentFilters = {
            query: filterElements.query.value,
            domain: filterElements.domain.value,
            platform: filterElements.platform.value,
            followers: filterElements.followers.value,
            location: filterElements.location.value,
            page: currentPage,
            per_page: ITEMS_PER_PAGE
        };

        // Afficher le chargement
        isLoading = true;
        if (!append) {
            resultsContainer.innerHTML = '';
            loadingIndicator.style.display = 'flex';
            emptyState.style.display = 'none';
        }

        // Construire l'URL avec les paramètres de requête
        const queryParams = new URLSearchParams();
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
                isLoading = false;
                loadingIndicator.style.display = 'none';

                // Mettre à jour la pagination
                totalPages = Math.ceil(data.total / ITEMS_PER_PAGE);

                if (data.creators.length === 0 && !append) {
                    // Aucun résultat
                    emptyState.style.display = 'flex';
                } else {
                    // Afficher les résultats
                    renderCreators(data.creators, append);
                }
            })
            .catch(error => {
                console.error('Erreur:', error);
                isLoading = false;
                loadingIndicator.style.display = 'none';

                if (!append) {
                    resultsContainer.innerHTML = `
                        <div class="col-12 text-center py-5">
                            <div class="alert alert-danger">
                                Une erreur est survenue lors de la recherche. Veuillez réessayer plus tard.
                            </div>
                        </div>
                    `;
                }
            });
    }

    /**
     * Affiche les créateurs dans le conteneur de résultats
     * @param {Array} creators - Liste des créateurs à afficher
     * @param {boolean} append - Si true, ajoute les résultats aux existants
     */
    function renderCreators(creators, append = false) {
        if (!append) {
            resultsContainer.innerHTML = '';
        }

        creators.forEach(creator => {
            const creatorCard = createCreatorCard(creator);
            resultsContainer.appendChild(creatorCard);
        });
    }

    /**
     * Vérifie si l'utilisateur courant est un client
     * @returns {boolean} True si l'utilisateur est un client
     */
    function isClientUser() {
        // Vérifier si un élément avec data-user-role existe et a la valeur "client"
        const userRoleElement = document.querySelector('[data-user-role]');
        return userRoleElement && userRoleElement.getAttribute('data-user-role') === 'client';
    }

    /**
     * Formate le nom d'un créateur pour les clients (prénom + initiale du nom de famille)
     * @param {string} firstName - Prénom du créateur
     * @param {string} lastName - Nom de famille du créateur
     * @returns {string} Nom formaté pour les clients
     */
    function getCreatorName(firstName, lastName) {
        if (isClientUser()) {
            return `${firstName} ${lastName.charAt(0)}.`;
        }
        return `${firstName} ${lastName}`;
    }

    /**
     * Crée une carte de créateur
     * @param {Object} creator - Données du créateur
     * @return {HTMLElement} - Élément DOM de la carte
     */
    function createCreatorCard(creator) {
        const colElement = document.createElement('div');
        colElement.className = 'col-lg-4 col-md-6 col-12 mb-4';

        // Calculer le score moyen (sur 5)
        const avgScore = creator.rating ? (creator.rating.average_score / 2).toFixed(1) : '0.0';

        // Générer les badges de plateforme
        const platformBadges = creator.platforms.map(platform => {
            return `<span class="platform-badge ${platform.toLowerCase()}">${platform}</span>`;
        }).join('');

        // Formater les métriques
        const formattedFollowers = formatNumber(creator.followers_count);
        const formattedEngagement = creator.engagement_rate ? creator.engagement_rate.toFixed(2) + '%' : 'N/A';

        // Obtenir le nom formaté
        const creatorName = getCreatorName(creator.first_name, creator.last_name);

        // Construire la carte HTML
        colElement.innerHTML = `
            <div class="result-card">
                <div class="card-header">
                    <div class="profile-image">
                        <img src="${creator.profile_image || '/static/img/default-avatar.png'}" alt="${creatorName}">
                    </div>
                    <div class="creator-info">
                        <h3 class="creator-name">${creatorName}</h3>
                        <p class="creator-location">
                            <i class="fas fa-map-marker-alt"></i> ${creator.location.city || 'Non spécifié'}, ${creator.location.country || ''}
                        </p>
                        <div class="platforms-container">
                            ${platformBadges}
                        </div>
                    </div>
                    <div class="score-container">
                        <div class="score-value">${avgScore}</div>
                        <div class="score-stars">
                            ${renderStars(avgScore)}
                        </div>
                        <div class="rating-count">${creator.rating ? creator.rating.count : 0} avis</div>
                    </div>
                </div>
                <div class="card-body">
                    <div class="domains">
                        ${creator.domains.map(domain => `<span class="domain-badge">${domain.name}</span>`).join('')}
                    </div>
                    <div class="metrics">
                        <div class="metric">
                            <div class="metric-value">${formattedFollowers}</div>
                            <div class="metric-label">Abonnés</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">${formattedEngagement}</div>
                            <div class="metric-label">Engagement</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">${creator.media_count || 0}</div>
                            <div class="metric-label">Médias</div>
                        </div>
                    </div>
                </div>
                <div class="card-footer">
                    <a href="/creators/${creator.id}/" class="btn btn-outline-primary btn-sm">Voir le profil</a>
                    <button class="btn btn-primary btn-sm add-favorite" data-creator-id="${creator.id}">
                        <i class="far fa-heart"></i> Ajouter aux favoris
                    </button>
                </div>
            </div>
        `;

        // Ajouter l'événement pour ajouter aux favoris
        const favoriteBtn = colElement.querySelector('.add-favorite');
        if (favoriteBtn) {
            favoriteBtn.addEventListener('click', function () {
                addToFavorites(creator.id);
            });
        }

        return colElement;
    }

    /**
     * Génère les étoiles HTML en fonction de la note
     * @param {number} score - Note sur 5
     * @return {string} - HTML des étoiles
     */
    function renderStars(score) {
        const fullStars = Math.floor(score);
        const halfStar = score % 1 >= 0.5;
        const emptyStars = 5 - fullStars - (halfStar ? 1 : 0);

        let starsHTML = '';

        // Étoiles pleines
        for (let i = 0; i < fullStars; i++) {
            starsHTML += '<i class="fas fa-star"></i>';
        }

        // Demi-étoile
        if (halfStar) {
            starsHTML += '<i class="fas fa-star-half-alt"></i>';
        }

        // Étoiles vides
        for (let i = 0; i < emptyStars; i++) {
            starsHTML += '<i class="far fa-star"></i>';
        }

        return starsHTML;
    }

    /**
     * Ajoute un créateur aux favoris
     * @param {number} creatorId - ID du créateur
     */
    function addToFavorites(creatorId) {
        // Implémenter la logique pour ajouter aux favoris
        // Cette fonction enverra une requête au serveur
        fetch('/api/favorites/add/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
                creator_id: creatorId
            })
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Erreur lors de l\'ajout aux favoris');
                }
                return response.json();
            })
            .then(data => {
                // Mettre à jour l'UI
                const btn = document.querySelector(`.add-favorite[data-creator-id="${creatorId}"]`);
                if (btn) {
                    btn.innerHTML = '<i class="fas fa-heart"></i> Ajouté aux favoris';
                    btn.classList.remove('btn-primary');
                    btn.classList.add('btn-success');
                    btn.disabled = true;
                }

                // Afficher une notification
                showNotification('Créateur ajouté à vos favoris avec succès!', 'success');
            })
            .catch(error => {
                console.error('Erreur:', error);
                showNotification('Une erreur est survenue lors de l\'ajout aux favoris.', 'error');
            });
    }

    /**
     * Récupère le token CSRF à partir des cookies
     * @return {string} - Token CSRF
     */
    function getCSRFToken() {
        const name = 'csrftoken';
        const cookieValue = document.cookie.split('; ')
            .find(row => row.startsWith(name + '='))
            ?.split('=')[1];
        return cookieValue || '';
    }

    /**
     * Affiche une notification à l'utilisateur
     * @param {string} message - Message à afficher
     * @param {string} type - Type de notification (success, error, warning, info)
     */
    function showNotification(message, type) {
        // Vérifier si la div de notification existe déjà
        let notificationContainer = document.getElementById('notification-container');

        if (!notificationContainer) {
            // Créer le conteneur de notification
            notificationContainer = document.createElement('div');
            notificationContainer.id = 'notification-container';
            notificationContainer.style.position = 'fixed';
            notificationContainer.style.top = '20px';
            notificationContainer.style.right = '20px';
            notificationContainer.style.zIndex = '9999';
            document.body.appendChild(notificationContainer);
        }

        // Créer la notification
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show`;
        notification.role = 'alert';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;

        // Ajouter la notification au conteneur
        notificationContainer.appendChild(notification);

        // Supprimer automatiquement après 5 secondes
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                notification.remove();
            }, 150);
        }, 5000);
    }

    /**
     * Formate un nombre (ex: 1200 -> 1.2K)
     * @param {number} num - Nombre à formater
     * @return {string} - Nombre formaté
     */
    function formatNumber(num) {
        if (!num) return '0';

        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        } else {
            return num.toString();
        }
    }

    /**
     * Fonction debounce pour limiter les appels fréquents
     * @param {Function} func - Fonction à exécuter
     * @param {number} wait - Délai d'attente en ms
     * @return {Function} - Fonction debounced
     */
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // API publique
    return {
        init: init
    };
})();

// Initialiser le module quand le DOM est chargé
document.addEventListener('DOMContentLoaded', DiscoverCreators.init); 