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

        const url = `/map/ajax/data/?${searchParams.toString()}`;
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
                console.error(`❌ Error loading creators data after ${totalTime}ms:`, error);
                console.error('📊 Error details:', {
                    message: error.message,
                    name: error.name,
                    stack: error.stack
                });

                showLoading(false);
                performance.endTimer('dataLoading');

                // Afficher un message d'erreur visuellement
                const errorMsg = document.createElement('div');
                errorMsg.className = 'alert alert-danger map-error';
                errorMsg.style.position = 'absolute';
                errorMsg.style.bottom = '20px';
                errorMsg.style.right = '20px';
                errorMsg.style.zIndex = '1000';
                errorMsg.innerHTML = `
                    <strong>Erreur de chargement</strong>
                    <p>Impossible de charger les données. Veuillez rafraîchir la page.</p>
                    <small class="text-muted">Erreur: ${error.message}</small>
                `;
                mapElement.parentNode.appendChild(errorMsg);
                console.log('🔄 Error message displayed to user');
                setTimeout(() => {
                    errorMsg.remove();
                    console.log('ℹ️ Error message removed after timeout');
                }, 10000);
            });
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

        creatorsData.forEach((point, index) => {
            const creatorCoords = {
                latitude: point.lat,
                longitude: point.lng
            };

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

            // N'afficher que les créateurs dans le rayon spécifié
            if (distance <= currentRadius) {
                visibleCreatorsCount++;
                if (index < 10 || index % 50 === 0) { // Log every 50th creator to avoid excessive logging
                    console.log(`ℹ️ Adding creator #${index + 1} at distance ${distance.toFixed(2)}km: ${point.name}`);
                }
                addCreatorMarker(point, distance);
                markersAdded++;
                performance.metrics.markerOperations++;
            }
        });

        const calculationTime = performance.endTimer('distanceCalculations');
        const avgCalcTime = calculationTime / distancesCalculated;

        console.log(`✅ Filtered creators: ${visibleCreatorsCount} visible within ${currentRadius}km`);
        console.log('📊 Distance calculations performance:', {
            totalCalculations: distancesCalculated,
            totalTime: `${calculationTime}ms`,
            averagePerCreator: `${avgCalcTime.toFixed(2)}ms`
        });
        console.log('📊 Distance statistics:', {
            min: minDistance !== Infinity ? minDistance.toFixed(2) + 'km' : 'N/A',
            max: maxDistance.toFixed(2) + 'km',
            avg: (distanceSum / creatorsData.length).toFixed(2) + 'km',
            distribution: distanceDistribution
        });
        console.log('📊 Map statistics:', {
            totalCreators: creatorsData.length,
            displayedCreators: visibleCreatorsCount,
            percentage: ((visibleCreatorsCount / creatorsData.length) * 100).toFixed(1) + '%',
            markersAdded: markersAdded
        });

        // Mettre à jour le compteur
        if (creatorCountElement) {
            creatorCountElement.textContent = visibleCreatorsCount;
            console.log('✅ Updated creator count display:', visibleCreatorsCount);
        }

        const totalFilterTime = performance.endTimer('filterCreators');
        console.log(`✅ Creator filtering and marker creation completed in ${totalFilterTime}ms`);
    };

    /**
     * Ajoute un marqueur de créateur à la carte
     * @param {Object} point - Données du créateur
     * @param {number} distance - Distance par rapport à l'utilisateur en km
     */
    const addCreatorMarker = (point, distance) => {
        const marker = L.marker([point.lat, point.lng]);

        // Création du popup
        const distanceText = distance.toFixed(1);
        const popupContent = `
            <div class="creator-popup">
                ${point.thumbnail ? `<img src="${point.thumbnail}" alt="${point.name}">` : ''}
                <h5>${point.name}</h5>
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <div class="star-rating">
                        ${renderStars(point.rating)}
                        <span class="ms-1 text-muted small">(${point.rating})</span>
                    </div>
                    <span class="badge bg-info">${distanceText} km</span>
                </div>
                <a href="${point.url}" class="btn btn-sm btn-primary">Voir le profil</a>
            </div>
        `;

        marker.bindPopup(popupContent);
        markers.addLayer(marker);
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

    // API publique
    console.log('✅ MapManager module loaded and ready');
    return {
        initialize,
        updateUserPosition,
        reloadData: loadCreatorsData,
        getMapStats
    };
})();

// Exporter pour une utilisation dans d'autres modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MapManager;
} 