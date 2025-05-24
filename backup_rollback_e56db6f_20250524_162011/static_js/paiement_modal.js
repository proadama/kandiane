/**
 * Gestion AJAX des paiements pour l'application Cotisations
 * Version sécurisée avec génération automatique des références
 */
class PaiementManager {
    constructor(options = {}) {
        this.options = Object.assign({
            formSelector: '#paiementAjaxForm',
            paiementsListSelector: '#paiementsList',
            submitButtonSelector: '#submitPaiement',
            modalSelector: '#paiementModal',
            totalPayeSelector: '#totalPaye',
            montantRestantSelector: '#montantRestant',
            statutPaiementSelector: '#statutPaiement',
            progressBarSelector: '#progressPaiement',
            alertsContainerSelector: '#alertsContainer',
            cotisationId: null,
            csrfTokenName: 'csrfmiddlewaretoken' // Nom du token CSRF pour Django
        }, options);
        
        this.form = document.querySelector(this.options.formSelector);
        this.paiementsList = document.querySelector(this.options.paiementsListSelector);
        this.submitButton = document.querySelector(this.options.submitButtonSelector);
        this.modal = document.querySelector(this.options.modalSelector);
        this.totalPayeElement = document.querySelector(this.options.totalPayeSelector);
        this.montantRestantElement = document.querySelector(this.options.montantRestantSelector);
        this.statutPaiementElement = document.querySelector(this.options.statutPaiementSelector);
        this.progressBarElement = document.querySelector(this.options.progressBarSelector);
        this.alertsContainer = document.querySelector(this.options.alertsContainerSelector);
        
        this.bootstrapModal = null;
        if (this.modal) {
            this.bootstrapModal = new bootstrap.Modal(this.modal);
        }
        
        this.validator = null;
        this.csrfToken = this.getCsrfToken();
        
        this.init();
    }
    
    /**
     * Récupère le token CSRF depuis les cookies ou le DOM
     */
    getCsrfToken() {
        // Essayer d'abord de récupérer depuis un input dans le formulaire
        const tokenInput = this.form ? this.form.querySelector(`[name="${this.options.csrfTokenName}"]`) : null;
        if (tokenInput && tokenInput.value) {
            return tokenInput.value;
        }
        
        // Sinon, essayer de récupérer depuis les cookies
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
            
        return cookieValue || '';
    }
    
    /**
     * Échapper les caractères HTML pour prévenir les attaques XSS
     */
    escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
    
    init() {
        if (!this.form) {
            console.error('Formulaire de paiement non trouvé');
            return;
        }
        
        // Initialiser la validation
        this.setupValidation();
        
        // Gérer la soumission du formulaire
        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            
            if (this.validator && !this.validator.validateAll()) {
                return;
            }
            
            this.envoyerPaiement();
        });
        
        // Réinitialiser le formulaire lors de l'ouverture du modal
        if (this.modal) {
            this.modal.addEventListener('show.bs.modal', () => {
                this.resetForm();
            });
        }
        
        // Gérer le changement de type de transaction
        const typeTransactionSelect = this.form.querySelector('[name="type_transaction"]');
        const montantInput = this.form.querySelector('[name="montant"]');
        
        if (typeTransactionSelect && montantInput) {
            typeTransactionSelect.addEventListener('change', () => {
                // Ajuster les limitations de montant selon le type
                if (typeTransactionSelect.value === 'paiement') {
                    const montantRestant = parseFloat(this.montantRestantElement.dataset.value || 0);
                    montantInput.setAttribute('max', montantRestant);
                    montantInput.value = Math.min(parseFloat(montantInput.value || 0), montantRestant).toFixed(2);
                } else {
                    montantInput.removeAttribute('max');
                }
                
                // Mettre à jour l'info sur la référence qui sera générée
                this.updateReferenceInfo(typeTransactionSelect.value);
                
                // Revalider le champ
                if (this.validator) {
                    this.validator.validateField('formMontant');
                }
            });
        }
        
        // Initialiser l'info de référence
        if (typeTransactionSelect) {
            this.updateReferenceInfo(typeTransactionSelect.value);
        }
    }
    
    /**
     * Met à jour l'information sur la référence qui sera générée
     */
    updateReferenceInfo(transactionType) {
        const referenceInfoElement = document.getElementById('referenceGenerationInfo');
        if (!referenceInfoElement) return;
        
        const prefixes = {
            'paiement': 'PAI',
            'remboursement': 'RMB',
            'rejet': 'REJ'
        };
        
        const prefix = prefixes[transactionType] || 'PAI';
        const dateToday = new Date().toISOString().slice(0, 10).replace(/-/g, '');
        
        referenceInfoElement.innerHTML = `
            <strong>Référence:</strong> 
            <span class="text-muted"><em>Sera générée automatiquement</em></span>
            <br>
            <small class="text-info">Format: ${prefix}-${dateToday}-XXXX-YYYY</small>
        `;
    }
    
    setupValidation() {
        // Créer un validateur pour le formulaire
        this.validator = new FormValidator(this.form.id, {
            validateOnInput: true,
            validateOnBlur: true
        });
        
        // Ajouter les règles de validation
        this.validator
            .addValidator('formMontant', [
                ValidationRules.required('Veuillez indiquer un montant'),
                ValidationRules.numeric('Le montant doit être un nombre'),
                ValidationRules.positiveNumber('Le montant doit être supérieur à zéro'),
                ValidationRules.custom(
                    (value) => {
                        const typeTransaction = this.form.querySelector('[name="type_transaction"]').value;
                        const montantRestant = parseFloat(this.montantRestantElement.dataset.value || 0);
                        
                        // La validation du montant max ne s'applique qu'aux paiements
                        return typeTransaction !== 'paiement' || parseFloat(value) <= montantRestant;
                    },
                    `Le montant ne peut pas dépasser le montant restant à payer`
                )
            ])
            .addValidator('formModePaiement', [
                ValidationRules.required('Veuillez sélectionner un mode de paiement')
            ])
            .addValidator('formDatePaiement', [
                ValidationRules.required('La date de paiement est obligatoire'),
                ValidationRules.date('Veuillez entrer une date valide')
            ]);
    }
    
    envoyerPaiement() {
        if (!this.form) return;
        
        // Afficher un indicateur de chargement
        this.submitButton.disabled = true;
        const originalText = this.submitButton.innerHTML;
        this.submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Traitement...';
        
        // Récupérer les données du formulaire
        const formData = new FormData(this.form);
        const cotisationId = this.options.cotisationId || this.form.dataset.cotisationId;
        
        // Convertir en objet
        const data = Object.fromEntries(formData.entries());
        
        // Supprimer la référence de paiement si elle existe
        // (puisqu'elle sera générée automatiquement par le serveur)
        if (data.reference_paiement) {
            delete data.reference_paiement;
        }
        
        // Ajouter le token CSRF si nécessaire
        if (this.csrfToken && !data[this.options.csrfTokenName]) {
            data[this.options.csrfTokenName] = this.csrfToken;
        }
        
        // Appeler l'API pour enregistrer le paiement
        fetch(`/cotisations/${cotisationId}/paiement/ajax/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify(data),
            credentials: 'same-origin'
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Erreur HTTP: ${response.status}`);
            }
            return response.json();
        })
        .then(response => {
            if (response.success) {
                // Ajouter le nouveau paiement à la liste
                this.ajouterPaiementAListe(response.paiement);
                
                // Mettre à jour les informations de la cotisation
                this.mettreAJourInfosCotisation(response.cotisation);
                
                // Afficher un message de succès
                this.afficherMessage('success', response.message || 'Paiement enregistré avec succès');
                
                // Fermer le modal
                if (this.bootstrapModal) {
                    this.bootstrapModal.hide();
                }
            } else {
                // Afficher l'erreur
                this.afficherMessage('danger', response.message || 'Erreur lors de l\'enregistrement du paiement');
                console.error('Erreurs:', response.errors);
            }
        })
        .catch(error => {
            console.error('Erreur:', error);
            this.afficherMessage('danger', 'Une erreur s\'est produite lors de la communication avec le serveur');
        })
        .finally(() => {
            // Réinitialiser le bouton
            this.submitButton.disabled = false;
            this.submitButton.innerHTML = originalText;
        });
    }
    
    ajouterPaiementAListe(paiement) {
        if (!this.paiementsList || !paiement) return;
        
        // Créer une nouvelle ligne pour le paiement
        const tr = document.createElement('tr');
        tr.id = `paiement-${paiement.id}`;
        
        // Classe pour les nouveaux éléments (pour animation)
        tr.classList.add('new-item');
        
        // Formater la date
        const datePaiement = new Date(paiement.date_paiement);
        const dateFormatee = datePaiement.toLocaleDateString('fr-FR') + ' ' + 
                            datePaiement.toLocaleTimeString('fr-FR', {hour: '2-digit', minute:'2-digit'});
        
        // Classe pour le type de transaction
        let badgeClass = 'bg-success';
        if (paiement.type_transaction === 'remboursement') {
            badgeClass = 'bg-warning';
        } else if (paiement.type_transaction === 'rejet') {
            badgeClass = 'bg-danger';
        }
        
        // Construire le contenu HTML avec échappement des données
        tr.innerHTML = `
            <td>${this.escapeHtml(dateFormatee)}</td>
            <td>${parseFloat(paiement.montant).toFixed(2)} €</td>
            <td>${this.escapeHtml(paiement.mode_paiement)}</td>
            <td><span class="badge ${badgeClass}">${this.escapeHtml(paiement.type_transaction)}</span></td>
            <td>${this.escapeHtml(paiement.reference_paiement || '-')}</td>
            <td class="text-center">
                <div class="btn-group">
                    <a href="/cotisations/paiements/${paiement.id}/" class="btn btn-sm btn-outline-primary">
                        <i class="fas fa-eye"></i>
                    </a>
                    <a href="/cotisations/paiements/${paiement.id}/modifier/" class="btn btn-sm btn-outline-secondary">
                        <i class="fas fa-edit"></i>
                    </a>
                    <a href="/cotisations/paiements/${paiement.id}/supprimer/" class="btn btn-sm btn-outline-danger">
                        <i class="fas fa-trash"></i>
                    </a>
                </div>
            </td>
        `;
        
        // Ajouter au début de la liste
        if (this.paiementsList.querySelector('tbody')) {
            this.paiementsList.querySelector('tbody').prepend(tr);
        } else {
            this.paiementsList.prepend(tr);
        }
        
        // Mettre à jour le message si la liste était vide
        const emptyMessage = document.querySelector('#noPaiementsMessage');
        if (emptyMessage) {
            emptyMessage.style.display = 'none';
        }
        
        // Animer l'entrée
        setTimeout(() => {
            tr.classList.add('show');
        }, 10);
        
        // Supprimer la classe d'animation après un délai
        setTimeout(() => {
            tr.classList.remove('new-item', 'show');
        }, 3000);
    }
    
    mettreAJourInfosCotisation(cotisation) {
        if (!cotisation) return;
        
        // Mettre à jour le montant total payé
        if (this.totalPayeElement) {
            const montantPaye = cotisation.montant - cotisation.montant_restant;
            this.totalPayeElement.textContent = montantPaye.toFixed(2) + ' €';
        }
        
        // Mettre à jour le montant restant
        if (this.montantRestantElement) {
            this.montantRestantElement.textContent = cotisation.montant_restant.toFixed(2) + ' €';
            this.montantRestantElement.dataset.value = cotisation.montant_restant;
            
            // Mettre à jour la couleur selon le montant restant
            if (cotisation.montant_restant <= 0) {
                this.montantRestantElement.classList.remove('text-danger');
                this.montantRestantElement.classList.add('text-success');
            } else {
                this.montantRestantElement.classList.remove('text-success');
                this.montantRestantElement.classList.add('text-danger');
            }
        }
        
        // Mettre à jour le statut de paiement
        if (this.statutPaiementElement) {
            // Supprimer les anciennes classes
            this.statutPaiementElement.classList.remove('bg-danger', 'bg-warning', 'bg-success');
            
            // Ajouter la nouvelle classe selon le statut
            let newClass = 'bg-danger';
            let statutText = 'Non payée';
            
            if (cotisation.statut_paiement === 'payee') {
                newClass = 'bg-success';
                statutText = 'Payée';
            } else if (cotisation.statut_paiement === 'partiellement_payee') {
                newClass = 'bg-warning';
                statutText = 'Partiellement payée';
            }
            
            this.statutPaiementElement.classList.add(newClass);
            this.statutPaiementElement.textContent = statutText;
        }
        
        // Mettre à jour la barre de progression
        if (this.progressBarElement) {
            const montantTotal = parseFloat(this.progressBarElement.dataset.montantTotal || 0);
            const pourcentage = montantTotal > 0 ? ((montantTotal - cotisation.montant_restant) / montantTotal * 100).toFixed(0) : 0;
            
            this.progressBarElement.style.width = pourcentage + '%';
            this.progressBarElement.setAttribute('aria-valuenow', pourcentage);
            this.progressBarElement.textContent = pourcentage + '%';
            
            // Mettre à jour la couleur de la barre de progression
            this.progressBarElement.classList.remove('bg-danger', 'bg-warning', 'bg-success');
            
            if (pourcentage >= 100) {
                this.progressBarElement.classList.add('bg-success');
            } else if (pourcentage >= 50) {
                this.progressBarElement.classList.add('bg-warning');
            } else {
                this.progressBarElement.classList.add('bg-danger');
            }
        }
    }
    
    resetForm() {
        if (!this.form) return;
        
        // Réinitialiser les champs du formulaire
        this.form.reset();
        
        // Réinitialiser le montant par défaut (montant restant pour les paiements)
        const montantInput = this.form.querySelector('[name="montant"]');
        const typeTransactionSelect = this.form.querySelector('[name="type_transaction"]');
        
        if (montantInput && typeTransactionSelect && this.montantRestantElement) {
            if (typeTransactionSelect.value === 'paiement') {
                montantInput.value = parseFloat(this.montantRestantElement.dataset.value || 0).toFixed(2);
            }
        }
        
        // Réinitialiser la date de paiement à aujourd'hui
        const dateInput = this.form.querySelector('[name="date_paiement"]');
        if (dateInput) {
            const now = new Date();
            const year = now.getFullYear();
            const month = String(now.getMonth() + 1).padStart(2, '0');
            const day = String(now.getDate()).padStart(2, '0');
            const hours = String(now.getHours()).padStart(2, '0');
            const minutes = String(now.getMinutes()).padStart(2, '0');
            
            dateInput.value = `${year}-${month}-${day}T${hours}:${minutes}`;
        }
        
        // Mettre à jour l'info de référence
        if (typeTransactionSelect) {
            this.updateReferenceInfo(typeTransactionSelect.value);
        }
        
        // Réinitialiser les validations
        if (this.validator) {
            this.validator.reset();
        }
    }
    
    afficherMessage(type, message) {
        if (!this.alertsContainer) {
            // Créer un container pour les alertes si nécessaire
            this.alertsContainer = document.createElement('div');
            this.alertsContainer.id = 'alertsContainer';
            this.alertsContainer.className = 'mb-4';
            
            // Insérer avant le premier enfant du conteneur principal
            const mainContainer = document.querySelector('.container-fluid');
            if (mainContainer && mainContainer.firstChild) {
                mainContainer.insertBefore(this.alertsContainer, mainContainer.firstChild);
            }
        }
        
        // Créer l'alerte avec échappement du message pour prévenir les attaques XSS
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.role = 'alert';
        
        // Ajouter l'icône appropriée
        let icon = 'info-circle';
        if (type === 'success') icon = 'check-circle';
        if (type === 'danger') icon = 'exclamation-triangle';
        if (type === 'warning') icon = 'exclamation-circle';
        
        alert.innerHTML = `
            <i class="fas fa-${icon} me-2"></i>
            ${this.escapeHtml(message)}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        // Ajouter l'alerte au container
        this.alertsContainer.appendChild(alert);
        
        // Faire défiler jusqu'à l'alerte
        window.scrollTo({
            top: this.alertsContainer.offsetTop - 20,
            behavior: 'smooth'
        });
        
        // Supprimer l'alerte après un délai
        setTimeout(() => {
            if (alert.parentNode) {
                // Ajouter la classe pour l'animation de sortie
                alert.classList.remove('show');
                
                // Supprimer après l'animation
                setTimeout(() => {
                    if (alert.parentNode) {
                        alert.parentNode.removeChild(alert);
                    }
                }, 150);
            }
        }, 5000);
    }
}

// Initialiser le gestionnaire de paiements quand le DOM est chargé
document.addEventListener('DOMContentLoaded', function() {
    const cotisationDetailElement = document.getElementById('cotisationDetail');
    
    if (cotisationDetailElement) {
        const cotisationId = cotisationDetailElement.dataset.cotisationId;
        
        if (cotisationId) {
            // Initialiser le gestionnaire de paiements
            const paiementManager = new PaiementManager({
                cotisationId: cotisationId
            });
            
            // Eviter l'exposition globale pour sécurité
            // window.paiementManager = paiementManager; // Commenté pour sécurité
        }
    }
});