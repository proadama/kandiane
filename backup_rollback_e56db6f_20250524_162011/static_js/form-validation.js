/**
 * Validation dynamique des formulaires pour l'application Cotisations
 */
class FormValidator {
    constructor(formId, options = {}) {
        this.form = document.getElementById(formId);
        this.options = Object.assign({
            validateOnInput: true,
            validateOnBlur: true,
            validateOnSubmit: true,
            showSuccessState: true
        }, options);
        
        this.validators = {};
        this.errors = {};
        
        this.init();
    }
    
    init() {
        if (!this.form) {
            console.error('Le formulaire avec ID', formId, 'n\'a pas été trouvé.');
            return;
        }
        
        // Valider à la soumission
        if (this.options.validateOnSubmit) {
            this.form.addEventListener('submit', (e) => {
                if (!this.validateAll()) {
                    e.preventDefault();
                    this.focusFirstInvalid();
                }
            });
        }
    }
    
    // Ajouter une règle de validation pour un champ
    addValidator(fieldId, rules) {
        const field = document.getElementById(fieldId);
        if (!field) {
            console.error('Champ non trouvé:', fieldId);
            return this;
        }
        
        this.validators[fieldId] = rules;
        
        // Valider au changement si l'option est activée
        if (this.options.validateOnInput) {
            field.addEventListener('input', () => this.validateField(fieldId));
        }
        
        // Valider à la perte de focus si l'option est activée
        if (this.options.validateOnBlur) {
            field.addEventListener('blur', () => this.validateField(fieldId));
        }
        
        return this;
    }
    
    // Valider un champ spécifique
    validateField(fieldId) {
        const field = document.getElementById(fieldId);
        if (!field || !this.validators[fieldId]) return true;
        
        const rules = this.validators[fieldId];
        const value = field.value.trim();
        let isValid = true;
        let errorMessage = '';
        
        // Parcourir les règles et valider
        for (const rule of rules) {
            if (!rule.validate(value, field)) {
                isValid = false;
                errorMessage = rule.message;
                break;
            }
        }
        
        // Mettre à jour l'état du champ (valide/invalide)
        this.updateFieldState(fieldId, isValid, errorMessage);
        
        // Mettre à jour les erreurs
        if (isValid) {
            delete this.errors[fieldId];
        } else {
            this.errors[fieldId] = errorMessage;
        }
        
        return isValid;
    }
    
    // Valider tous les champs
    validateAll() {
        let isFormValid = true;
        
        for (const fieldId in this.validators) {
            if (!this.validateField(fieldId)) {
                isFormValid = false;
            }
        }
        
        return isFormValid;
    }
    
    // Mettre à jour l'état visuel d'un champ
    updateFieldState(fieldId, isValid, errorMessage = '') {
        const field = document.getElementById(fieldId);
        if (!field) return;
        
        // Trouver le conteneur
        const container = field.closest('.form-group') || field.parentNode;
        
        // Nettoyer les classes et messages précédents
        field.classList.remove('is-valid', 'is-invalid');
        
        // Supprimer les messages d'erreur existants
        const existingFeedback = container.querySelector('.invalid-feedback');
        if (existingFeedback) {
            existingFeedback.remove();
        }
        
        if (isValid) {
            // Appliquer les styles de succès si l'option est activée
            if (this.options.showSuccessState) {
                field.classList.add('is-valid');
            }
        } else {
            // Appliquer les styles d'erreur
            field.classList.add('is-invalid');
            
            // Créer le message d'erreur
            const feedback = document.createElement('div');
            feedback.className = 'invalid-feedback d-block';
            feedback.textContent = errorMessage;
            
            // Ajouter le message après le champ ou son conteneur
            if (field.parentNode.classList.contains('input-group')) {
                field.parentNode.parentNode.appendChild(feedback);
            } else {
                container.appendChild(feedback);
            }
        }
    }
    
    // Mettre le focus sur le premier champ invalide
    focusFirstInvalid() {
        for (const fieldId in this.errors) {
            const field = document.getElementById(fieldId);
            if (field) {
                field.focus();
                break;
            }
        }
    }
    
    // Réinitialiser l'état de tous les champs
    reset() {
        this.errors = {};
        for (const fieldId in this.validators) {
            const field = document.getElementById(fieldId);
            if (field) {
                field.classList.remove('is-valid', 'is-invalid');
                
                // Trouver le conteneur
                const container = field.closest('.form-group') || field.parentNode;
                
                // Supprimer les messages d'erreur existants
                const existingFeedback = container.querySelector('.invalid-feedback');
                if (existingFeedback) {
                    existingFeedback.remove();
                }
            }
        }
    }
}

// Règles de validation prédéfinies
const ValidationRules = {
    required: (message = 'Ce champ est obligatoire') => ({
        validate: value => value !== '',
        message: message
    }),
    
    min: (min, message = `La valeur doit être supérieure ou égale à ${min}`) => ({
        validate: value => value === '' || parseFloat(value) >= min,
        message: message
    }),
    
    max: (max, message = `La valeur doit être inférieure ou égale à ${max}`) => ({
        validate: value => value === '' || parseFloat(value) <= max,
        message: message
    }),
    
    email: (message = 'Veuillez saisir une adresse email valide') => ({
        validate: value => value === '' || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value),
        message: message
    }),
    
    date: (message = 'Veuillez saisir une date valide') => ({
        validate: value => value === '' || !isNaN(new Date(value).getTime()),
        message: message
    }),
    
    dateAfter: (otherFieldId, message = 'La date doit être postérieure à {otherField}') => ({
        validate: (value, field) => {
            if (value === '') return true;
            
            const otherField = document.getElementById(otherFieldId);
            if (!otherField || otherField.value === '') return true;
            
            const date = new Date(value);
            const otherDate = new Date(otherField.value);
            
            return date > otherDate;
        },
        message: message.replace('{otherField}', document.getElementById(otherFieldId)?.previousElementSibling?.textContent || 'la date précédente')
    }),
    
    dateBefore: (otherFieldId, message = 'La date doit être antérieure à {otherField}') => ({
        validate: (value, field) => {
            if (value === '') return true;
            
            const otherField = document.getElementById(otherFieldId);
            if (!otherField || otherField.value === '') return true;
            
            const date = new Date(value);
            const otherDate = new Date(otherField.value);
            
            return date < otherDate;
        },
        message: message.replace('{otherField}', document.getElementById(otherFieldId)?.previousElementSibling?.textContent || 'la date suivante')
    }),
    
    numeric: (message = 'Veuillez saisir un nombre valide') => ({
        validate: value => value === '' || !isNaN(parseFloat(value)),
        message: message
    }),
    
    positiveNumber: (message = 'Veuillez saisir un nombre positif') => ({
        validate: value => value === '' || (parseFloat(value) > 0 && !isNaN(parseFloat(value))),
        message: message
    }),
    
    maxLength: (maxLength, message = `La longueur maximale est de ${maxLength} caractères`) => ({
        validate: value => value.length <= maxLength,
        message: message
    }),
    
    minLength: (minLength, message = `La longueur minimale est de ${minLength} caractères`) => ({
        validate: value => value === '' || value.length >= minLength,
        message: message
    }),
    
    pattern: (regex, message = 'Format invalide') => ({
        validate: value => value === '' || regex.test(value),
        message: message
    }),
    
    custom: (validateFn, message = 'Validation échouée') => ({
        validate: validateFn,
        message: message
    })
};

// Validation spécifique pour les cotisations
function setupCotisationValidation() {
    const validator = new FormValidator('cotisationForm', {
        validateOnInput: true,
        validateOnBlur: true
    });
    
    // Règles de validation pour chaque champ
    validator.addValidator('id_membre', [
        ValidationRules.required('Veuillez sélectionner un membre')
    ]);
    
    validator.addValidator('id_type_membre', [
        ValidationRules.required('Veuillez sélectionner un type de membre')
    ]);
    
    validator.addValidator('id_montant', [
        ValidationRules.required('Veuillez indiquer un montant'),
        ValidationRules.numeric('Le montant doit être un nombre'),
        ValidationRules.positiveNumber('Le montant doit être supérieur à zéro')
    ]);
    
    validator.addValidator('id_date_emission', [
        ValidationRules.required('La date d\'émission est obligatoire'),
        ValidationRules.date('Veuillez entrer une date valide')
    ]);
    
    validator.addValidator('id_date_echeance', [
        ValidationRules.required('La date d\'échéance est obligatoire'),
        ValidationRules.date('Veuillez entrer une date valide'),
        ValidationRules.dateAfter('id_date_emission', 'La date d\'échéance doit être postérieure à la date d\'émission')
    ]);
    
    validator.addValidator('id_periode_debut', [
        ValidationRules.required('La date de début de période est obligatoire'),
        ValidationRules.date('Veuillez entrer une date valide')
    ]);
    
    validator.addValidator('id_periode_fin', [
        ValidationRules.date('Veuillez entrer une date valide'),
        ValidationRules.dateAfter('id_periode_debut', 'La date de fin doit être postérieure à la date de début')
    ]);
    
    // Validation conditionnelle pour la référence
    const genererReferenceCheckbox = document.getElementById('id_generer_reference');
    const referenceInput = document.getElementById('id_reference');
    
    if (genererReferenceCheckbox && referenceInput) {
        validator.addValidator('id_reference', [
            ValidationRules.custom(
                (value) => genererReferenceCheckbox.checked || value.trim() !== '',
                'Une référence est requise si la génération automatique est désactivée'
            )
        ]);
        
        // Mettre à jour la validation lorsque la case à cocher change
        genererReferenceCheckbox.addEventListener('change', () => {
            validator.validateField('id_reference');
        });
    }
    
    return validator;
}

// Validation spécifique pour les paiements
function setupPaiementValidation() {

    const validator = new FormValidator('paiementForm');
    
    // Montant maximal pour les paiements
    let montantMaximal = Infinity;
    const cotisationElement = document.querySelector('[data-montant-restant]');
    if (cotisationElement) {
        montantMaximal = parseFloat(cotisationElement.dataset.montantRestant);
    }
    
    // Règles de validation pour chaque champ
    validator.addValidator('id_montant', [
        ValidationRules.required('Veuillez indiquer un montant'),
        ValidationRules.numeric('Le montant doit être un nombre'),
        ValidationRules.positiveNumber('Le montant doit être supérieur à zéro'),
        ValidationRules.custom(
            (value) => {
                const typeTransaction = document.getElementById('id_type_transaction')?.value;
                // Appliquer la limite uniquement pour les paiements, pas pour les remboursements
                return typeTransaction !== 'paiement' || parseFloat(value) <= montantMaximal;
            },
            `Le montant ne peut pas dépasser le montant restant à payer (${montantMaximal.toFixed(2)} €)`
        )
    ]);
    
    validator.addValidator('id_mode_paiement', [
        ValidationRules.required('Veuillez sélectionner un mode de paiement')
    ]);
    
    validator.addValidator('id_date_paiement', [
        ValidationRules.required('La date de paiement est obligatoire'),
        ValidationRules.date('Veuillez entrer une date valide')
    ]);
    
    // Gestion du changement de type de transaction
    const typeTransactionSelect = document.getElementById('id_type_transaction');
    if (typeTransactionSelect) {
        typeTransactionSelect.addEventListener('change', () => {
            validator.validateField('id_montant');
        });
    }
    
    return validator;
}

// Validation spécifique pour les rappels
function setupRappelValidation() {
    const validator = new FormValidator('rappelForm');
    
    validator.addValidator('id_type_rappel', [
        ValidationRules.required('Veuillez sélectionner un type de rappel')
    ]);
    
    validator.addValidator('id_niveau', [
        ValidationRules.required('Veuillez indiquer un niveau de rappel'),
        ValidationRules.numeric('Le niveau doit être un nombre'),
        ValidationRules.min(1, 'Le niveau doit être au minimum 1')
    ]);
    
    validator.addValidator('id_contenu', [
        ValidationRules.required('Le contenu du rappel est obligatoire'),
        ValidationRules.minLength(10, 'Le contenu est trop court')
    ]);
    
    // Validation pour les dates d'envoi planifiées
    const envoyerImmediatementSwitch = document.getElementById('envoyerImmediatement');
    
    if (envoyerImmediatementSwitch) {
        validator.addValidator('datePlanification', [
            ValidationRules.custom(
                (value) => envoyerImmediatementSwitch.checked || value.trim() !== '',
                'Veuillez sélectionner une date d\'envoi'
            )
        ]);
        
        validator.addValidator('heurePlanification', [
            ValidationRules.custom(
                (value) => envoyerImmediatementSwitch.checked || value.trim() !== '',
                'Veuillez sélectionner une heure d\'envoi'
            )
        ]);
        
        // Mettre à jour la validation lorsque la case à cocher change
        envoyerImmediatementSwitch.addEventListener('change', () => {
            validator.validateField('datePlanification');
            validator.validateField('heurePlanification');
        });
    }
    
    return validator;
}

// Validation spécifique pour les barèmes
function setupBaremeValidation() {
    const validator = new FormValidator('baremeForm');
    
    validator.addValidator('id_type_membre', [
        ValidationRules.required('Veuillez sélectionner un type de membre')
    ]);
    
    validator.addValidator('id_montant', [
        ValidationRules.required('Veuillez indiquer un montant'),
        ValidationRules.numeric('Le montant doit être un nombre'),
        ValidationRules.positiveNumber('Le montant doit être supérieur à zéro')
    ]);
    
    // Validation pour les boutons radio de périodicité
    validator.addValidator('periodicite_mensuelle', [
        ValidationRules.custom(
            () => document.querySelector('input[name="periodicite"]:checked') !== null,
            'Veuillez sélectionner une périodicité'
        )
    ]);
    
    validator.addValidator('id_date_debut_validite', [
        ValidationRules.required('La date de début de validité est obligatoire'),
        ValidationRules.date('Veuillez entrer une date valide')
    ]);
    
    validator.addValidator('id_date_fin_validite', [
        ValidationRules.date('Veuillez entrer une date valide'),
        ValidationRules.dateAfter('id_date_debut_validite', 'La date de fin doit être postérieure à la date de début')
    ]);
    
    return validator;
}

// Initialiser la validation lors du chargement de la page
document.addEventListener('DOMContentLoaded', function() {
    // Détecter le type de formulaire par son ID
    if (document.getElementById('cotisationForm')) {
        setupCotisationValidation();
    } else if (document.getElementById('paiementForm')) {
        setupPaiementValidation();
    } else if (document.getElementById('rappelForm')) {
        setupRappelValidation();
    } else if (document.getElementById('baremeForm')) {
        setupBaremeValidation();
    }
});