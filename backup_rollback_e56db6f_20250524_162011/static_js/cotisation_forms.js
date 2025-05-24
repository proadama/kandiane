/**
 * Script pour gérer les interactions dynamiques du formulaire de cotisation
 * S'occupe spécifiquement du filtrage des barèmes par type de membre
 */
document.addEventListener('DOMContentLoaded', function() {
    // Éléments du formulaire
    const typeMembreSelect = document.getElementById('id_type_membre');
    const baremeSelect = document.getElementById('id_bareme');
    const montantInput = document.getElementById('id_montant');
    const utiliserBaremeCheckbox = document.getElementById('id_utiliser_bareme');
    const periodeDebutInput = document.getElementById('id_periode_debut');
    const periodeFinInput = document.getElementById('id_periode_fin');
    const calculProrataInfo = document.getElementById('calcul-prorata-info');
    const calculProrataTexte = document.getElementById('calcul-prorata-texte');
    const peridiciteInfo = document.getElementById('periodicite-info');
    
    // Référence pour les barèmes
    let baremesDisponibles = [];
    
    // Initialiser les événements
    if (typeMembreSelect && baremeSelect) {
        console.log("Initialisation du filtrage des barèmes par type de membre");
        
        // Écouter les changements sur le sélecteur de type de membre
        typeMembreSelect.addEventListener('change', function() {
            console.log("Type de membre changé :", this.value);
            chargerBaremesParType(this.value);
        });
        
        // Charger les barèmes si un type de membre est déjà sélectionné
        if (typeMembreSelect.value) {
            console.log("Type de membre déjà sélectionné :", typeMembreSelect.value);
            chargerBaremesParType(typeMembreSelect.value);
        }
    } else {
        console.warn("Éléments du formulaire non trouvés");
    }
    
    /**
     * Charge les barèmes disponibles pour un type de membre spécifique
     * @param {string|number} typeMembreId - ID du type de membre
     */
    function chargerBaremesParType(typeMembreId) {
        if (!typeMembreId) {
            console.log("Aucun type de membre sélectionné");
            // Réinitialiser le barème si aucun type n'est sélectionné
            reinitialiserBareme();
            return;
        }
        
        console.log("Chargement des barèmes pour le type", typeMembreId);
        
        // Afficher l'indicateur de chargement
        baremeSelect.disabled = true;
        const optionChargement = document.createElement('option');
        optionChargement.textContent = 'Chargement...';
        baremeSelect.innerHTML = '';
        baremeSelect.appendChild(optionChargement);
        
        // Récupérer le token CSRF
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

        // AJOUTEZ LE LOG ICI, juste avant l'appel fetch
        console.log("URL API:", '/cotisations/api/baremes-par-type/?type_membre=' + typeMembreId);
        
        // Faire la requête AJAX
        fetch(`/cotisations/api/baremes-par-type/?type_membre=${typeMembreId}`, {
            method: 'GET',
            headers: {
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json'
            },
            credentials: 'same-origin'
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Erreur réseau: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log("Données reçues:", data);
                
                if (data.success) {
                    baremesDisponibles = data.baremes;
                    mettreAJourSelectBareme();
                } else {
                    console.error('Erreur lors du chargement des barèmes:', data.message);
                    afficherErreur(baremeSelect, 'Erreur lors du chargement des barèmes');
                }
            })
            .catch(error => {
                console.error('Erreur lors de la requête:', error);
                afficherErreur(baremeSelect, 'Erreur de communication avec le serveur');
            })
            .finally(() => {
                baremeSelect.disabled = false;
            });
    }
    
    /**
     * Met à jour le sélecteur de barèmes avec les données récupérées
     */
    function mettreAJourSelectBareme() {
        // Vider le sélecteur
        baremeSelect.innerHTML = '';
        
        // Ajouter une option vide
        const optionVide = document.createElement('option');
        optionVide.value = '';
        optionVide.textContent = 'Sélectionnez un barème';
        baremeSelect.appendChild(optionVide);
        
        // Ajouter les barèmes disponibles
        if (baremesDisponibles.length > 0) {
            console.log(`${baremesDisponibles.length} barèmes disponibles`);
            
            // Création d'un groupe pour les barèmes actifs
            const groupeActifs = document.createElement('optgroup');
            groupeActifs.label = 'Barèmes actifs';
            
            // Création d'un groupe pour les barèmes inactifs
            const groupeInactifs = document.createElement('optgroup');
            groupeInactifs.label = 'Barèmes inactifs';
            
            let actifsTrouves = false;
            let inactifsTrouves = false;
            
            baremesDisponibles.forEach(bareme => {
                const option = document.createElement('option');
                option.value = bareme.id;
                option.textContent = `${bareme.montant} € (${bareme.periodicite})`;
                option.dataset.montant = bareme.montant;
                option.dataset.periodicite = bareme.periodicite_code || bareme.periodicite;
                option.dataset.dureeJours = bareme.duree_jours || getDureeJoursParPeriodicite(bareme.periodicite_code || bareme.periodicite);
                
                if (bareme.est_actif) {
                    groupeActifs.appendChild(option);
                    actifsTrouves = true;
                } else {
                    groupeInactifs.appendChild(option);
                    inactifsTrouves = true;
                }
            });
            
            // Ajouter les groupes au sélecteur
            if (actifsTrouves) {
                baremeSelect.appendChild(groupeActifs);
            }
            
            if (inactifsTrouves) {
                baremeSelect.appendChild(groupeInactifs);
            }
            
            // Sélectionner automatiquement le premier barème actif s'il existe
            if (actifsTrouves && groupeActifs.children.length > 0) {
                baremeSelect.value = groupeActifs.children[0].value;
                
                // Déclencher l'événement de changement pour mettre à jour le montant
                const event = new Event('change');
                baremeSelect.dispatchEvent(event);
            }
        } else {
            console.log("Aucun barème disponible");
            // Message si aucun barème n'est disponible
            const optionAucun = document.createElement('option');
            optionAucun.disabled = true;
            optionAucun.textContent = 'Aucun barème disponible pour ce type de membre';
            baremeSelect.appendChild(optionAucun);
        }
    }
    
    /**
     * Calcule la durée standard en jours selon la périodicité
     */
    function getDureeJoursParPeriodicite(periodicite) {
        switch (periodicite) {
            case 'mensuelle': return 30;
            case 'trimestrielle': return 91;
            case 'semestrielle': return 182;
            case 'annuelle': return 365;
            default: return 365;
        }
    }
    
    /**
     * Réinitialise le sélecteur de barème
     */
    function reinitialiserBareme() {
        baremeSelect.innerHTML = '';
        const option = document.createElement('option');
        option.value = '';
        option.textContent = 'Sélectionnez d\'abord un type de membre';
        baremeSelect.appendChild(option);
        
        baremesDisponibles = [];
    }
    
    /**
     * Affiche un message d'erreur
     */
    function afficherErreur(message) {
        console.error(message);
        const alerteElem = document.getElementById('alerte-bareme');
        if (alerteElem) {
            alerteElem.textContent = message;
            alerteElem.style.display = 'block';
            
            setTimeout(() => {
                alerteElem.style.display = 'none';
            }, 5000);
        }
    }
    
    // Indiquer que le script a été chargé correctement
    console.log("Script de filtrage des barèmes chargé");
});