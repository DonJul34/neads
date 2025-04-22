/**
 * Module de gestion de la carte pour la recherche de créateurs
 * Affiche les créateurs sur une carte et permet de filtrer par proximité
 */
const MapManager = (function () {
    // Variables privées
    let map;
    let userMarker;
    let creatorMarkers = [];
    let userLocation = null;
    let isFullscreen = false;
    let mapContainer;
    let mapElement;
    let fullscreenButton;
    let radiusSelector;
    let resultCountElement;
    let allCreators = [];
    let activeRadius = 0; // 0 signifie tous les créateurs

    /**
     * Initialise la carte des créateurs
     * @param {string} mapContainerId - ID du conteneur de la carte
     * @param {string} mapElementId - ID de l'élément de carte
     * @param {Array} creatorsData - Données des créateurs à afficher
     * @param {Object} options - Options de configuration
     */
    function initialize(mapContainerId, mapElementId, creatorsData, options = {}) {
        // Récupérer les éléments
        mapContainer = document.getElementById(mapContainerId) || document.querySelector('.' + mapContainerId);
        mapElement = document.getElementById(mapElementId);

        if (!mapContainer || !mapElement) {
            console.error("Éléments de carte introuvables", mapContainerId, mapElementId);
            return;
        }

        // Initialiser les options
        const defaultOptions = {
            autoLocate: true,
            enableFiltering: true,
            defaultZoom: 5,
            defaultCenter: [46.603354, 1.888334], // Centre de la France
            maxRadius: 100 // Rayon maximum en km
        };

        const config = { ...defaultOptions, ...options };

        // Stocker les données des créateurs
        allCreators = creatorsData || [];

        // Initialiser la carte Leaflet
        initializeMap(config);

        // Mettre en place les contrôles
        setupControls();

        // Si autoLocate est activé, obtenir la position de l'utilisateur
        if (config.autoLocate) {
            // Vérifier si nous avons déjà une position sauvegardée
            const storedLocation = localStorage.getItem('userLocation');
            if (storedLocation) {
                try {
                    userLocation = JSON.parse(storedLocation);
                    addUserMarker();
                    map.setView([userLocation.lat, userLocation.lng], 10);

                    // Événement personnalisé pour notifier que la localisation utilisateur est disponible
                    const event = new CustomEvent('userLocationReady', {
                        detail: { location: userLocation }
                    });
                    document.dispatchEvent(event);
                } catch (e) {
                    console.error("Erreur lors de la récupération de la position sauvegardée:", e);
                    // En cas d'erreur, on appelle getUserLocation quand même
                    getUserLocation();
                }
            } else {
                // Sinon, obtenir la position de l'utilisateur
                getUserLocation();
            }
        }

        // Ajouter les marqueurs des créateurs
        addCreatorMarkers();

        // Gérer le modal pour la carte mobile
        const mapModal = document.getElementById('mapModal');
        if (mapModal) {
            mapModal.addEventListener('shown.bs.modal', function () {
                // Recalculer la taille de la carte quand le modal s'ouvre
                if (map) {
                    setTimeout(() => {
                        map.invalidateSize();
                    }, 10);
                }
            });
        }
    }

    /**
     * Initialise la carte Leaflet
     * @param {Object} config - Configuration de la carte
     */
    function initializeMap(config) {
        map = L.map(mapElement.id, {
            center: config.defaultCenter,
            zoom: config.defaultZoom,
            zoomControl: false
        });

        // Ajouter la couche de tuiles
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);

        // Ajouter le contrôle de zoom dans le coin supérieur gauche
        L.control.zoom({
            position: 'topleft'
        }).addTo(map);

        // Adapter la carte quand sa taille change (important pour le mode plein écran)
        map.on('fullscreenchange', function () {
            setTimeout(function () {
                map.invalidateSize();
            }, 100);
        });
    }

    /**
     * Configure les contrôles de la carte
     */
    function setupControls() {
        // Bouton plein écran
        fullscreenButton = document.querySelector('.fullscreen-toggle');
        if (fullscreenButton) {
            fullscreenButton.addEventListener('click', toggleFullscreen);
        }

        // Sélecteur de rayon
        const allRadiusSelectors = document.querySelectorAll('.radius-selector');
        if (allRadiusSelectors.length > 0) {
            allRadiusSelectors.forEach(selector => {
                selector.addEventListener('change', function () {
                    activeRadius = parseInt(this.value, 10);
                    filterCreatorsByRadius();

                    // Synchroniser les autres sélecteurs de rayon
                    if (allRadiusSelectors.length > 1) {
                        allRadiusSelectors.forEach(otherSelector => {
                            if (otherSelector !== this) {
                                otherSelector.value = activeRadius;
                            }
                        });
                    }
                });
            });
        }

        // Élément de comptage des résultats
        resultCountElement = document.querySelector('.map-results-count');

        // Boutons de localisation
        const locateButtons = document.querySelectorAll('.locate-me-button');
        if (locateButtons.length > 0) {
            locateButtons.forEach(button => {
                button.addEventListener('click', getUserLocation);
            });
        }
    }

    /**
     * Obtient la localisation de l'utilisateur
     */
    function getUserLocation() {
        const locateButtons = document.querySelectorAll('.locate-me-button');

        // Mettre tous les boutons de localisation en mode chargement
        if (locateButtons.length > 0) {
            locateButtons.forEach(button => {
                button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
                button.disabled = true;
            });
        }

        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(function (position) {
                userLocation = {
                    lat: position.coords.latitude,
                    lng: position.coords.longitude
                };

                // Mettre à jour les distances pour tous les créateurs
                updateCreatorDistances();

                // Ajouter le marqueur de l'utilisateur
                addUserMarker();

                // Centrer et zoomer la carte
                map.setView([userLocation.lat, userLocation.lng], 10);

                // Filtrer les créateurs par rayon si un rayon est sélectionné
                if (activeRadius > 0) {
                    filterCreatorsByRadius();
                }

                // Trier les créateurs par proximité
                sortCreatorsByDistance();

                // Mettre à jour l'interface
                updateUI();

                // Réinitialiser tous les boutons de localisation
                if (locateButtons.length > 0) {
                    locateButtons.forEach(button => {
                        button.innerHTML = '<i class="fas fa-location-arrow"></i>';
                        button.disabled = false;
                    });
                }

                // Événement personnalisé pour notifier que la localisation utilisateur est disponible
                const event = new CustomEvent('userLocationReady', {
                    detail: { location: userLocation }
                });
                document.dispatchEvent(event);
            }, function (error) {
                console.error("Erreur de géolocalisation:", error);

                // Réinitialiser tous les boutons de localisation
                if (locateButtons.length > 0) {
                    locateButtons.forEach(button => {
                        button.innerHTML = '<i class="fas fa-location-arrow"></i>';
                        button.disabled = false;
                    });
                }

                // Afficher un message d'erreur
                alert("Impossible d'obtenir votre position. Veuillez vérifier vos paramètres de localisation.");
            });
        } else {
            console.error("La géolocalisation n'est pas prise en charge par ce navigateur.");

            // Réinitialiser tous les boutons de localisation
            if (locateButtons.length > 0) {
                locateButtons.forEach(button => {
                    button.innerHTML = '<i class="fas fa-location-arrow"></i>';
                    button.disabled = false;
                });
            }

            // Afficher un message d'erreur
            alert("La géolocalisation n'est pas prise en charge par votre navigateur.");
        }
    }

    /**
     * Ajoute le marqueur de l'utilisateur sur la carte
     */
    function addUserMarker() {
        if (!userLocation) return;

        // Sauvegarder la position dans localStorage pour usage ultérieur
        localStorage.setItem('userLocation', JSON.stringify(userLocation));

        // Supprimer le marqueur existant s'il y en a un
        if (userMarker) {
            map.removeLayer(userMarker);
        }

        // Créer un élément HTML personnalisé pour le marqueur
        const markerHtml = `
            <div class="user-marker-inner">
                <i class="fas fa-user"></i>
            </div>
        `;

        const userIcon = L.divIcon({
            html: markerHtml,
            className: 'user-location-marker',
            iconSize: [30, 30],
            iconAnchor: [15, 15]
        });

        // Ajouter le marqueur à la carte
        userMarker = L.marker([userLocation.lat, userLocation.lng], {
            icon: userIcon,
            zIndexOffset: 1000 // S'assurer qu'il est au-dessus des autres marqueurs
        }).addTo(map);

        // Ajouter une popup
        userMarker.bindPopup("Votre position").openPopup();
    }

    /**
     * Ajoute les marqueurs des créateurs sur la carte
     */
    function addCreatorMarkers() {
        // Supprimer les marqueurs existants
        creatorMarkers.forEach(marker => {
            map.removeLayer(marker);
        });
        creatorMarkers = [];

        // Ajouter un marqueur pour chaque créateur
        allCreators.forEach(creator => {
            if (creator.latitude && creator.longitude) {
                const marker = L.marker([creator.latitude, creator.longitude]).addTo(map);

                // Créer le contenu de la popup
                const popupContent = createCreatorPopup(creator);

                // Ajouter la popup au marqueur
                marker.bindPopup(popupContent);

                // Stocker le marqueur avec une référence au créateur
                creatorMarkers.push({
                    marker: marker,
                    creator: creator
                });
            }
        });
    }

    /**
     * Crée le contenu HTML de la popup pour un créateur
     * @param {Object} creator - Données du créateur
     * @returns {string} Contenu HTML de la popup
     */
    function createCreatorPopup(creator) {
        // Générer les étoiles pour la notation
        let starsHtml = '';
        for (let i = 1; i <= 5; i++) {
            if (i <= creator.rating) {
                starsHtml += '<i class="fas fa-star"></i>';
            } else if (i <= creator.rating + 0.5) {
                starsHtml += '<i class="fas fa-star-half-alt"></i>';
            } else {
                starsHtml += '<i class="far fa-star"></i>';
            }
        }

        // Afficher la distance si disponible
        const distanceHtml = creator.distance
            ? `<div class="creator-distance"><i class="fas fa-map-marker-alt"></i> À ${creator.distance.toFixed(1)} km de vous</div>`
            : '';

        // Construire le HTML complet
        return `
            <div class="creator-map-popup">
                <img src="${creator.thumbnail || 'https://via.placeholder.com/300x150?text=Pas+d\'image'}" alt="${creator.full_name}">
                <h5>${creator.full_name} ${creator.verified ? '<i class="fas fa-check-circle"></i>' : ''}</h5>
                <div class="popup-star-rating">${starsHtml} <small>(${creator.total_ratings || 0})</small></div>
                ${distanceHtml}
                <a href="/creators/creator/${creator.id}/" class="btn btn-sm btn-primary w-100">Voir le profil</a>
            </div>
        `;
    }

    /**
     * Met à jour les distances pour tous les créateurs
     */
    function updateCreatorDistances() {
        if (!userLocation) return;

        allCreators.forEach(creator => {
            if (creator.latitude && creator.longitude) {
                creator.distance = calculateDistance(
                    userLocation.lat, userLocation.lng,
                    creator.latitude, creator.longitude
                );
            } else {
                creator.distance = null;
            }
        });
    }

    /**
     * Calcule la distance entre deux points en kilomètres (formule de Haversine)
     * @param {number} lat1 - Latitude du premier point
     * @param {number} lon1 - Longitude du premier point
     * @param {number} lat2 - Latitude du deuxième point
     * @param {number} lon2 - Longitude du deuxième point
     * @returns {number} Distance en kilomètres
     */
    function calculateDistance(lat1, lon1, lat2, lon2) {
        const R = 6371; // Rayon de la Terre en km
        const dLat = deg2rad(lat2 - lat1);
        const dLon = deg2rad(lon2 - lon1);
        const a =
            Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(deg2rad(lat1)) * Math.cos(deg2rad(lat2)) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        const distance = R * c; // Distance en km
        return distance;
    }

    /**
     * Convertit des degrés en radians
     * @param {number} deg - Angle en degrés
     * @returns {number} Angle en radians
     */
    function deg2rad(deg) {
        return deg * (Math.PI / 180);
    }

    /**
     * Filtre les créateurs par rayon de distance
     */
    function filterCreatorsByRadius() {
        if (activeRadius === 0 || !userLocation) {
            // Afficher tous les marqueurs
            creatorMarkers.forEach(markerData => {
                markerData.marker.addTo(map);
            });

            // Mettre à jour tous les compteurs sur l'interface
            updateResultCount(creatorMarkers.length);

            // Événement personnalisé pour notifier que le filtrage a changé
            const event = new CustomEvent('creatorFilterChanged', {
                detail: {
                    creators: allCreators,
                    filtered: false
                }
            });
            document.dispatchEvent(event);

            return;
        }

        // Filtrer les créateurs par distance
        const filteredCreators = allCreators.filter(creator =>
            creator.distance !== null && creator.distance <= activeRadius
        );

        // Mettre à jour les marqueurs visibles
        creatorMarkers.forEach(markerData => {
            const isVisible = filteredCreators.some(c => c.id === markerData.creator.id);

            if (isVisible) {
                markerData.marker.addTo(map);
            } else {
                map.removeLayer(markerData.marker);
            }
        });

        // Mettre à jour tous les compteurs sur l'interface
        updateResultCount(filteredCreators.length);

        // Mettre à jour le formulaire de recherche
        const radiusFilter = document.getElementById('radius');
        if (radiusFilter) {
            radiusFilter.value = activeRadius;
        }

        // Mettre à jour le texte des badges de distance dans la liste des créateurs
        updateDistanceBadges();

        // Événement personnalisé pour notifier que le filtrage a changé
        const event = new CustomEvent('creatorFilterChanged', {
            detail: {
                creators: filteredCreators,
                filtered: true,
                radius: activeRadius
            }
        });
        document.dispatchEvent(event);
    }

    /**
     * Trie les créateurs par distance
     */
    function sortCreatorsByDistance() {
        if (!userLocation) return;

        // Événement personnalisé pour notifier que les créateurs sont triés par distance
        const event = new CustomEvent('creatorsSorted', {
            detail: {
                creators: [...allCreators].sort((a, b) => {
                    // Placer les créateurs sans distance à la fin
                    if (a.distance === null) return 1;
                    if (b.distance === null) return -1;
                    return a.distance - b.distance;
                })
            }
        });
        document.dispatchEvent(event);
    }

    /**
     * Met à jour tous les compteurs de résultats sur l'interface
     * @param {number} count - Nombre de créateurs à afficher
     */
    function updateResultCount(count) {
        // Mettre à jour tous les éléments d'affichage de comptage
        const resultElements = document.querySelectorAll('.map-results-count');
        resultElements.forEach(element => {
            element.textContent = count + ' créateur' + (count > 1 ? 's' : '') + ' sur la carte';
        });
    }

    /**
     * Met à jour les badges de distance dans la liste des créateurs
     */
    function updateDistanceBadges() {
        if (!userLocation) return;

        // Pour chaque créateur, mettre à jour son badge de distance
        document.querySelectorAll('.creator-card').forEach(card => {
            const id = card.dataset.id;
            const creator = allCreators.find(c => c.id === id);

            if (creator && creator.distance !== null) {
                const distanceBadge = card.querySelector('.distance-badge');
                const distanceValue = card.querySelector('.distance-value');

                if (distanceBadge && distanceValue) {
                    distanceBadge.classList.remove('d-none');
                    distanceValue.textContent = creator.distance.toFixed(1);

                    // Masquer les créateurs au-delà du rayon sélectionné si un rayon est défini
                    if (activeRadius > 0 && creator.distance > activeRadius) {
                        card.classList.add('d-none');
                    } else {
                        card.classList.remove('d-none');
                    }
                }
            }
        });
    }

    /**
     * Met à jour les éléments de l'interface
     */
    function updateUI() {
        // Mettre à jour les éléments relatifs à la localisation
        const locateButton = document.querySelector('.locate-me-button');
        if (locateButton && userLocation) {
            locateButton.classList.add('active');
            locateButton.title = "Recentrer sur ma position";
        }

        // Mettre à jour le compteur
        updateResultCount(creatorMarkers.length);
    }

    /**
     * Bascule entre le mode normal et plein écran
     */
    function toggleFullscreen() {
        isFullscreen = !isFullscreen;

        if (mapElement) {
            mapElement.classList.toggle('fullscreen', isFullscreen);
        }

        if (fullscreenButton) {
            fullscreenButton.classList.toggle('active', isFullscreen);
            fullscreenButton.innerHTML = isFullscreen
                ? '<i class="fas fa-compress-alt"></i>'
                : '<i class="fas fa-expand-alt"></i>';
        }

        // Invalider la taille de la carte pour qu'elle se redimensionne correctement
        setTimeout(function () {
            map.invalidateSize();
        }, 100);
    }

    /**
     * API publique
     */
    return {
        initialize,
        getUserLocation,
        filterCreatorsByRadius,
        toggleFullscreen
    };
})(); 