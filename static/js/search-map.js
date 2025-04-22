/**
 * Script pour la carte de recherche de créateurs
 * Dépend de Leaflet et de UserLocation
 */

let searchMap;
let userMarker;
let creatorMarkers = [];
let radiusCircle;
let currentRadius = 50; // Rayon par défaut en km

/**
 * Initialise la carte de recherche
 * @param {string} mapElementId - ID de l'élément DOM de la carte
 * @param {string} radiusSelectorId - ID du sélecteur de rayon (optionnel)
 */
function initSearchMap(mapElementId, radiusSelectorId = null) {
    // Initialiser la carte
    const defaultPosition = UserLocation.DEFAULT_COORDS;
    searchMap = L.map(mapElementId).setView([defaultPosition.latitude, defaultPosition.longitude], 5);

    // Ajouter le fond de carte
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(searchMap);

    // Ajouter les contrôles
    L.control.scale().addTo(searchMap);

    // Ajouter le contrôle plein écran
    const fullscreenControl = document.querySelector('.fullscreen-toggle');
    if (fullscreenControl) {
        fullscreenControl.addEventListener('click', function () {
            const mapContainer = document.querySelector('.search-map-container');
            if (mapContainer) {
                mapContainer.classList.toggle('fullscreen');
                // Mettre à jour la taille de la carte
                setTimeout(() => {
                    searchMap.invalidateSize();
                }, 100);
            }
        });
    }

    // Localiser l'utilisateur
    const locateButton = document.querySelector('.locate-me-button');
    if (locateButton) {
        locateButton.addEventListener('click', function () {
            // Montrer un indicateur de chargement
            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

            UserLocation.getUserLocation(
                function (coords) {
                    // Réinitialiser l'icône du bouton
                    if (locateButton) {
                        locateButton.innerHTML = '<i class="fas fa-location-arrow"></i>';
                    }

                    // Mettre à jour la position sur la carte
                    addUserMarker({
                        lat: coords.latitude,
                        lng: coords.longitude
                    });

                    // Charger les créateurs avec la nouvelle position
                    loadCreators();

                    // Créer un événement pour notifier que la localisation utilisateur est disponible
                    const event = new CustomEvent('user-location-ready', {
                        detail: {
                            lat: coords.latitude,
                            lng: coords.longitude
                        }
                    });
                    document.dispatchEvent(event);
                },
                function (error) {
                    // Réinitialiser l'icône du bouton
                    if (locateButton) {
                        locateButton.innerHTML = '<i class="fas fa-location-arrow"></i>';
                    }

                    console.error('Erreur de géolocalisation:', error);
                    handleLocationError(mapElementId);
                }
            );
        });
    }

    // Si un sélecteur de rayon est fourni, configurer l'événement de changement
    if (radiusSelectorId) {
        const radiusSelector = document.getElementById(radiusSelectorId);
        if (radiusSelector) {
            radiusSelector.addEventListener('change', function () {
                currentRadius = parseInt(this.value);

                // Mettre à jour le cercle de rayon
                if (userMarker) {
                    updateRadiusCircle(userMarker.getLatLng());
                }

                // Charger les créateurs avec le nouveau rayon
                loadCreators();

                // Créer un événement pour notifier que le rayon a changé
                const event = new CustomEvent('radius-changed', {
                    detail: {
                        radius: currentRadius
                    }
                });
                document.dispatchEvent(event);
            });
        }
    }

    // Configurer le clic sur la carte pour définir la position de l'utilisateur
    searchMap.on('click', function (e) {
        addUserMarker(e.latlng);

        // Charger les créateurs avec la nouvelle position
        loadCreators();

        // Créer un événement pour notifier que la position a changé
        const event = new CustomEvent('user-location-changed', {
            detail: {
                lat: e.latlng.lat,
                lng: e.latlng.lng
            }
        });
        document.dispatchEvent(event);
    });

    // Essayer d'obtenir la localisation de l'utilisateur au démarrage
    UserLocation.getUserLocation(
        function (coords) {
            addUserMarker({
                lat: coords.latitude,
                lng: coords.longitude
            });

            // Charger les créateurs avec la position initiale
            loadCreators();

            // Créer un événement pour notifier que la localisation utilisateur est disponible
            const event = new CustomEvent('user-location-ready', {
                detail: {
                    lat: coords.latitude,
                    lng: coords.longitude
                }
            });
            document.dispatchEvent(event);
        },
        function (error) {
            console.error('Erreur de géolocalisation:', error);
            handleLocationError(mapElementId);
        }
    );
}

/**
 * Ajoute ou met à jour le marqueur de l'utilisateur
 * @param {Object} coords - Coordonnées {lat, lng}
 */
function addUserMarker(coords) {
    // Si un marqueur existe déjà, le mettre à jour
    if (userMarker) {
        userMarker.setLatLng(coords);
    } else {
        // Sinon, créer un nouveau marqueur
        const userIcon = L.divIcon({
            className: 'user-marker',
            html: '<i class="fas fa-user-circle"></i>',
            iconSize: [30, 30],
            iconAnchor: [15, 15]
        });

        userMarker = L.marker(coords, {
            icon: userIcon,
            zIndexOffset: 1000
        }).addTo(searchMap);

        userMarker.bindPopup('Votre position');
    }

    // Mettre à jour le cercle de rayon
    updateRadiusCircle(coords);

    // Centrer la carte sur la position de l'utilisateur
    searchMap.setView(coords, 10);
}

/**
 * Met à jour le cercle de rayon autour de l'utilisateur
 * @param {Object} center - Coordonnées du centre {lat, lng}
 */
function updateRadiusCircle(center) {
    // Si un cercle existe déjà, le mettre à jour
    if (radiusCircle) {
        radiusCircle.setLatLng(center);
        radiusCircle.setRadius(currentRadius * 1000); // Convertir km en mètres
    } else {
        // Sinon, créer un nouveau cercle
        radiusCircle = L.circle(center, {
            radius: currentRadius * 1000, // Convertir km en mètres
            fillColor: '#007bff',
            fillOpacity: 0.1,
            color: '#007bff',
            weight: 1
        }).addTo(searchMap);
    }
}

/**
 * Charge les créateurs depuis l'API en fonction de la position et du rayon
 */
function loadCreators() {
    // Si l'utilisateur n'est pas localisé, ne rien faire
    if (!userMarker) {
        return;
    }

    // Récupérer les coordonnées de l'utilisateur
    const userPosition = userMarker.getLatLng();

    // Récupérer les filtres du formulaire de recherche
    const searchForm = document.getElementById('search-form');
    const formData = searchForm ? new FormData(searchForm) : new FormData();
    const queryParams = new URLSearchParams();

    // Ajouter les coordonnées et le rayon
    queryParams.append('lat', userPosition.lat);
    queryParams.append('lng', userPosition.lng);
    queryParams.append('radius', currentRadius);

    // Ajouter les autres filtres du formulaire
    for (const [key, value] of formData.entries()) {
        if (value) {
            queryParams.append(key, value);
        }
    }

    // Afficher un indicateur de chargement
    const mapElement = searchMap.getContainer();
    let loadingIndicator = mapElement.querySelector('.map-loading');

    if (!loadingIndicator) {
        loadingIndicator = document.createElement('div');
        loadingIndicator.className = 'map-loading';
        loadingIndicator.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        mapElement.appendChild(loadingIndicator);
    } else {
        loadingIndicator.style.display = 'flex';
    }

    // Faire la requête à l'API
    fetch(`/api/creators/map-search/?${queryParams.toString()}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Erreur lors de la récupération des créateurs');
            }
            return response.json();
        })
        .then(data => {
            // Cacher l'indicateur de chargement
            if (loadingIndicator) {
                loadingIndicator.style.display = 'none';
            }

            // Afficher les créateurs sur la carte
            renderCreators(data.creators);

            // Mettre à jour le compteur
            updateCreatorCount(data.total);
        })
        .catch(error => {
            console.error('Erreur:', error);

            // Cacher l'indicateur de chargement
            if (loadingIndicator) {
                loadingIndicator.style.display = 'none';
            }

            // Afficher un message d'erreur
            const errorControl = L.control({ position: 'bottomleft' });
            errorControl.onAdd = function () {
                const div = L.DomUtil.create('div', 'map-error-message');
                div.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-circle me-2"></i>
                        Erreur lors du chargement des créateurs. Veuillez réessayer.
                    </div>
                `;
                return div;
            };
            errorControl.addTo(searchMap);

            // Disparaître après 5 secondes
            setTimeout(() => {
                const messageElement = document.querySelector('.map-error-message');
                if (messageElement && messageElement.parentNode) {
                    messageElement.parentNode.removeChild(messageElement);
                }
            }, 5000);
        });
}

/**
 * Met à jour le compteur de créateurs
 * @param {number} count - Nombre de créateurs
 */
function updateCreatorCount(count) {
    const countElements = document.querySelectorAll('.map-results-count');
    if (countElements.length > 0) {
        countElements.forEach(element => {
            element.textContent = `${count} créateur${count > 1 ? 's' : ''} sur la carte`;
        });
    }
}

/**
 * Affiche les créateurs sur la carte
 * @param {Array} creators - Tableau d'objets créateurs avec lat, lng, et autres données
 */
function renderCreators(creators) {
    // Supprimer les marqueurs existants
    if (creatorMarkers.length > 0) {
        creatorMarkers.forEach(marker => {
            searchMap.removeLayer(marker);
        });
        creatorMarkers = [];
    }

    // Ajouter les nouveaux marqueurs
    creators.forEach(creator => {
        const marker = L.marker([creator.lat, creator.lng]).addTo(searchMap);

        // Utiliser la distance fournie par l'API
        let distanceText = '';
        if (creator.distance !== undefined) {
            distanceText = `<span class="badge bg-info">${creator.distance} km</span>`;
        }

        // Créer le contenu du popup
        const popupContent = `
            <div class="creator-popup">
                ${creator.image ? `<img src="${creator.image}" alt="${creator.name}">` : ''}
                <h5>${creator.name}</h5>
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <div class="star-rating">
                        ${renderStars(creator.rating || 0)}
                        <span class="ms-1 text-muted small">(${creator.rating || 0})</span>
                    </div>
                    ${distanceText}
                </div>
                <a href="${creator.url}" class="btn btn-sm btn-primary">Voir le profil</a>
            </div>
        `;

        marker.bindPopup(popupContent);
        creatorMarkers.push(marker);
    });

    // Déclencher un événement pour indiquer que les créateurs ont été rendus
    const event = new CustomEvent('creatorsRendered', {
        detail: { creators: creators }
    });
    document.dispatchEvent(event);
}

/**
 * Génère le HTML pour l'affichage des étoiles de notation
 * @param {number} rating - Note de 0 à 5
 * @returns {string} HTML pour l'affichage des étoiles
 */
function renderStars(rating) {
    let stars = '';
    for (let i = 1; i <= 5; i++) {
        if (i <= rating) {
            stars += '<i class="fas fa-star text-warning"></i>';
        } else if (i - 0.5 <= rating) {
            stars += '<i class="fas fa-star-half-alt text-warning"></i>';
        } else {
            stars += '<i class="far fa-star text-warning"></i>';
        }
    }
    return stars;
}

/**
 * Fonction pour gérer le cas où nous ne pouvons pas obtenir la géolocalisation de l'utilisateur
 * @param {string} mapElementId - ID de l'élément DOM de la carte
 */
function handleLocationError(mapElementId) {
    // Vérifier si la carte existe
    if (!searchMap && mapElementId) {
        const defaultPosition = UserLocation.DEFAULT_COORDS;
        searchMap = L.map(mapElementId).setView([defaultPosition.latitude, defaultPosition.longitude], 5);

        // Ajouter le fond de carte
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(searchMap);
    }

    // Afficher un message sur la carte
    const errorMessage = L.control({ position: 'bottomleft' });
    errorMessage.onAdd = function () {
        const div = L.DomUtil.create('div', 'location-error-message');
        div.innerHTML = `
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Impossible d'obtenir votre localisation. Vous pouvez cliquer sur la carte pour définir manuellement votre position.
            </div>
        `;
        return div;
    };
    errorMessage.addTo(searchMap);

    // Disparaître après 10 secondes
    setTimeout(() => {
        const messageElement = document.querySelector('.location-error-message');
        if (messageElement) {
            messageElement.style.opacity = '0';
            setTimeout(() => {
                if (messageElement.parentNode) {
                    messageElement.parentNode.removeChild(messageElement);
                }
            }, 1000);
        }
    }, 10000);
}

// Initialiser la carte quand le document est prêt
document.addEventListener('DOMContentLoaded', function () {
    const desktopMap = document.getElementById('creatorMap');
    const mobileMap = document.getElementById('mobileCreatorMap');

    if (desktopMap) {
        initSearchMap('creatorMap', 'radius');
    }

    if (mobileMap) {
        initSearchMap('mobileCreatorMap');
    }
});

// Exposer les fonctions nécessaires à l'extérieur
window.initSearchMap = initSearchMap;
window.renderCreators = renderCreators;
window.loadCreators = loadCreators;
window.handleLocationError = handleLocationError;