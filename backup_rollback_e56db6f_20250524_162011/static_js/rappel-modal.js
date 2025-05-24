/**
 * Script spécifique pour appliquer les améliorations visuelles au modal de rappel
 * 
 * Ce script doit être inclus séparément pour garantir que les boutons de modèle
 * dans le modal sont correctement mis en évidence, indépendamment de rappel-ajax.js
 */
document.addEventListener('DOMContentLoaded', function() {
    // Identifier le modal de rappel
    const rappelModal = document.getElementById('rappelModal');
    
    if (!rappelModal) {
        console.log('Modal de rappel non trouvé, le script ne sera pas appliqué');
        return;
    }
    
    // Ajouter les styles CSS si nécessaire
    if (!document.getElementById('template-modal-style')) {
        const style = document.createElement('style');
        style.id = 'template-modal-style';
        style.textContent = `
            .btn-template {
                transition: all 0.3s ease;
            }
            .btn-template-active {
                background-color: #28a745 !important;
                color: white !important;
                border-color: #28a745 !important;
                box-shadow: 0 0 0 0.2rem rgba(40, 167, 69, 0.25);
            }
            .btn-template-inactive {
                background-color: #f8f9fa;
                color: #6c757d;
                border-color: #ced4da;
            }
        `;
        document.head.appendChild(style);
    }
    
    // Fonction pour configurer les boutons du modal
    function setupModalTemplateButtons() {
        // Sélectionner spécifiquement les boutons dans le modal
        const modalTemplateDefaultBtn = rappelModal.querySelector('#templateDefault');
        const modalTemplateUrgentBtn = rappelModal.querySelector('#templateUrgent');
        const modalTemplateFormalBtn = rappelModal.querySelector('#templateFormal');
        const modalContenuTextarea = rappelModal.querySelector('[name="contenu"]');
        
        // Si les éléments n'existent pas, sortir
        if (!modalTemplateDefaultBtn || !modalTemplateUrgentBtn || !modalTemplateFormalBtn || !modalContenuTextarea) {
            console.log('Éléments de template du modal non trouvés');
            return;
        }
        
        // Fonction utilitaire pour mettre à jour les styles des boutons
        function updateTemplateButtonStyles(activeButton) {
            const buttons = [modalTemplateDefaultBtn, modalTemplateUrgentBtn, modalTemplateFormalBtn];
            
            buttons.forEach(button => {
                // Ajouter la classe de base
                button.classList.add('btn-template');
                
                // Appliquer la classe active ou inactive
                if (button === activeButton) {
                    button.classList.add('btn-template-active');
                    button.classList.remove('btn-template-inactive', 'btn-outline-secondary');
                } else {
                    button.classList.remove('btn-template-active', 'btn-outline-secondary');
                    button.classList.add('btn-template-inactive');
                }
            });
        }
        
        // Fonction pour formater un template avec date limite
        function formatTemplate(template, dateLimite) {
            if (!template) return '';
            
            let formattedTemplate = template;
            
            // Remplacer les phrases génériques par des versions avec date limite
            if (template.includes("procéder au règlement dans les meilleurs délais")) {
                formattedTemplate = template.replace(
                    "procéder au règlement dans les meilleurs délais", 
                    `procéder au règlement avant le ${dateLimite}`
                );
            } else if (template.includes("sous 7 jours")) {
                formattedTemplate = template.replace(
                    "sous 7 jours", 
                    `avant le ${dateLimite}`
                );
            } else if (template.includes("dans un délai de 15 jours")) {
                formattedTemplate = template.replace(
                    "dans un délai de 15 jours", 
                    `dans un délai de 15 jours, soit au plus tard le ${dateLimite}`
                );
            }
            
            return formattedTemplate;
        }
        
        // Vérifier quel modèle est actuellement utilisé
        function checkExistingTemplateContent() {
            const content = modalContenuTextarea.value;
            
            if (!content) return;
            
            if (content.includes('RAPPEL URGENT')) {
                updateTemplateButtonStyles(modalTemplateUrgentBtn);
            } else if (content.includes('Veuillez agréer')) {
                updateTemplateButtonStyles(modalTemplateFormalBtn);
            } else if (content.includes('Nous vous rappelons')) {
                updateTemplateButtonStyles(modalTemplateDefaultBtn);
            }
        }
        
        // Configurer le bouton de modèle standard
        modalTemplateDefaultBtn.addEventListener('click', function() {
            // Récupérer le contenu actuel pour préserver les variables personnalisées
            let template = modalContenuTextarea.value;
            
            // Si pas encore de contenu ou modèle différent, utiliser le modèle standard
            if (!template.includes('Nous vous rappelons')) {
                template = window.rappelManager?.options.templates.standard || 
                           `Cher/Chère {prenom},

Nous vous rappelons que votre cotisation (réf. {reference}) d'un montant restant dû de {montant} est arrivée à échéance le {date_echeance}.

Nous vous remercions de bien vouloir procéder au règlement dans les meilleurs délais.

Cordialement,
L'équipe de l'association`;
            }
            
            // Calculer la date limite
            const dateLimite = new Date();
            dateLimite.setDate(dateLimite.getDate() + 7);
            const dateLimiteStr = dateLimite.toLocaleDateString('fr-FR');
            
            // Mettre à jour le textarea
            modalContenuTextarea.value = formatTemplate(template, dateLimiteStr);
            
            // Mettre à jour les styles des boutons
            updateTemplateButtonStyles(this);
        });
        
        // Configurer le bouton de modèle urgent
        modalTemplateUrgentBtn.addEventListener('click', function() {
            // Récupérer le template depuis l'instance rappelManager si disponible
            let template = window.rappelManager?.options.templates.urgent || 
                           `Cher/Chère {prenom},

RAPPEL URGENT : Votre cotisation (réf. {reference}) d'un montant de {montant} est en retard de paiement depuis le {date_echeance}.

Afin d'éviter toute procédure supplémentaire, nous vous invitons à régulariser cette situation sous 7 jours.

Pour toute question ou difficulté, n'hésitez pas à nous contacter rapidement.

Cordialement,
L'équipe de l'association`;
            
            // Calculer la date limite
            const dateLimite = new Date();
            dateLimite.setDate(dateLimite.getDate() + 5);
            const dateLimiteStr = dateLimite.toLocaleDateString('fr-FR');
            
            // Mettre à jour le textarea
            modalContenuTextarea.value = formatTemplate(template, dateLimiteStr);
            
            // Mettre à jour les styles des boutons
            updateTemplateButtonStyles(this);
        });
        
        // Configurer le bouton de modèle formel
        modalTemplateFormalBtn.addEventListener('click', function() {
            // Récupérer le template depuis l'instance rappelManager si disponible
            let template = window.rappelManager?.options.templates.formel || 
                           `Madame, Monsieur,

Nous constatons qu'à ce jour, votre cotisation référencée {reference}, d'un montant de {montant} et échue le {date_echeance}, demeure impayée.

Conformément à nos statuts, nous vous prions de bien vouloir procéder au règlement de cette somme dans un délai de 15 jours à compter de la réception du présent courrier.

À défaut de paiement dans le délai imparti, nous nous verrons contraints d'appliquer les mesures prévues par le règlement intérieur.

Veuillez agréer, Madame, Monsieur, l'expression de nos salutations distinguées.

Le Trésorier
Association XYZ`;
            
            // Calculer la date limite
            const dateLimite = new Date();
            dateLimite.setDate(dateLimite.getDate() + 15);
            const dateLimiteStr = dateLimite.toLocaleDateString('fr-FR');
            
            // Mettre à jour le textarea
            modalContenuTextarea.value = formatTemplate(template, dateLimiteStr);
            
            // Mettre à jour les styles des boutons
            updateTemplateButtonStyles(this);
        });
        
        // Vérifier le contenu initial et mettre en évidence le bouton correspondant
        checkExistingTemplateContent();
        
        // Réinitialiser les styles des boutons lorsque le type de rappel change
        const typeRappelSelect = rappelModal.querySelector('[name="type_rappel"]');
        if (typeRappelSelect) {
            typeRappelSelect.addEventListener('change', function() {
                const buttons = [modalTemplateDefaultBtn, modalTemplateUrgentBtn, modalTemplateFormalBtn];
                buttons.forEach(button => {
                    button.classList.remove('btn-template-active', 'btn-template-inactive');
                    button.classList.add('btn-outline-secondary');
                });
                
                // Désactiver le bouton de modèle formel pour les SMS
                if (this.value === 'sms') {
                    modalTemplateFormalBtn.disabled = true;
                } else {
                    modalTemplateFormalBtn.disabled = false;
                }
            });
        }
    }
    
    // Configurer les boutons lorsque le modal est ouvert
    rappelModal.addEventListener('shown.bs.modal', setupModalTemplateButtons);
    
    // En cas de chargement dynamique du contenu du modal, reconfigurer lorsque le DOM change
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                // Vérifier si les boutons de template existent dans le modal
                const templateButtons = rappelModal.querySelectorAll('#templateDefault, #templateUrgent, #templateFormal');
                if (templateButtons.length > 0) {
                    setupModalTemplateButtons();
                }
            }
        });
    });
    
    // Observer les changements dans le modal
    observer.observe(rappelModal, { childList: true, subtree: true });
});