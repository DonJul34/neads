/**
 * Module de gestion de la géolocalisation de l'utilisateur
 */
const UserLocation = (() => {
    // Clé pour le stockage local
    const STORAGE_KEY = 'user_map_location';

    // Position par défaut (Paris, France)
    const DEFAULT_LOCATION = {
        latitude: 48.8566,
        longitude: 2.3522
    };

    /**
     * Obtient la localisation de l'utilisateur via le navigateur
     * @param {Function} successCallback - Fonction appelée en cas de succès
     * @param {Function} errorCallback - Fonction appelée en cas d'erreur
     */
    const getUserLocation = (successCallback, errorCallback) => {
        if (!navigator.geolocation) {
            errorCallback(new Error("La géolocalisation n'est pas supportée par ce navigateur."));
            return;
        }

        navigator.geolocation.getCurrentPosition(
            (position) => {
                const coords = {
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude
                };

                // Sauvegarder la position
                saveLocation(coords);

                if (successCallback) successCallback(coords);
            },
            (error) => {
                console.error("Erreur de géolocalisation:", error.message);
                if (errorCallback) errorCallback(error);
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 0
            }
        );
    };

    /**
     * Sauvegarde la position de l'utilisateur
     * @param {Object} coords - Coordonnées {latitude, longitude}
     */
    const saveLocation = (coords) => {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(coords));
        } catch (e) {
            console.warn("Impossible de sauvegarder la position:", e);
        }
    };

    /**
     * Sauvegarde la position manuelle de l'utilisateur
     * @param {Object} coords - Coordonnées {latitude, longitude}
     */
    const saveManualLocation = (coords) => {
        saveLocation(coords);
    };

    /**
     * Récupère la position sauvegardée de l'utilisateur
     * @returns {Object} - Coordonnées {latitude, longitude}
     */
    const getSavedLocation = () => {
        try {
            const saved = localStorage.getItem(STORAGE_KEY);
            return saved ? JSON.parse(saved) : DEFAULT_LOCATION;
        } catch (e) {
            console.warn("Impossible de récupérer la position sauvegardée:", e);
            return DEFAULT_LOCATION;
        }
    };

    /**
     * Calcule la distance entre deux points géographiques en km
     * @param {Object} coords1 - Coordonnées du premier point {latitude, longitude}
     * @param {Object} coords2 - Coordonnées du deuxième point {latitude, longitude}
     * @returns {number} - Distance en kilomètres
     */
    const calculateDistance = (coords1, coords2) => {
        const R = 6371; // Rayon de la Terre en km
        const dLat = deg2rad(coords2.latitude - coords1.latitude);
        const dLon = deg2rad(coords2.longitude - coords1.longitude);

        const a =
            Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(deg2rad(coords1.latitude)) * Math.cos(deg2rad(coords2.latitude)) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2);

        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return R * c;
    };

    /**
     * Convertit les degrés en radians
     * @param {number} deg - Angle en degrés
     * @returns {number} - Angle en radians
     */
    const deg2rad = (deg) => {
        return deg * (Math.PI / 180);
    };

    /**
     * Recherche un lieu via l'API Nominatim
     * @param {string} query - Terme de recherche
     * @param {Function} callback - Fonction de rappel avec les résultats
     */
    const searchLocation = (query, callback) => {
        if (!query || query.length < 3) {
            callback([]);
            return;
        }

        const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=5`;

        fetch(url, {
            headers: {
                'Accept': 'application/json',
                'User-Agent': 'NEADS Map Application'
            }
        })
            .then(response => response.json())
            .then(data => {
                const results = data.map(item => ({
                    name: item.display_name,
                    latitude: parseFloat(item.lat),
                    longitude: parseFloat(item.lon)
                }));
                callback(results);
            })
            .catch(error => {
                console.error('Erreur lors de la recherche de lieu:', error);
                callback([]);
            });
    };

    // API publique
    return {
        getUserLocation,
        getSavedLocation,
        saveManualLocation,
        calculateDistance,
        searchLocation
    };
})();

// Exporter pour une utilisation dans d'autres modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UserLocation;
} 