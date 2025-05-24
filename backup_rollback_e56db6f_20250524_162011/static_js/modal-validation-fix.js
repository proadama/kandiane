/**
 * modal-validation-fix.js - Solution ciblée pour le problème de duplication
 * dans les modals de paiement
 */
(function() {
    // Cibler spécifiquement les modals de paiement
    const targetSelector = '#paiementModal';
    
    // Registre pour suivre les erreurs déjà affichées
    const errorRegistry = {
        errors: {},
        
        hasError: function(modal, fieldId, message) {
            const key = `${modal.id}-${fieldId}`;
            return this.errors[key] && this.errors[key].includes(message);
        },
        
        addError: function(modal, fieldId, message) {
            const key = `${modal.id}-${fieldId}`;
            this.errors[key] = this.errors[key] || [];
            
            if (!this.errors[key].includes(message)) {
                this.errors[key].push(message);
                return true;
            }
            return false;
        },
        
        clearErrors: function(modal, fieldId) {
            if (fieldId) {
                const key = `${modal.id}-${fieldId}`;
                delete this.errors[key];
            } else {
                // Supprimer toutes les erreurs pour cette modal
                const prefix = `${modal.id}-`;
                Object.keys(this.errors).forEach(key => {
                    if (key.startsWith(prefix)) {
                        delete this.errors[key];
                    }
                });
            }
        }
    };
    
    // Fonction pour nettoyer toutes les erreurs dans une modal
    function clearModalErrors(modal) {
        if (!modal) return;
        
        // Supprimer tous les messages d'erreur
        modal.querySelectorAll('.invalid-feedback, .text-danger').forEach(el => {
            el.remove();
        });
        
        // Retirer la classe d'invalidité
        modal.querySelectorAll('.is-invalid').forEach(el => {
            el.classList.remove('is-invalid');
        });
        
        // Vider le registre
        errorRegistry.clearErrors(modal);
    }
    
    // Fonction pour nettoyer les erreurs d'un champ spécifique
    function clearFieldErrors(field, modal) {
        if (!field || !modal) return;
        
        // Supprimer la classe d'invalidité
        field.classList.remove('is-invalid');
        
        // Identifier le champ
        const fieldId = field.id || field.name;
        if (!fieldId) return;
        
        // Vider le registre pour ce champ
        errorRegistry.clearErrors(modal, fieldId);
        
        // Chercher et supprimer les messages associés
        const container = field.closest('.form-group, .input-group') || field.parentNode;
        container.querySelectorAll('.invalid-feedback, .text-danger').forEach(el => {
            el.remove();
        });
        
        // Si c'est dans un input-group, nettoyer aussi le parent
        if (field.parentNode.classList.contains('input-group')) {
            const parentContainer = field.parentNode.parentNode;
            parentContainer.querySelectorAll('.invalid-feedback, .text-danger').forEach(el => {
                el.remove();
            });
        }
    }
    
    // Fonction spéciale pour la conversion des nombres avec virgule
    function safeParseFloat(value) {
        if (typeof value === 'string') {
            value = value.replace(',', '.');
        }
        return parseFloat(value);
    }
    
    // Observer les changements du DOM pour intercepter l'ouverture de la modal
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList') {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType !== Node.ELEMENT_NODE) return;
                    
                    // Vérifier si c'est notre modal ou si elle contient notre modal
                    const modal = node.matches(targetSelector) ? 
                        node : node.querySelector(targetSelector);
                    
                    if (!modal) return;
                    
                    // La modal a été ajoutée ! Initialiser notre correctif
                    initializeModalFix(modal);
                });
            }
        });
    });
    
    // Démarrer l'observation du DOM
    observer.observe(document.body, { childList: true, subtree: true });
    
    // Vérifier aussi si la modal existe déjà
    document.addEventListener('DOMContentLoaded', function() {
        const existingModal = document.querySelector(targetSelector);
        if (existingModal) {
            initializeModalFix(existingModal);
        }
    });
    
    // Initialisation du correctif pour une modal spécifique
    function initializeModalFix(modal) {
        console.log('Modal de paiement détectée, application du correctif anti-duplication');
        
        // 1. Intercepter l'ouverture de la modal pour nettoyer les erreurs
        modal.addEventListener('show.bs.modal', function() {
            clearModalErrors(modal);
        });
        
        // 2. Trouver le formulaire dans la modal
        const form = modal.querySelector('form');
        if (!form) return;
        
        // 3. Trouver les champs importants
        const montantInput = form.querySelector('input[id*="montant"]');
        const typeSelect = form.querySelector('select[id*="type_transaction"]');
        
        // 4. Ajouter nos propres écouteurs d'événements
        if (montantInput) {
            // Nettoyer les erreurs à la saisie
            montantInput.addEventListener('input', function() {
                clearFieldErrors(this, modal);
            });
            
            // Validation personnalisée
            montantInput.addEventListener('blur', function() {
                validateMontant(this, typeSelect, modal);
            });
        }
        
        if (typeSelect) {
            typeSelect.addEventListener('change', function() {
                if (montantInput) {
                    clearFieldErrors(montantInput, modal);
                    validateMontant(montantInput, this, modal);
                }
            });
        }
        
        // 5. Intercepter la soumission du formulaire
        form.addEventListener('submit', function(event) {
            // Ne pas interférer avec d'autres validations, juste nettoyer avant
            clearModalErrors(modal);
        }, true); // Phase de capture pour s'exécuter en premier
        
        // 6. Patch de la fonction highlightField si elle est utilisée dans cette modal
        const originalHighlightField = window.highlightField;
        window.highlightField = function(field, message) {
            // Ne pas dupliquer les messages dans la modal
            if (field && modal.contains(field)) {
                if (!errorRegistry.addError(modal, field.id || field.name, message)) {
                    return; // Message déjà présent, ne rien faire
                }
            }
            
            // Appeler l'original pour les autres cas
            if (originalHighlightField) {
                originalHighlightField(field, message);
            }
        };
    }
    
    // Fonction de validation personnalisée pour le montant
    function validateMontant(montantInput, typeSelect, modal) {
        if (!montantInput) return;
        
        // Convertir la valeur avec virgule en nombre
        const value = montantInput.value.trim();
        const montant = safeParseFloat(value);
        
        // Vérifier si c'est un nombre valide et positif
        if (isNaN(montant) || montant <= 0) {
            // Ajouter la classe d'invalidité
            montantInput.classList.add('is-invalid');
            
            // Trouver le bon conteneur
            const container = montantInput.closest('.form-group') || montantInput.parentNode;
            const targetContainer = montantInput.parentNode.classList.contains('input-group') ? 
                montantInput.parentNode.parentNode : container;
            
            // Ajouter le message d'erreur s'il n'existe pas déjà
            const message = "Le montant doit être supérieur à zéro.";
            if (errorRegistry.addError(modal, montantInput.id || montantInput.name, message)) {
                const errorDiv = document.createElement('div');
                errorDiv.className = 'invalid-feedback d-block';
                errorDiv.textContent = message;
                targetContainer.appendChild(errorDiv);
            }
            return false;
        }
        
        // Vérifier si le montant ne dépasse pas le maximum pour les paiements
        if (typeSelect && typeSelect.value === 'paiement') {
            // Trouver le montant maximum autorisé
            const montantRestantElement = modal.querySelector('[data-montant-restant]');
            if (montantRestantElement) {
                const montantRestant = safeParseFloat(montantRestantElement.dataset.montantRestant);
                
                if (montant > montantRestant) {
                    // Ajouter la classe d'invalidité
                    montantInput.classList.add('is-invalid');
                    
                    // Trouver le bon conteneur
                    const container = montantInput.closest('.form-group') || montantInput.parentNode;
                    const targetContainer = montantInput.parentNode.classList.contains('input-group') ? 
                        montantInput.parentNode.parentNode : container;
                    
                    // Ajouter le message d'erreur s'il n'existe pas déjà
                    const message = `Le montant ne peut pas dépasser le montant restant à payer (${montantRestant.toLocaleString('fr-FR', {minimumFractionDigits: 2, maximumFractionDigits: 2}).replace('.', ',')} €).`;
                    
                    if (errorRegistry.addError(modal, montantInput.id || montantInput.name, message)) {
                        const errorDiv = document.createElement('div');
                        errorDiv.className = 'invalid-feedback d-block';
                        errorDiv.textContent = message;
                        targetContainer.appendChild(errorDiv);
                    }
                    return false;
                }
            }
        }
        
        // Tout est valide
        montantInput.classList.remove('is-invalid');
        return true;
    }
    
    console.log('Correctif anti-duplication pour les modals de paiement chargé');
})();