/**
 * Module pour gérer la localisation de l'utilisateur
 */
const UserLocation = (() => {
    console.log('🔄 UserLocation module initializing...');

    // Constantes
    const STORAGE_KEY = 'user_map_location';
    const DEFAULT_LOCATION = {
        latitude: 48.8566, // Paris
        longitude: 2.3522
    };

    console.log('📊 Default location set to:', DEFAULT_LOCATION);

    /**
     * Demande la position de l'utilisateur via l'API Geolocation
     * @param {Function} successCallback - Fonction appelée en cas de succès
     * @param {Function} errorCallback - Fonction appelée en cas d'erreur
     */
    const getUserLocation = (successCallback, errorCallback) => {
        console.log('🔄 getUserLocation called, checking geolocation API...');
        const startTime = Date.now();

        if (!navigator.geolocation) {
            console.error('❌ Geolocation API not supported in this browser');
            return errorCallback(new Error("Votre navigateur ne supporte pas la géolocalisation"));
        }

        console.log('🔄 Requesting user position from browser with options:');
        console.log('- High accuracy enabled');
        console.log('- Timeout: 10 seconds');
        console.log('- Maximum age: 10 minutes');

        navigator.geolocation.getCurrentPosition(
            (position) => {
                const requestTime = Date.now() - startTime;
                console.log(`✅ Geolocation successful in ${requestTime}ms:`);
                console.log(`📊 Location details:`, {
                    latitude: position.coords.latitude.toFixed(6),
                    longitude: position.coords.longitude.toFixed(6),
                    accuracy: position.coords.accuracy ? `${position.coords.accuracy.toFixed(1)}m` : 'unknown',
                    altitude: position.coords.altitude ? `${position.coords.altitude.toFixed(1)}m` : 'unknown',
                    heading: position.coords.heading || 'unknown',
                    speed: position.coords.speed ? `${position.coords.speed.toFixed(1)}m/s` : 'unknown',
                    timestamp: new Date(position.timestamp).toISOString()
                });

                const coords = {
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude
                };

                // Sauvegarder la position pour une utilisation future
                saveManualLocation(coords);

                // Appeler le callback
                successCallback(coords);
            },
            (error) => {
                console.error('❌ Geolocation error occurred after', (Date.now() - startTime), 'ms');
                console.error('📊 Error details:', {
                    code: error.code,
                    message: error.message,
                    PERMISSION_DENIED: error.code === 1 ? 'true' : 'false',
                    POSITION_UNAVAILABLE: error.code === 2 ? 'true' : 'false',
                    TIMEOUT: error.code === 3 ? 'true' : 'false'
                });
                errorCallback(error);
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 10 * 60 * 1000 // 10 minutes
            }
        );
    };

    /**
     * Sauvegarde la position de l'utilisateur dans le stockage local
     * @param {Object} coords - Coordonnées (latitude, longitude)
     */
    const saveManualLocation = (coords) => {
        console.log('🔄 saveManualLocation called with:', coords);
        if (!coords || typeof coords.latitude !== 'number' || typeof coords.longitude !== 'number') {
            console.error('❌ Invalid coordinates provided to saveManualLocation:', coords);
            return;
        }

        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(coords));
            console.log('✅ Location saved to localStorage:', STORAGE_KEY);
        } catch (e) {
            console.error('❌ Failed to save location to localStorage:', e);
            console.error('📊 Error details:', {
                name: e.name,
                message: e.message,
                storageAvailable: typeof localStorage !== 'undefined',
                storageLength: localStorage ? localStorage.length : 'N/A'
            });
        }
    };

    /**
     * Récupère la position sauvegardée de l'utilisateur
     * @returns {Object} Coordonnées (latitude, longitude)
     */
    const getSavedLocation = () => {
        console.log('🔄 getSavedLocation called, looking for key:', STORAGE_KEY);
        try {
            const saved = localStorage.getItem(STORAGE_KEY);
            if (saved) {
                const parsed = JSON.parse(saved);
                console.log('✅ Retrieved saved location:', parsed);
                return parsed;
            }
            console.log('ℹ️ No location found in localStorage for key:', STORAGE_KEY);
        } catch (e) {
            console.error('❌ Error reading location from localStorage:', e);
            console.error('📊 Error details:', {
                name: e.name,
                message: e.message
            });
        }

        console.log('ℹ️ No saved location found, using default location (Paris)');
        return DEFAULT_LOCATION;
    };

    /**
     * Calcule la distance en kilomètres entre deux points
     * Utilise la formule de Haversine
     * @param {Object} point1 - Premier point {latitude, longitude}
     * @param {Object} point2 - Second point {latitude, longitude}
     * @returns {number} Distance en kilomètres
     */
    const calculateDistance = (point1, point2) => {
        const startTime = performance.now();
        console.log('🔄 calculateDistance called with points:');
        console.log('- Point 1:', point1);
        console.log('- Point 2:', point2);

        if (!point1 || !point2 ||
            typeof point1.latitude !== 'number' ||
            typeof point1.longitude !== 'number' ||
            typeof point2.latitude !== 'number' ||
            typeof point2.longitude !== 'number') {
            console.error('❌ Invalid coordinates provided to calculateDistance');
            return null;
        }

        const R = 6371; // Rayon de la Terre en km
        const dLat = toRad(point2.latitude - point1.latitude);
        const dLon = toRad(point2.longitude - point1.longitude);

        const a =
            Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(toRad(point1.latitude)) * Math.cos(toRad(point2.latitude)) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2);

        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        const distance = R * c;

        const endTime = performance.now();
        console.log(`✅ Distance calculated: ${distance.toFixed(2)} km (took ${(endTime - startTime).toFixed(2)}ms)`);

        return distance;
    };

    /**
     * Convertit des degrés en radians
     * @param {number} deg - Angle en degrés
     * @returns {number} Angle en radians
     */
    const toRad = (deg) => {
        return deg * (Math.PI / 180);
    };

    /**
     * Formatage d'une distance en texte lisible
     * @param {number} distance - Distance en kilomètres
     * @returns {string} Distance formatée
     */
    const formatDistance = (distance) => {
        if (typeof distance !== 'number') {
            console.error('❌ Invalid distance value provided to formatDistance:', distance);
            return 'Distance inconnue';
        }

        console.log('🔄 Formatting distance:', distance);

        if (distance < 1) {
            const meters = Math.round(distance * 1000);
            console.log(`✅ Formatted as: ${meters} m`);
            return `${meters} m`;
        } else if (distance < 10) {
            const km = distance.toFixed(1);
            console.log(`✅ Formatted as: ${km} km`);
            return `${km} km`;
        } else {
            const km = Math.round(distance);
            console.log(`✅ Formatted as: ${km} km`);
            return `${km} km`;
        }
    };

    /**
     * Recherche un lieu via l'API Nominatim (OpenStreetMap)
     * @param {string} query - Terme de recherche
     * @param {Function} callback - Fonction de rappel avec les résultats
     */
    const searchLocation = (query, callback) => {
        console.log('🔄 searchLocation called with query:', query);

        if (!query || query.length < 3) {
            console.log('ℹ️ Query too short, returning empty results');
            callback([]);
            return;
        }

        // URL de l'API Nominatim avec paramètres
        const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=5&addressdetails=1&accept-language=fr`;

        console.log('🔄 Fetching data from Nominatim API:', url);
        const startTime = Date.now();

        // Utiliser une requête CORS-safe
        fetch(url, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'User-Agent': 'NEADS Map Application (contact@neads.com)'
            },
            mode: 'cors'
        })
            .then(response => {
                const responseTime = Date.now() - startTime;
                console.log(`✅ Received Nominatim response in ${responseTime}ms, status:`, response.status);

                if (!response.ok) {
                    throw new Error(`HTTP error: ${response.status} ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                const totalTime = Date.now() - startTime;
                console.log(`✅ Nominatim data parsed in ${totalTime}ms`);
                console.log(`📊 Found ${data.length} locations:`, data);

                if (!Array.isArray(data)) {
                    console.error('❌ Invalid response format: expected array but got', typeof data);
                    callback([]);
                    return;
                }

                // Transformer les résultats dans un format plus simple
                const results = data.map(item => {
                    // S'assurer que les coordonnées sont des nombres
                    const lat = parseFloat(item.lat);
                    const lon = parseFloat(item.lon);

                    if (isNaN(lat) || isNaN(lon)) {
                        console.error('❌ Invalid coordinates in result:', item);
                        return null;
                    }

                    // Construire un nom plus convivial avec les détails d'adresse si disponibles
                    let displayName = item.display_name;

                    // Si address details sont disponibles, construire un nom plus court et plus lisible
                    if (item.address) {
                        const parts = [];

                        // Ville
                        if (item.address.city || item.address.town || item.address.village) {
                            parts.push(item.address.city || item.address.town || item.address.village);
                        }

                        // Quartier/Région
                        if (item.address.suburb || item.address.county || item.address.state_district) {
                            parts.push(item.address.suburb || item.address.county || item.address.state_district);
                        }

                        // Pays
                        if (item.address.country) {
                            parts.push(item.address.country);
                        }

                        if (parts.length > 0) {
                            displayName = parts.join(', ');
                        }
                    }

                    return {
                        name: displayName,
                        latitude: lat,
                        longitude: lon,
                        type: item.type,
                        importance: item.importance
                    };
                }).filter(result => result !== null);

                console.log('📊 Transformed results:', results);
                callback(results);
            })
            .catch(error => {
                const totalTime = Date.now() - startTime;
                console.error(`❌ Error searching location after ${totalTime}ms:`, error);
                console.error('📊 Error details:', {
                    message: error.message,
                    name: error.name,
                    stack: error.stack
                });

                // Tenter une approche alternative avec un proxy CORS
                console.log('🔄 Attempting alternative approach with CORS proxy...');
                const proxyUrl = `https://cors-anywhere.herokuapp.com/https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=5`;

                fetch(proxyUrl, {
                    method: 'GET',
                    headers: {
                        'Accept': 'application/json',
                        'Origin': window.location.origin
                    }
                })
                    .then(response => {
                        if (!response.ok) {
                            throw new Error(`Proxy HTTP error: ${response.status}`);
                        }
                        return response.json();
                    })
                    .then(data => {
                        console.log('✅ Data received via proxy:', data);

                        const results = data.map(item => ({
                            name: item.display_name,
                            latitude: parseFloat(item.lat),
                            longitude: parseFloat(item.lon)
                        }));

                        callback(results);
                    })
                    .catch(proxyError => {
                        console.error('❌ Proxy approach also failed:', proxyError);
                        // Fallback à la recherche locale
                        fallbackLocalSearch(query, callback);
                    });
            });
    };

    /**
     * Recherche locale de secours avec quelques villes majeures
     * Utilisée si l'API Nominatim ne répond pas
     */
    const fallbackLocalSearch = (query, callback) => {
        console.log('🔄 Using fallback local search for query:', query);

        // Quelques grandes villes françaises avec leurs coordonnées
        const cities = [
            { name: 'Paris, France', latitude: 48.8566, longitude: 2.3522 },
            { name: 'Lyon, France', latitude: 45.7640, longitude: 4.8357 },
            { name: 'Marseille, France', latitude: 43.2965, longitude: 5.3698 },
            { name: 'Bordeaux, France', latitude: 44.8378, longitude: -0.5792 },
            { name: 'Lille, France', latitude: 50.6292, longitude: 3.0573 },
            { name: 'Toulouse, France', latitude: 43.6047, longitude: 1.4442 },
            { name: 'Nice, France', latitude: 43.7102, longitude: 7.2620 },
            { name: 'Nantes, France', latitude: 47.2184, longitude: -1.5536 },
            { name: 'Strasbourg, France', latitude: 48.5734, longitude: 7.7521 },
            { name: 'Montpellier, France', latitude: 43.6110, longitude: 3.8767 },
            { name: 'London, United Kingdom', latitude: 51.5074, longitude: -0.1278 },
            { name: 'Berlin, Germany', latitude: 52.5200, longitude: 13.4050 },
            { name: 'Madrid, Spain', latitude: 40.4168, longitude: -3.7038 },
            { name: 'Rome, Italy', latitude: 41.9028, longitude: 12.4964 },
            { name: 'Amsterdam, Netherlands', latitude: 52.3676, longitude: 4.9041 },
            { name: 'Brussels, Belgium', latitude: 50.8476, longitude: 4.3572 },
            { name: 'Zurich, Switzerland', latitude: 47.3769, longitude: 8.5417 },
            { name: 'Barcelona, Spain', latitude: 41.3851, longitude: 2.1734 },
            { name: 'Vienna, Austria', latitude: 48.2082, longitude: 16.3738 },
            { name: 'Prague, Czech Republic', latitude: 50.0755, longitude: 14.4378 }
        ];

        // Recherche simple (contient)
        const lowercaseQuery = query.toLowerCase();
        const results = cities.filter(city =>
            city.name.toLowerCase().includes(lowercaseQuery)
        );

        console.log('📊 Local search results:', results);
        callback(results);
    };

    // API publique
    console.log('✅ UserLocation module loaded and ready');
    return {
        getUserLocation,
        getSavedLocation,
        saveManualLocation,
        calculateDistance,
        formatDistance,
        searchLocation
    };
})();

// Exporter pour une utilisation dans d'autres modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UserLocation;
} 