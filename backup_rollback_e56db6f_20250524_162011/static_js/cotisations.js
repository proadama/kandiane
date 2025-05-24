// static/js/cotisations/cotisations.js

/**
 * Fonctions AJAX pour l'application Cotisations
 */
const CotisationsAPI = {
    /**
     * Récupère les barèmes disponibles pour un type de membre
     * @param {number} typeMembreId - ID du type de membre
     * @returns {Promise} - Promesse avec les données des barèmes
     */
    getBaremesByType: function(typeMembreId) {
        return fetch(`/cotisations/api/baremes-par-type/?type_membre=${typeMembreId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Erreur réseau');
                }
                return response.json();
            });
    },
    
    /**
     * Calcule le montant à partir d'un barème
     * @param {number} baremeId - ID du barème
     * @returns {Promise} - Promesse avec le montant calculé
     */
    calculerMontant: function(baremeId) {
        return fetch(`/cotisations/api/calculer-montant/?bareme_id=${baremeId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Erreur réseau');
                }
                return response.json();
            });
    },
    
    /**
     * Vérifie si un barème existe déjà pour un type de membre à une date donnée
     * @param {number} typeMembreId - ID du type de membre
     * @param {string} date - Date de début de validité (format YYYY-MM-DD)
     * @param {number} excludeId - ID du barème à exclure de la vérification
     * @returns {Promise} - Promesse avec les informations de l'existence
     */
    verifierBaremeExistant: function(typeMembreId, date, excludeId = null) {
        let url = `/api/cotisations/verifier-bareme/?type_membre=${typeMembreId}&date=${date}`;
        if (excludeId) {
            url += `&exclude=${excludeId}`;
        }
        
        return fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Erreur réseau');
                }
                return response.json();
            });
    },
    
    /**
     * Crée un paiement via AJAX
     * @param {number} cotisationId - ID de la cotisation
     * @param {Object} data - Données du paiement
     * @returns {Promise} - Promesse avec le résultat
     */
    creerPaiement: function(cotisationId, data) {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        
        return fetch(`/cotisations/${cotisationId}/paiement/ajax/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(data)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Erreur lors de l\'enregistrement du paiement');
            }
            return response.json();
        });
    },
    
    /**
     * Crée un rappel via AJAX
     * @param {number} cotisationId - ID de la cotisation
     * @param {Object} data - Données du rappel
     * @returns {Promise} - Promesse avec le résultat
     */
    creerRappel: function(cotisationId, data) {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        
        return fetch(`/cotisations/${cotisationId}/rappel/ajax/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(data)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Erreur lors de la création du rappel');
            }
            return response.json();
        });
    }
};

// Initialiser les comportements AJAX au chargement
document.addEventListener('DOMContentLoaded', function() {
    // Code d'initialisation si nécessaire
});