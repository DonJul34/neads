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

    // Coordonnées géographiques des principales villes françaises
    // Permet d'éviter les appels API pour les recherches courantes
    const COMMON_CITIES = {
        'paris': { latitude: 48.8566, longitude: 2.3522 },
        'marseille': { latitude: 43.2965, longitude: 5.3698 },
        'lyon': { latitude: 45.7578, longitude: 4.8320 },
        'toulouse': { latitude: 43.6047, longitude: 1.4442 },
        'nice': { latitude: 43.7102, longitude: 7.2620 },
        'nantes': { latitude: 47.2184, longitude: -1.5536 },
        'montpellier': { latitude: 43.6112, longitude: 3.8767 },
        'strasbourg': { latitude: 48.5734, longitude: 7.7521 },
        'bordeaux': { latitude: 44.8378, longitude: -0.5792 },
        'lille': { latitude: 50.6292, longitude: 3.0573 },
        'rennes': { latitude: 48.1173, longitude: -1.6778 },
        'grenoble': { latitude: 45.1885, longitude: 5.7245 },
        'angers': { latitude: 47.4784, longitude: -0.5630 },
        'dijon': { latitude: 47.3220, longitude: 5.0415 },
        'nîmes': { latitude: 43.8367, longitude: 4.3601 },
        'aix-en-provence': { latitude: 43.5298, longitude: 5.4474 }
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

        if (!query || query.length < 2) {
            console.log('ℹ️ Query too short, returning empty results');
            callback([]);
            return;
        }

        // Vérifier si c'est une ville courante (insensible à la casse)
        const normalizedQuery = query.trim().toLowerCase();
        const commonCity = Object.keys(COMMON_CITIES).find(city => {
            return normalizedQuery === city ||
                normalizedQuery.includes(city) ||
                city.includes(normalizedQuery);
        });

        if (commonCity) {
            console.log('✅ Ville trouvée dans le dictionnaire des villes courantes:', commonCity);
            const coords = COMMON_CITIES[commonCity];

            // Construire un résultat similaire à celui de l'API Nominatim
            const result = {
                lat: coords.latitude.toString(),
                lon: coords.longitude.toString(),
                display_name: commonCity.charAt(0).toUpperCase() + commonCity.slice(1),
                name: commonCity.charAt(0).toUpperCase() + commonCity.slice(1),
                type: 'city',
                importance: 0.9,
                is_common_city: true
            };

            callback([result]);
            return;
        }

        // URL de l'API Nominatim avec paramètres optimisés pour la recherche de villes
        const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=5&addressdetails=1&accept-language=fr&featuretype=city,town,village`;

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
                    throw new Error('Invalid response format from Nominatim API');
                }

                // Transformer les résultats dans un format plus simple
                const results = data.map(item => {
                    let name = item.display_name;

                    // Simplifier le nom affiché
                    if (item.address) {
                        if (item.address.city || item.address.town || item.address.village) {
                            name = item.address.city || item.address.town || item.address.village;

                            // Ajouter le pays pour clarifier
                            if (item.address.country) {
                                name += `, ${item.address.country}`;
                            }
                        }
                    }

                    return {
                        name: name,
                        lat: parseFloat(item.lat),
                        lon: parseFloat(item.lon),
                        type: item.type,
                        importance: item.importance
                    };
                });

                console.log('✅ Search results processed:', results);
                callback(results);
            })
            .catch(error => {
                console.error('❌ Error fetching location data:', error);

                // Appeler le callback avec un tableau vide en cas d'erreur
                callback([]);

                // Afficher un message d'erreur à l'utilisateur si nécessaire
                console.error('📊 Error details:', {
                    name: error.name,
                    message: error.message,
                    url: url
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

    // Exposer les fonctions publiques
    return {
        getUserLocation,
        saveManualLocation,
        getSavedLocation,
        calculateDistance,
        formatDistance,
        searchLocation,
        fallbackLocalSearch,
        COMMON_CITIES
    };
})();

// Exporter pour une utilisation dans d'autres modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UserLocation;
} 