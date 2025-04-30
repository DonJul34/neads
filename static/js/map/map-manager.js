/**
 * Module de gestion de la carte pour afficher les créateurs
 * Dépend de Leaflet et de UserLocation
 */
const MapManager = (() => {
    console.log('🔄 MapManager module initializing...');

    // Performance tracking
    const performance = {
        timers: {},
        metrics: {
            mapInitTime: 0,
            dataLoadTime: 0,
            renderTime: 0,
            apiCalls: 0,
            markerOperations: 0,
            lastRefresh: Date.now()
        },
        startTimer: function (name) {
            this.timers[name] = Date.now();
            console.log(`⏱️ Timer started: ${name}`);
        },
        endTimer: function (name) {
            if (!this.timers[name]) {
                console.warn(`⚠️ Timer ${name} was never started`);
                return 0;
            }
            const duration = Date.now() - this.timers[name];
            console.log(`⏱️ Timer ${name} ended: ${duration}ms`);
            delete this.timers[name];
            return duration;
        },
        logMetrics: function () {
            console.log('📊 Performance Metrics:', {
                mapInitTime: `${this.metrics.mapInitTime}ms`,
                dataLoadTime: `${this.metrics.dataLoadTime}ms`,
                renderTime: `${this.metrics.renderTime}ms`,
                apiCalls: this.metrics.apiCalls,
                markerOperations: this.metrics.markerOperations,
                uptime: `${Math.round((Date.now() - this.metrics.lastRefresh) / 1000)}s`
            });
        }
    };

    // Variables privées
    let map;
    let markers;
    let currentUserMarker;
    let searchCircle;
    let creatorsData = [];
    let currentRadius = 50; // Rayon de recherche en km
    let mapState = {
        zoom: 11,
        center: null,
        bounds: null,
        lastInteraction: Date.now()
    };

    // DOM elements
    let mapElement;
    let radiusSelector;
    let creatorCountElement;
    let loadingElement;

    /**
     * Initialise la carte
     * @param {string} mapElementId - ID de l'élément DOM pour la carte
     * @param {string} radiusSelectorId - ID du sélecteur de rayon
     * @param {string} creatorCountId - ID de l'élément pour afficher le nombre de créateurs
     * @param {string} loadingId - ID de l'élément de chargement
     */
    const initialize = (mapElementId, radiusSelectorId, creatorCountId, loadingId) => {
        performance.startTimer('initialize');
        console.log(`🔄 MapManager.initialize called with: map=${mapElementId}, radius=${radiusSelectorId}, count=${creatorCountId}, loading=${loadingId}`);

        // Récupérer les éléments DOM
        mapElement = document.getElementById(mapElementId);
        radiusSelector = document.getElementById(radiusSelectorId);
        creatorCountElement = document.getElementById(creatorCountId);
        loadingElement = document.getElementById(loadingId);

        if (!mapElement) {
            console.error("❌ Élément de carte introuvable: #" + mapElementId);
            return;
        }

        console.log('✅ Map element found, dimensions:', mapElement.offsetWidth + 'x' + mapElement.offsetHeight);

        // Vérifier si Leaflet est chargé
        if (typeof L === 'undefined') {
            console.error('❌ Leaflet library not loaded! Map initialization aborted.');
            return;
        }

        console.log('✅ Leaflet library detected, creating map instance');

        // Créer la carte avec la position par défaut (sera mise à jour)
        const initialCoords = UserLocation.getSavedLocation();
        console.log('ℹ️ Initial coordinates from saved location:', initialCoords);

        performance.startTimer('mapCreate');
        map = L.map(mapElement).setView([initialCoords.latitude, initialCoords.longitude], 11);
        performance.metrics.mapInitTime = performance.endTimer('mapCreate');
        console.log('✅ Leaflet map instance created');

        // Enregistrer l'état initial de la carte
        mapState.center = [initialCoords.latitude, initialCoords.longitude];
        mapState.zoom = 11;

        // Ajouter le fond de carte
        console.log('🔄 Adding tile layer (OpenStreetMap)');
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);

        // Initialiser les clusters de marqueurs
        console.log('🔄 Initializing marker cluster group');
        markers = L.markerClusterGroup({
            disableClusteringAtZoom: 12,
            maxClusterRadius: 50,
            spiderfyOnMaxZoom: true
        });
        map.addLayer(markers);

        // Ajouter les contrôles de zoom
        L.control.scale().addTo(map);
        console.log('✅ Map controls added');

        // Configurer le clic sur la carte pour changer la position
        map.on('click', (e) => {
            console.log('🔄 Map clicked at:', e.latlng.lat.toFixed(6) + ', ' + e.latlng.lng.toFixed(6));
            mapState.lastInteraction = Date.now();
            updateUserPosition({
                latitude: e.latlng.lat,
                longitude: e.latlng.lng
            });
        });

        // Surveiller les interactions avec la carte
        map.on('zoomend', () => {
            mapState.zoom = map.getZoom();
            mapState.lastInteraction = Date.now();
            console.log(`🔄 Map zoom changed to: ${mapState.zoom}`);
        });

        map.on('moveend', () => {
            const center = map.getCenter();
            mapState.center = [center.lat, center.lng];
            mapState.bounds = map.getBounds();
            mapState.lastInteraction = Date.now();
            console.log(`🔄 Map moved to center: ${mapState.center[0].toFixed(6)}, ${mapState.center[1].toFixed(6)}`);
        });

        // Configurer le changement de rayon
        if (radiusSelector) {
            console.log('✅ Radius selector found, setting up change event');
            radiusSelector.addEventListener('change', (e) => {
                currentRadius = parseInt(e.target.value);
                console.log('🔄 Radius changed to:', currentRadius + 'km');
                performance.startTimer('radiusUpdate');
                updateSearchArea();
                filterCreatorsByDistance();
                performance.endTimer('radiusUpdate');
            });
        } else {
            console.warn('⚠️ Radius selector not found in DOM');
        }

        // Obtenir la position de l'utilisateur et initialiser la carte
        console.log('🔄 Getting user position to initialize map...');
        getUserPositionAndInitialize();

        const initTime = performance.endTimer('initialize');
        console.log(`✅ MapManager initialization complete in ${initTime}ms`);

        // Log initial performance metrics
        performance.logMetrics();
    };

    /**
     * Récupère la position de l'utilisateur et initialise la carte
     */
    const getUserPositionAndInitialize = () => {
        performance.startTimer('getUserPosition');
        console.log('🔄 getUserPositionAndInitialize called');
        showLoading(true);
        UserLocation.getUserLocation(
            (coords) => {
                console.log('✅ User location obtained:', coords);
                const positionTime = performance.endTimer('getUserPosition');
                console.log(`📊 User position obtained in ${positionTime}ms`);

                updateUserPosition(coords);
                console.log('🔄 Initiating data loading after user position update');
                loadCreatorsData();
            },
            (error) => {
                // En cas d'erreur, utiliser la position par défaut
                performance.endTimer('getUserPosition');
                console.warn("⚠️ Error getting user location, using default position. Error:", error);
                const defaultCoords = UserLocation.getSavedLocation();
                console.log('ℹ️ Using default coordinates:', defaultCoords);
                updateUserPosition(defaultCoords);
                console.log('🔄 Initiating data loading with default position');
                loadCreatorsData();
            }
        );
    };

    /**
     * Met à jour la position de l'utilisateur sur la carte
     * @param {Object} coords - Coordonnées (latitude, longitude)
     */
    const updateUserPosition = (coords) => {
        performance.startTimer('updatePosition');
        console.log('🔄 MapManager.updateUserPosition called with:', coords);

        // Valider les coordonnées
        if (!coords || typeof coords.latitude !== 'number' || typeof coords.longitude !== 'number') {
            console.error('❌ Invalid coordinates provided to updateUserPosition:', coords);
            alert('Coordonnées invalides. Veuillez réessayer.');
            performance.endTimer('updatePosition');
            return;
        }

        // Vérifier si les coordonnées sont dans des limites raisonnables
        if (coords.latitude < -90 || coords.latitude > 90 || coords.longitude < -180 || coords.longitude > 180) {
            console.error('❌ Coordinates out of bounds:', coords);
            alert('Coordonnées hors limites. Latitude doit être entre -90 et 90, longitude entre -180 et 180.');
            performance.endTimer('updatePosition');
            return;
        }

        // Sauvegarder la position
        try {
            UserLocation.saveManualLocation(coords);
        } catch (error) {
            console.error('❌ Error saving location:', error);
        }

        // Mettre à jour/créer le marqueur de l'utilisateur
        if (currentUserMarker) {
            console.log('ℹ️ Updating existing user marker position to:', [coords.latitude, coords.longitude]);
            currentUserMarker.setLatLng([coords.latitude, coords.longitude]);
        } else {
            console.log('ℹ️ Creating new user marker at:', [coords.latitude, coords.longitude]);
            const userIcon = L.divIcon({
                className: 'user-location-marker',
                html: '<div class="user-marker-inner"><i class="fas fa-user"></i></div>',
                iconSize: [30, 30],
                iconAnchor: [15, 15]
            });

            try {
                currentUserMarker = L.marker([coords.latitude, coords.longitude], {
                    icon: userIcon,
                    zIndexOffset: 1000
                }).addTo(map);

                currentUserMarker.bindPopup("Votre position<br><small>(cliquez ailleurs pour déplacer)</small>");
                console.log('✅ User marker created and added to map');
            } catch (error) {
                console.error('❌ Error creating user marker:', error);
            }
        }

        // Centrer la carte sur la nouvelle position
        console.log('🔄 Centering map on user position:', [coords.latitude, coords.longitude]);
        try {
            map.setView([coords.latitude, coords.longitude], mapState.zoom || 11);
            console.log('✅ Map centered successfully');
        } catch (error) {
            console.error('❌ Error centering map:', error);
        }

        // Mettre à jour l'état de la carte
        mapState.center = [coords.latitude, coords.longitude];

        // Mettre à jour le cercle de recherche
        updateSearchArea();

        // Filtrer les créateurs par distance
        filterCreatorsByDistance();

        const positionUpdateTime = performance.endTimer('updatePosition');
        console.log(`✅ User position updated successfully in ${positionUpdateTime}ms`);
    };

    /**
     * Met à jour le cercle de recherche autour de la position de l'utilisateur
     */
    const updateSearchArea = () => {
        performance.startTimer('updateSearchArea');
        console.log('🔄 updateSearchArea called, radius:', currentRadius + 'km');
        const coords = UserLocation.getSavedLocation();

        if (searchCircle) {
            console.log('ℹ️ Updating existing search circle');
            searchCircle.setLatLng([coords.latitude, coords.longitude]);
            searchCircle.setRadius(currentRadius * 1000); // Convertir km en mètres
        } else {
            console.log('ℹ️ Creating new search circle');
            searchCircle = L.circle([coords.latitude, coords.longitude], {
                radius: currentRadius * 1000, // Convertir km en mètres
                color: '#3b82f6',
                fillColor: '#3b82f6',
                fillOpacity: 0.1,
                weight: 1
            }).addTo(map);
            console.log('✅ Search circle created and added to map');
        }

        const searchAreaUpdateTime = performance.endTimer('updateSearchArea');
        console.log(`✅ Search area updated in ${searchAreaUpdateTime}ms`);
    };

    /**
     * Charge les données des créateurs depuis l'API
     */
    const loadCreatorsData = () => {
        performance.startTimer('dataLoading');
        console.log('🔄 loadCreatorsData called');
        console.log('📊 Starting data loading process...');
        showLoading(true);

        // Construire l'URL avec les paramètres de recherche
        const searchParams = new URLSearchParams(window.location.search);
        console.log('ℹ️ URL params from current page:', searchParams.toString());

        // Ajouter les coordonnées de l'utilisateur
        const coords = UserLocation.getSavedLocation();
        searchParams.append('lat', coords.latitude);
        searchParams.append('lng', coords.longitude);
        searchParams.append('radius', currentRadius);

        // Mise à jour de l'URL pour utiliser l'endpoint API qui existe réellement
        const url = `/creators/api/creators/map-search/?${searchParams.toString()}`;
        console.log('🔄 Fetching data from:', url);
        console.log('📊 Complete request parameters:', searchParams.toString());

        // Timestamp pour mesurer le temps de chargement
        const startTime = Date.now();
        performance.metrics.apiCalls++;

        fetch(url, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
            .then(response => {
                const responseTime = Date.now() - startTime;
                console.log(`✅ Received response in ${responseTime}ms, status:`, response.status);
                console.log('📤 Response headers:', Object.fromEntries([...response.headers]));

                if (!response.ok) {
                    console.error(`❌ HTTP error: ${response.status} ${response.statusText}`);
                    throw new Error(`Network response was not ok: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                const totalTime = Date.now() - startTime;
                performance.metrics.dataLoadTime = totalTime;
                console.log(`✅ Data parsed successfully in ${totalTime}ms`);
                console.log(`📊 Received ${data.points ? data.points.length : 0} creators`);

                if (data.meta) {
                    console.log('📊 Response metadata:', data.meta);
                }

                if (data.points && data.points.length > 0) {
                    console.log('📊 First creator sample:', {
                        name: data.points[0].name,
                        lat: data.points[0].lat,
                        lng: data.points[0].lng,
                        // Include other non-sensitive fields but omit detailed info
                    });
                    console.log('📊 Data statistics:', {
                        totalCreators: data.points.length,
                        uniqueCities: [...new Set(data.points.filter(p => p.city).map(p => p.city))].length,
                        avgRating: data.points.reduce((sum, p) => sum + (p.rating || 0), 0) / data.points.length,
                        dataSize: JSON.stringify(data).length / 1024 + 'KB'
                    });
                } else {
                    console.log('ℹ️ No creators data in response or empty array');
                }

                creatorsData = data.points || [];
                console.log('🔄 Processing received data and adding to map...');

                performance.startTimer('renderMarkers');
                addCreatorsToMap();
                performance.metrics.renderTime = performance.endTimer('renderMarkers');

                showLoading(false);
                performance.endTimer('dataLoading');

                // Log updated performance metrics
                performance.metrics.lastRefresh = Date.now();
                performance.logMetrics();

                console.log('✅ Data loading complete');
            })
            .catch(error => {
                const totalTime = Date.now() - startTime;
                handleError(error, totalTime);
            });
    };

    /**
     * Gère les erreurs de chargement et affiche un message à l'utilisateur
     * @param {Error} error - L'erreur survenue
     * @param {number} duration - Durée de chargement en ms
     */
    const handleError = (error, duration) => {
        console.error(`❌ Error loading creators data after ${duration}ms:`, error);
        console.log('📊 Error details:', error);

        // Cacher l'indicateur de chargement
        showLoading(false);
        performance.endTimer('dataLoading');

        // Afficher un message d'erreur convivial
        const errorMessage = document.createElement('div');
        errorMessage.className = 'alert alert-danger';
        errorMessage.innerHTML = `
            <h5><i class="fas fa-exclamation-triangle me-2"></i>Erreur lors du chargement des créateurs</h5>
            <p>Impossible de charger les créateurs. Veuillez réessayer ultérieurement.</p>
            <button class="btn btn-sm btn-outline-danger mt-2" onclick="window.location.reload()">
                <i class="fas fa-sync-alt me-1"></i>Réessayer
            </button>
        `;

        // Injecter le message dans la liste des créateurs
        const listContainer = document.getElementById('creators-list-content');
        if (listContainer) {
            listContainer.innerHTML = '';
            listContainer.appendChild(errorMessage);
        }

        console.log('🔄 Error message displayed to user');
    };

    /**
     * Ajoute les marqueurs des créateurs à la carte
     */
    const addCreatorsToMap = () => {
        performance.startTimer('addCreatorsToMap');
        console.log('🔄 addCreatorsToMap called');
        console.log('🗺️ Starting to process creator data for map display');

        // Vider les marqueurs existants
        const markerCountBefore = markers.getLayers().length;
        console.log(`ℹ️ Clearing existing markers (count: ${markerCountBefore})`);
        markers.clearLayers();
        console.log('✅ Existing markers cleared from map');

        // Filtrer par distance et ajouter les marqueurs
        console.log('🔄 Applying distance filter to creators');
        filterCreatorsByDistance();

        const mapRenderTime = performance.endTimer('addCreatorsToMap');
        console.log(`✅ Creators added to map in ${mapRenderTime}ms`);
    };

    /**
     * Filtre les créateurs par distance et les affiche sur la carte
     */
    const filterCreatorsByDistance = () => {
        performance.startTimer('filterCreators');
        console.log('🔄 filterCreatorsByDistance called');
        console.log(`📊 Filtering ${creatorsData ? creatorsData.length : 0} creators by distance (radius: ${currentRadius}km)`);

        if (!creatorsData || creatorsData.length === 0) {
            console.log('ℹ️ No creator data to filter');
            if (creatorCountElement) {
                creatorCountElement.textContent = 0;
                console.log('✅ Updated creator count display: 0');
            }
            performance.endTimer('filterCreators');
            return;
        }

        const userCoords = UserLocation.getSavedLocation();
        console.log('ℹ️ User coordinates for filtering:', userCoords);

        let visibleCreatorsCount = 0;
        let maxDistance = 0;
        let minDistance = Infinity;
        let distanceSum = 0;
        let distancesCalculated = 0;
        let markersAdded = 0;

        const distanceDistribution = {
            "0-5km": 0,
            "5-10km": 0,
            "10-25km": 0,
            "25-50km": 0,
            "50km+": 0
        };

        performance.startTimer('clearMarkers');
        // Vider les marqueurs existants
        markers.clearLayers();
        performance.endTimer('clearMarkers');

        console.log('🔄 Adding filtered creators to map...');
        performance.startTimer('distanceCalculations');

        // Liste des créateurs visibles après filtrage
        const visibleCreators = [];

        creatorsData.forEach((point, index) => {
            const creatorCoords = {
                latitude: point.lat || point.latitude,
                longitude: point.lng || point.longitude
            };

            // Passer les créateurs sans coordonnées valides
            if (!creatorCoords.latitude || !creatorCoords.longitude) {
                return;
            }

            const distance = UserLocation.calculateDistance(userCoords, creatorCoords);
            distancesCalculated++;

            // Collecter des statistiques sur les distances
            maxDistance = Math.max(maxDistance, distance);
            if (distance < minDistance) minDistance = distance;
            distanceSum += distance;

            // Catégoriser les distances pour la distribution
            if (distance <= 5) distanceDistribution["0-5km"]++;
            else if (distance <= 10) distanceDistribution["5-10km"]++;
            else if (distance <= 25) distanceDistribution["10-25km"]++;
            else if (distance <= 50) distanceDistribution["25-50km"]++;
            else distanceDistribution["50km+"]++;

            // Filtrer en fonction du rayon de recherche
            if (distance <= currentRadius) {
                // Ajouter la distance au point pour l'affichage
                point.distance = distance.toFixed(1);

                // Ajouter à la liste des créateurs visibles
                visibleCreators.push(point);

                // Ajouter le marqueur sur la carte
                if (index < 100 || distance < 50) {
                    if (distance < 1) {
                        console.log(`ℹ️ Adding nearby creator #${index + 1} at distance ${distance.toFixed(2)}km: ${point.name}`);
                    }
                    addCreatorMarker(point);
                    markersAdded++;
                    performance.metrics.markerOperations++;
                }
                visibleCreatorsCount++;
            }
        });

        performance.endTimer('distanceCalculations');

        const avgDistance = distancesCalculated ? (distanceSum / distancesCalculated).toFixed(1) : 0;

        // Mettre à jour les compteurs et statistiques
        if (creatorCountElement) {
            creatorCountElement.textContent = visibleCreatorsCount;
            console.log(`✅ Updated creator count display: ${visibleCreatorsCount}`);
        }

        // Journaliser des statistiques détaillées
        console.log('🔄 Creator distance statistics:', {
            total: creatorsData.length,
            filtered: visibleCreatorsCount,
            maxDistance: maxDistance.toFixed(1) + 'km',
            minDistance: (minDistance === Infinity ? 'N/A' : minDistance.toFixed(1) + 'km'),
            avgDistance: avgDistance + 'km',
            distribution: distanceDistribution,
            markersAdded: markersAdded
        });

        const filterTime = performance.endTimer('filterCreators');
        console.log(`✅ Creator filtering and marker creation completed in ${filterTime}ms`);

        return visibleCreators;
    };

    /**
     * Ajoute un marqueur pour un créateur sur la carte
     * @param {Object} creator - Données du créateur
     */
    const addCreatorMarker = (creator) => {
        performance.metrics.markerOperations++;

        try {
            // Récupérer les coordonnées
            const lat = creator.latitude || creator.lat;
            const lng = creator.longitude || creator.lng;

            if (!lat || !lng) {
                console.warn('Missing coordinates for creator:', creator.id);
                return;
            }

            // Vérifier si des coordonnées valides (nombres)
            if (isNaN(parseFloat(lat)) || isNaN(parseFloat(lng))) {
                console.warn('Invalid coordinates for creator:', creator.id, lat, lng);
                return;
            }

            // Créer le contenu de la popup
            const popupContent = `
                <div class="creator-popup">
                    ${creator.thumbnail ? `<img src="${creator.thumbnail}" alt="${creator.name}" class="img-fluid mb-2">` : ''}
                    <h5>${creator.name}</h5>
                    <div class="d-flex justify-content-between mb-2">
                        <div class="star-rating">
                            ${creator.rating ? '⭐ ' + creator.rating.toFixed(1) : 'Non noté'}
                        </div>
                        <div class="distance">
                            ${creator.distance ? creator.distance.toFixed(1) + ' km' : ''}
                        </div>
                    </div>
                    <div class="mb-2">
                        ${creator.domains && creator.domains.length > 0 ?
                    creator.domains.slice(0, 3).map(domain =>
                        `<span class="badge bg-secondary me-1">${domain.name}</span>`
                    ).join('') : ''
                }
                    </div>
                    <a href="${creator.url}" class="btn btn-primary btn-sm">Voir le profil</a>
                </div>
            `;

            // Ajouter un petit décalage aux coordonnées si plusieurs créateurs au même endroit
            // Cela permet d'éviter que les marqueurs se superposent
            const jitter = (Math.random() - 0.5) * 0.001; // Petit décalage aléatoire (environ 10-50m)

            // Créer le marqueur avec une icône personnalisée
            const marker = L.marker([parseFloat(lat) + jitter, parseFloat(lng) + jitter], {
                title: creator.name,
                alt: creator.name,
                riseOnHover: true
            });

            // Stocker l'ID du créateur dans le marqueur pour pouvoir le retrouver
            marker.creatorId = creator.id;

            // Ajouter la popup
            marker.bindPopup(popupContent);

            // Ajouter au cluster
            markers.addLayer(marker);

            return marker;
        } catch (e) {
            console.error('Error adding marker:', e, creator);
            return null;
        }
    };

    /**
     * Génère le HTML pour afficher les étoiles
     * @param {number} rating - Note (de 0 à 5)
     * @returns {string} HTML des étoiles
     */
    const renderStars = (rating) => {
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
    };

    /**
     * Affiche ou masque l'indicateur de chargement
     * @param {boolean} show - True pour afficher, false pour masquer
     */
    const showLoading = (show) => {
        console.log(`🔄 showLoading(${show})`);
        if (loadingElement) {
            loadingElement.style.display = show ? 'block' : 'none';
            console.log(`✅ Loading indicator ${show ? 'shown' : 'hidden'}`);
        } else {
            console.warn('⚠️ Loading element not found');
        }
    };

    /**
     * Obtient des statistiques sur l'état actuel de la carte
     * @returns {Object} État et métriques de la carte
     */
    const getMapStats = () => {
        const stats = {
            currentState: {
                zoom: mapState.zoom,
                center: mapState.center ? [mapState.center[0].toFixed(6), mapState.center[1].toFixed(6)] : null,
                radius: currentRadius + 'km',
                creatorsDisplayed: markers.getLayers().length,
                creatorsTotal: creatorsData.length,
                lastInteraction: new Date(mapState.lastInteraction).toISOString()
            },
            performance: {
                mapInitTime: performance.metrics.mapInitTime + 'ms',
                dataLoadTime: performance.metrics.dataLoadTime + 'ms',
                renderTime: performance.metrics.renderTime + 'ms',
                apiCalls: performance.metrics.apiCalls,
                markerOperations: performance.metrics.markerOperations,
                uptime: Math.round((Date.now() - performance.metrics.lastRefresh) / 1000) + 's'
            }
        };

        console.log('📊 Map statistics:', stats);
        return stats;
    };

    /**
     * Rend les créateurs sur la carte à partir de la structure de données fournie par l'API
     * @param {Array} creatorsList - Liste des créateurs avec données latitude/longitude
     */
    const renderCreators = (creatorsList) => {
        console.log('🔄 MapManager.renderCreators called with', creatorsList.length, 'creators');

        // Stocker les données des créateurs
        creatorsData = creatorsList;

        // Vider les marqueurs existants
        markers.clearLayers();

        // Mettre à jour le compteur de résultats
        if (creatorCountElement) {
            creatorCountElement.textContent = creatorsList.length;
        }

        // Remplir la liste des créateurs
        const creatorsListContainer = document.getElementById('creators-list-content');
        if (creatorsListContainer) {
            creatorsListContainer.innerHTML = '';

            if (creatorsList.length === 0) {
                creatorsListContainer.innerHTML = `
                    <div class="alert alert-info">
                        <i class="fas fa-info-circle me-2"></i> Aucun créateur trouvé avec ces critères.
                    </div>
                `;
            } else {
                // Trier les créateurs par distance
                const sortedCreators = [...creatorsList].sort((a, b) => a.distance - b.distance);

                // Ajouter chaque créateur à la liste
                sortedCreators.forEach(creator => {
                    try {
                        // Vérifier les données de position
                        const lat = creator.latitude;
                        const lng = creator.longitude;

                        if (!lat || !lng) {
                            return;
                        }

                        // Créer le marqueur sur la carte
                        addCreatorMarker(creator);

                        // Ajouter à la liste des créateurs
                        const creatorItem = document.createElement('div');
                        creatorItem.className = 'creator-item';
                        creatorItem.innerHTML = `
                            <div class="d-flex align-items-center">
                                ${creator.thumbnail ?
                                `<img src="${creator.thumbnail}" alt="${creator.name}" class="rounded-circle me-2" style="width: 40px; height: 40px; object-fit: cover;">` :
                                `<div class="rounded-circle me-2 bg-secondary d-flex align-items-center justify-content-center" style="width: 40px; height: 40px; color: white;">
                                        <i class="fas fa-user"></i>
                                    </div>`
                            }
                                <div>
                                    <h6 class="mb-0">${creator.name}</h6>
                                    <div class="small text-muted">
                                        ${creator.distance.toFixed(1)}km
                                        ${creator.rating ? `<span class="ms-2">⭐ ${creator.rating.toFixed(1)}</span>` : ''}
                                    </div>
                                </div>
                            </div>
                            <div class="mt-1 small">
                                ${creator.domains && creator.domains.length > 0 ?
                                creator.domains.slice(0, 2).map(d =>
                                    `<span class="badge bg-secondary me-1">${d.name}</span>`
                                ).join('') : ''
                            }
                            </div>
                            <a href="${creator.url}" class="stretched-link"></a>
                        `;

                        creatorItem.addEventListener('click', () => {
                            // Centrer la carte sur ce créateur
                            map.setView([lat, lng], 14);
                            // Ouvrir la popup
                            const marker = findCreatorMarker(creator.id);
                            if (marker) {
                                marker.openPopup();
                            }
                        });

                        creatorsListContainer.appendChild(creatorItem);
                    } catch (e) {
                        console.error('Error adding creator to list:', e, creator);
                    }
                });
            }
        }

        performance.metrics.totalCreators = creatorsList.length;
        console.log(`✅ Creator filtering and marker creation completed in ${performance.timers.filterCreators}ms`);
    };

    /**
     * Trouve le marqueur d'un créateur par son ID
     * @param {number} creatorId - ID du créateur
     * @returns {L.Marker|null} Le marqueur ou null si non trouvé
     */
    const findCreatorMarker = (creatorId) => {
        let foundMarker = null;
        markers.eachLayer(marker => {
            if (marker.creatorId === creatorId) {
                foundMarker = marker;
            }
        });
        return foundMarker;
    };

    // Exposer l'API publique
    return {
        initialize,
        updateUserPosition,
        loadCreatorsData,
        updateSearchArea,
        renderCreators,
        findCreatorMarker,
        addCreatorMarker,
        getMapStats
    };
})();

// Exporter pour une utilisation dans d'autres modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MapManager;
} 