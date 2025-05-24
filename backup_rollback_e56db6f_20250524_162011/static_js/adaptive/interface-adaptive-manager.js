/**
 * Interface adaptative avancée - Intégration avec contraintes intelligentes
 * Fichier: static/js/cotisations/adaptive/interface-adaptive-manager.js
 */
const InterfaceAdaptativeManager = (function() {
    
    // Configuration et état global
    let state = {
        currentType: 'email',
        currentNiveau: 1,
        currentTemplate: null,
        constraints: null,
        availableTemplates: [],
        previewMode: 'auto',
        animations: true,
        cotisationId: null,
        // Intégration avec contraintes intelligentes
        contraintesManager: null,
        validationActive: true
    };
    
    // Cache des éléments DOM
    let elements = {};
    
    // Timers pour debouncing
    let timers = {
        validation: null,
        preview: null,
        cascade: null
    };
    
    /**
     * Initialisation de l'interface adaptative
     */
    function init() {
        console.log('🎨 Initialisation de l\'interface adaptative avancée');
        
        // Vérifier si les contraintes intelligentes sont disponibles
        if (typeof ContraintesIntelligentesManager !== 'undefined') {
            state.contraintesManager = ContraintesIntelligentesManager;
            console.log('✅ Contraintes intelligentes détectées et intégrées');
        }
        
        // Cache des éléments DOM
        cacheElements();
        
        // Créer l'interface moderne
        createModernInterface();
        
        // Configurer les gestionnaires d'événements
        setupAdvancedEventListeners();
        
        // Initialiser l'état
        initializeState();
        
        // Charger l'interface initiale
        loadInitialInterface();
        
        // Intégrer avec les contraintes existantes
        integrateWithConstraints();
        
        console.log('✅ Interface adaptative initialisée');
    }
    
    /**
     * Cache les éléments DOM pour performance optimale
     */
    function cacheElements() {
        elements = {
            // Éléments de formulaire principaux (compatibilité avec l'existant)
            form: document.getElementById('rappelAjaxForm') || 
                  document.getElementById('rappelForm') ||
                  document.querySelector('form[data-type="rappel"]'),
            typeSelect: document.getElementById('formTypeRappel') || 
                       document.getElementById('id_type_rappel'),
            niveauInput: document.getElementById('formNiveau') || 
                        document.getElementById('id_niveau'),
            contenuTextarea: document.getElementById('formContenu') || 
                           document.getElementById('id_contenu'),
            sujetInput: document.getElementById('formSujet') || 
                       document.getElementById('id_sujet'),
            
            // Éléments contraintes intelligentes existants
            constraintsPanel: document.getElementById('contraintes-panel'),
            validationResults: document.getElementById('validation-results'),
            
            // Conteneurs pour interface adaptative
            mainContainer: document.querySelector('.container-fluid') || document.body,
            formContainer: null, // Sera créé dynamiquement
            selectorContainer: null,
            previewContainer: null,
            toolbarContainer: null
        };
        
        // Récupérer l'ID de cotisation
        state.cotisationId = elements.form?.dataset.cotisationId || 
                            getCurrentCotisationId() ||
                            getFromURL();
    }
    
    /**
     * Intégre avec le système de contraintes intelligentes existant
     */
    function integrateWithConstraints() {
        if (!state.contraintesManager) return;
        
        // Synchroniser les événements avec les contraintes
        document.addEventListener('typeRappelChanged', handleTypeChangedFromConstraints);
        document.addEventListener('validationUpdated', handleValidationFromConstraints);
        document.addEventListener('templateApplied', handleTemplateFromConstraints);
        
        // Écouter les changements de l'interface adaptative
        document.addEventListener('adaptiveTypeSelected', (e) => {
            if (state.contraintesManager.chargerContraintes) {
                state.contraintesManager.chargerContraintes(e.detail.type);
            }
        });
        
        document.addEventListener('adaptiveContentChanged', (e) => {
            if (state.contraintesManager.validerContenu && state.validationActive) {
                state.contraintesManager.validerContenu();
            }
        });
    }
    
    /**
     * Gère les changements de type venant des contraintes
     */
    function handleTypeChangedFromConstraints(event) {
        const newType = event.detail.type;
        if (newType !== state.currentType) {
            state.currentType = newType;
            updateTypeSelection(newType);
            loadCompatibleTemplates();
        }
    }
    
    /**
     * Gère les mises à jour de validation
     */
    function handleValidationFromConstraints(event) {
        const validationData = event.detail;
        updateValidationDisplay(validationData);
    }
    
    /**
     * Crée l'interface moderne adaptative intégrée
     */
    function createModernInterface() {
        // Vérifier si l'interface existe déjà
        if (document.getElementById('adaptive-interface')) {
            console.log('🔄 Interface adaptative déjà présente, mise à jour...');
            updateExistingInterface();
            return;
        }
        
        // Créer la structure principale
        createMainLayout();
        
        // Créer le sélecteur en cascade
        createCascadeSelector();
        
        // Créer la grille de templates intégrée
        createTemplateGridIntegrated();
        
        // Créer la prévisualisation en temps réel
        createLivePreviewIntegrated();
        
        // Créer la barre d'outils
        createToolbar();
        
        // Créer la barre de statut intégrée
        createStatusBarIntegrated();
        
        // Ajouter les styles CSS
        injectModernStyles();
        
        console.log('🎨 Interface moderne créée et intégrée');
    }
    
    /**
     * Crée la structure principale de l'interface intégrée
     */
    function createMainLayout() {
        // Conteneur principal adaptatif
        const mainLayout = document.createElement('div');
        mainLayout.id = 'adaptive-interface';
        mainLayout.className = 'adaptive-interface-container';
        mainLayout.innerHTML = `
            <div class="adaptive-header">
                <div class="interface-title">
                    <h5 class="mb-0">
                        <i class="fas fa-magic text-primary"></i>
                        Assistant de création de rappel intelligent
                    </h5>
                    <small class="text-muted">Interface adaptative avec contraintes intelligentes</small>
                </div>
                <div class="interface-controls">
                    <div class="btn-group btn-group-sm">
                        <button type="button" class="btn btn-outline-secondary" id="btn-toggle-preview" 
                                title="Activer/Désactiver la prévisualisation">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button type="button" class="btn btn-outline-secondary" id="btn-toggle-validation" 
                                title="Activer/Désactiver la validation temps réel">
                            <i class="fas fa-shield-alt"></i>
                        </button>
                        <button type="button" class="btn btn-outline-secondary" id="btn-toggle-animations" 
                                title="Activer/Désactiver les animations">
                            <i class="fas fa-play"></i>
                        </button>
                        <button type="button" class="btn btn-outline-secondary" id="btn-shortcuts" 
                                title="Afficher les raccourcis">
                            <i class="fas fa-keyboard"></i>
                        </button>
                        <button type="button" class="btn btn-outline-secondary" id="btn-fullscreen" 
                                title="Mode plein écran">
                            <i class="fas fa-expand"></i>
                        </button>
                    </div>
                </div>
            </div>
            
            <div class="adaptive-body">
                <div class="row h-100">
                    <!-- Colonne de sélection (gauche) -->
                    <div class="col-lg-4 adaptive-selector-column">
                        <div id="cascade-selector-container" class="h-100"></div>
                    </div>
                    
                    <!-- Colonne principale (centre) -->
                    <div class="col-lg-8 adaptive-main-column">
                        <div class="row h-100">
                            <!-- Formulaire avec contraintes intégrées -->
                            <div class="col-12 adaptive-form-section">
                                <div id="form-container" class="h-100"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Prévisualisation flottante intégrée -->
            <div id="floating-preview" class="floating-preview">
                <div class="floating-preview-header">
                    <div class="preview-controls">
                        <div class="preview-type-indicator">
                            <div class="type-icon">📧</div>
                            <div class="type-info">
                                <div class="type-name">Email</div>
                            </div>
                        </div>
                        <div class="preview-actions">
                            <button type="button" class="btn btn-sm btn-link text-light" id="btn-dock-preview" 
                                    title="Ancrer/Détacher la prévisualisation">
                                <i class="fas fa-external-link-alt"></i>
                            </button>
                            <button type="button" class="btn btn-sm btn-link text-light" id="btn-close-preview">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                    </div>
                    <div class="preview-stats">
                        <span class="stat-chars">0 caractères</span>
                        <span class="stat-validation">✅ Valide</span>
                        <span class="stat-cost">~0.05€</span>
                    </div>
                </div>
                <div class="floating-preview-body" id="live-preview-content">
                    <div class="text-center text-muted">
                        <i class="fas fa-eye fa-2x mb-2"></i>
                        <p>Saisissez du contenu pour voir l'aperçu</p>
                    </div>
                </div>
                <div class="floating-preview-footer">
                    <div class="preview-tabs">
                        <button class="preview-tab active" data-tab="rendered">Rendu</button>
                        <button class="preview-tab" data-tab="source">Source</button>
                        <button class="preview-tab" data-tab="analysis">Analyse</button>
                    </div>
                </div>
            </div>
        `;
        
        // Insérer avant le formulaire existant ou le conteneur de contraintes
        const insertTarget = elements.constraintsPanel || elements.form || document.querySelector('.card-body');
        if (insertTarget) {
            insertTarget.parentNode.insertBefore(mainLayout, insertTarget);
            
            // Déplacer le formulaire et les contraintes dans le nouveau conteneur
            const formContainer = mainLayout.querySelector('#form-container');
            
            // Préserver l'ordre: contraintes puis formulaire
            if (elements.constraintsPanel) {
                formContainer.appendChild(elements.constraintsPanel);
                elements.constraintsPanel.style.marginBottom = '1rem';
            }
            if (elements.form) {
                formContainer.appendChild(elements.form);
            }
            
            // Cacher les éléments originaux qui seront remplacés par l'interface cascade
            hideOriginalElements();
        }
        
        // Mettre à jour les références
        elements.formContainer = formContainer;
        elements.selectorContainer = mainLayout.querySelector('#cascade-selector-container');
        elements.previewContainer = mainLayout.querySelector('#floating-preview');
    }
    
    /**
     * Crée le sélecteur en cascade moderne intégré
     */
    function createCascadeSelector() {
        if (!elements.selectorContainer) return;
        
        const cascadeHTML = `
            <div class="cascade-selector">
                <!-- Étape 1: Sélection du type avec contraintes -->
                <div class="cascade-step active" data-step="1">
                    <div class="step-header">
                        <div class="step-number">1</div>
                        <div class="step-info">
                            <h6 class="step-title">Type de rappel</h6>
                            <small class="step-description">Choisissez le canal avec contraintes adaptées</small>
                        </div>
                    </div>
                    <div class="step-content">
                        <div class="type-selector-grid">
                            <div class="type-option" data-type="email">
                                <div class="type-icon">📧</div>
                                <div class="type-info">
                                    <div class="type-name">Email</div>
                                    <div class="type-description">Courrier électronique</div>
                                </div>
                                <div class="type-stats">
                                    <small class="text-muted">200-5000 chars</small>
                                    <div class="type-constraints">
                                        <span class="badge badge-info">Sujet requis</span>
                                        <span class="badge badge-secondary">HTML autorisé</span>
                                    </div>
                                </div>
                            </div>
                            <div class="type-option" data-type="sms">
                                <div class="type-icon">📱</div>
                                <div class="type-info">
                                    <div class="type-name">SMS</div>
                                    <div class="type-description">Message texte</div>
                                </div>
                                <div class="type-stats">
                                    <small class="text-muted">Max 160 chars</small>
                                    <div class="type-constraints">
                                        <span class="badge badge-warning">Pas de sujet</span>
                                        <span class="badge badge-danger">Texte seul</span>
                                    </div>
                                </div>
                            </div>
                            <div class="type-option" data-type="courrier">
                                <div class="type-icon">📮</div>
                                <div class="type-info">
                                    <div class="type-name">Courrier</div>
                                    <div class="type-description">Postal officiel</div>
                                </div>
                                <div class="type-stats">
                                    <small class="text-muted">300-3000 chars</small>
                                    <div class="type-constraints">
                                        <span class="badge badge-primary">Format lettre</span>
                                        <span class="badge badge-info">Mentions légales</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <!-- Contraintes en temps réel -->
                        <div class="constraints-summary" id="type-constraints-summary" style="display: none;">
                            <h6 class="text-muted mt-3">Contraintes pour ce type :</h6>
                            <div id="constraints-list"></div>
                        </div>
                    </div>
                </div>
                
                <!-- Étape 2: Sélection du niveau -->
                <div class="cascade-step" data-step="2">
                    <div class="step-header">
                        <div class="step-number">2</div>
                        <div class="step-info">
                            <h6 class="step-title">Niveau d'urgence</h6>
                            <small class="step-description">Définissez le ton avec validation adaptée</small>
                        </div>
                    </div>
                    <div class="step-content">
                        <div class="niveau-selector">
                            <div class="niveau-slider-container">
                                <input type="range" class="niveau-slider" id="niveau-range" 
                                       min="1" max="5" value="1" step="1">
                                <div class="niveau-labels">
                                    <span class="niveau-label" data-niveau="1">Standard</span>
                                    <span class="niveau-label" data-niveau="2">Modéré</span>
                                    <span class="niveau-label" data-niveau="3">Urgent</span>
                                    <span class="niveau-label" data-niveau="4">Critique</span>
                                    <span class="niveau-label" data-niveau="5">Formel</span>
                                </div>
                            </div>
                            <div class="niveau-description">
                                <div class="niveau-info" id="niveau-info">
                                    <h6 id="niveau-title">Standard</h6>
                                    <p id="niveau-desc">Rappel poli et cordial pour un premier contact</p>
                                    <div class="niveau-impact">
                                        <small class="text-muted">Impact sur les contraintes :</small>
                                        <ul id="niveau-constraints-impact" class="small mt-1">
                                            <li>Longueur recommandée : 200-800 caractères</li>
                                            <li>Ton professionnel mais cordial</li>
                                        </ul>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Étape 3: Sélection du template avec validation -->
                <div class="cascade-step" data-step="3">
                    <div class="step-header">
                        <div class="step-number">3</div>
                        <div class="step-info">
                            <h6 class="step-title">Template validé</h6>
                            <small class="step-description">Templates conformes aux contraintes</small>
                        </div>
                    </div>
                    <div class="step-content">
                        <div class="template-selector" id="template-selector">
                            <div class="text-center text-muted">
                                <i class="fas fa-arrow-up fa-2x mb-2"></i>
                                <p>Sélectionnez d'abord un type et un niveau</p>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Navigation avec validation -->
                <div class="cascade-navigation">
                    <button type="button" class="btn btn-outline-secondary" id="btn-prev-step" disabled>
                        <i class="fas fa-chevron-left"></i> Précédent
                    </button>
                    <div class="navigation-validation" id="navigation-validation">
                        <small class="text-muted">Toutes les contraintes sont respectées</small>
                    </div>
                    <button type="button" class="btn btn-primary" id="btn-next-step">
                        Suivant <i class="fas fa-chevron-right"></i>
                    </button>
                </div>
            </div>
        `;
        
        elements.selectorContainer.innerHTML = cascadeHTML;
        
        // Configurer les gestionnaires d'événements pour la cascade
        setupCascadeEventListeners();
    }
    
    /**
     * Charge les templates compatibles avec validation intégrée
     */
    async function loadCompatibleTemplates() {
        if (!state.currentType || !state.currentNiveau) return;
        
        const templateSelector = document.getElementById('template-selector');
        if (!templateSelector) return;
        
        // Animation de chargement
        templateSelector.innerHTML = `
            <div class="text-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Chargement...</span>
                </div>
                <p class="mt-2 text-muted">Chargement des templates validés...</p>
            </div>
        `;
        
        try {
            const params = new URLSearchParams({
                type_rappel: state.currentType,
                niveau: state.currentNiveau,
                cotisation_id: state.cotisationId || '',
                validate_constraints: 'true' // Nouvelle validation intégrée
            });
            
            const response = await fetch(`/cotisations/api/rappel-templates/?${params}`);
            const data = await response.json();
            
            if (data.success && data.templates.length > 0) {
                state.availableTemplates = data.templates;
                renderTemplateCardsValidated(data.templates);
            } else {
                showNoValidTemplatesMessage();
            }
        } catch (error) {
            console.error('❌ Erreur chargement templates:', error);
            showTemplateLoadError();
        }
    }
    
    /**
     * Affiche les templates avec validation intégrée
     */
    function renderTemplateCardsValidated(templates) {
        const templateSelector = document.getElementById('template-selector');
        if (!templateSelector) return;
        
        const cardsHTML = templates.map((template, index) => {
            const validationStatus = template.validation_status || 'valid';
            const validationClass = validationStatus === 'valid' ? 'border-success' : 
                                  validationStatus === 'warning' ? 'border-warning' : 'border-danger';
            const validationIcon = validationStatus === 'valid' ? '✅' : 
                                 validationStatus === 'warning' ? '⚠️' : '❌';
            
            return `
                <div class="template-card ${index === 0 ? 'recommended' : ''} ${validationClass}" 
                     data-template-id="${template.id}"
                     data-validation="${validationStatus}"
                     style="animation-delay: ${index * 100}ms">
                    <div class="template-card-header">
                        <div class="template-title">${template.nom}</div>
                        <div class="template-validation">
                            ${validationIcon} ${validationStatus === 'valid' ? 'Conforme' : 
                                                validationStatus === 'warning' ? 'Attention' : 'Non conforme'}
                        </div>
                        ${index === 0 ? '<div class="recommended-badge">Recommandé</div>' : ''}
                    </div>
                    <div class="template-card-body">
                        <div class="template-preview">
                            ${template.contenu_genere ? 
                              template.contenu_genere.substring(0, 120) + '...' : 
                              template.contenu.substring(0, 120) + '...'}
                        </div>
                        <div class="template-stats">
                            <span class="stat-item">
                                <i class="fas fa-font"></i>
                                ${template.contenu.length} chars
                            </span>
                            <span class="stat-item">
                                <i class="fas fa-layer-group"></i>
                                Niveaux ${template.niveau_min}-${template.niveau_max}
                            </span>
                            ${template.constraint_score ? `
                                <span class="stat-item">
                                    <i class="fas fa-star"></i>
                                    Score: ${template.constraint_score}%
                                </span>
                            ` : ''}
                        </div>
                        ${template.validation_warnings ? `
                            <div class="template-warnings">
                                <small class="text-warning">
                                    <i class="fas fa-exclamation-triangle"></i>
                                    ${template.validation_warnings.join(', ')}
                                </small>
                            </div>
                        ` : ''}
                    </div>
                    <div class="template-card-footer">
                        <button type="button" class="btn btn-sm btn-outline-primary btn-preview-template">
                            <i class="fas fa-eye"></i> Aperçu
                        </button>
                        <button type="button" class="btn btn-sm btn-primary btn-select-template" 
                                ${validationStatus === 'error' ? 'disabled' : ''}>
                            <i class="fas fa-check"></i> Utiliser
                        </button>
                    </div>
                </div>
            `;
        }).join('');
        
        templateSelector.innerHTML = `
            <div class="template-cards-container">
                ${cardsHTML}
                <div class="templates-validation-summary mt-3">
                    <small class="text-muted">
                        <i class="fas fa-info-circle"></i>
                        ${templates.filter(t => t.validation_status === 'valid').length} template(s) entièrement conforme(s)
                    </small>
                </div>
            </div>
        `;
        
        // Configurer les gestionnaires d'événements
        setupTemplateCardEvents();
        
        // Animation d'apparition
        if (state.animations) {
            setTimeout(() => {
                templateSelector.querySelectorAll('.template-card').forEach(card => {
                    card.classList.add('fade-in');
                });
            }, 100);
        }
    }
    
    // ==================== ÉVÉNEMENTS INTÉGRÉS ====================
    
    /**
     * Configure les gestionnaires d'événements pour la cascade
     */
    function setupCascadeEventListeners() {
        // Sélection du type avec contraintes
        const typeOptions = document.querySelectorAll('.type-option');
        typeOptions.forEach(option => {
            option.addEventListener('click', handleTypeSelectionIntegrated);
        });
        
        // Slider de niveau avec validation
        const niveauSlider = document.getElementById('niveau-range');
        if (niveauSlider) {
            niveauSlider.addEventListener('input', handleNiveauChangeIntegrated);
            niveauSlider.addEventListener('change', handleNiveauChangeComplete);
        }
        
        // Navigation des étapes avec validation
        const btnPrev = document.getElementById('btn-prev-step');
        const btnNext = document.getElementById('btn-next-step');
        
        if (btnPrev) btnPrev.addEventListener('click', () => navigateStep(-1));
        if (btnNext) btnNext.addEventListener('click', () => navigateStepWithValidation(1));
        
        // Raccourcis clavier pour navigation
        document.addEventListener('keydown', handleKeyboardNavigation);
    }
    
    /**
     * Gère la sélection du type avec contraintes intégrées
     */
    function handleTypeSelectionIntegrated(event) {
        const typeOption = event.currentTarget;
        const selectedType = typeOption.dataset.type;
        
        // Animation de sélection
        document.querySelectorAll('.type-option').forEach(opt => {
            opt.classList.remove('selected');
        });
        typeOption.classList.add('selected');
        
        // Animation de transition
        if (state.animations) {
            typeOption.style.transform = 'scale(0.95)';
            setTimeout(() => {
                typeOption.style.transform = 'scale(1)';
            }, 150);
        }
        
        // Mettre à jour l'état
        state.currentType = selectedType;
        
        // Charger les contraintes pour ce type (intégration)
        loadTypeConstraintsIntegrated(selectedType);
        
        // Notifier le changement pour les contraintes intelligentes
        document.dispatchEvent(new CustomEvent('adaptiveTypeSelected', {
            detail: { type: selectedType }
        }));
        
        // Passer à l'étape suivante automatiquement
        setTimeout(() => {
            navigateStep(1);
        }, state.animations ? 300 : 0);
        
        console.log(`🎯 Type sélectionné: ${selectedType}`);
    }
    
    /**
     * Charge les contraintes avec intégration
     */
    async function loadTypeConstraintsIntegrated(type) {
        try {
            const params = new URLSearchParams({
                type_rappel: type,
                jours_retard: 0,
                nb_destinataires: 1
            });
            
            const response = await fetch(`/cotisations/api/contraintes/?${params}`);
            const data = await response.json();
            
            if (data.success) {
                state.constraints = data.contraintes;
                updateConstraintsDisplayIntegrated(data.contraintes);
            }
        } catch (error) {
            console.error('❌ Erreur chargement contraintes:', error);
        }
    }
    
    /**
     * Met à jour l'affichage des contraintes dans l'interface cascade
     */
    function updateConstraintsDisplayIntegrated(constraints) {
        const summaryElement = document.getElementById('type-constraints-summary');
        const listElement = document.getElementById('constraints-list');
        
        if (!summaryElement || !listElement || !constraints) return;
        
        // Construire la liste des contraintes
        const constraintsList = [];
        
        if (constraints.longueur_min && constraints.longueur_max) {
            constraintsList.push(`Longueur: ${constraints.longueur_min}-${constraints.longueur_max} caractères`);
        }
        
        if (constraints.sujet_requis === true) {
            constraintsList.push('Sujet obligatoire');
        } else if (constraints.sujet_requis === false) {
            constraintsList.push('Pas de sujet');
        }
        
        if (constraints.html_autorise) {
            constraintsList.push('HTML autorisé');
        } else {
            constraintsList.push('Texte seul');
        }
        
        if (constraints.emojis_autorises === false) {
            constraintsList.push('Pas d\'emojis');
        }
        
        // Afficher les contraintes
        listElement.innerHTML = constraintsList.map(c => `
            <span class="badge badge-info mr-1 mb-1">${c}</span>
        `).join('');
        
        summaryElement.style.display = 'block';
        
        console.log('📊 Contraintes affichées dans l\'interface cascade');
    }
    
    // ==================== FONCTIONS UTILITAIRES INTÉGRÉES ====================
    
    function getCurrentCotisationId() {
        const urlParts = window.location.pathname.split('/');
        const cotisationIndex = urlParts.indexOf('cotisations');
        return cotisationIndex !== -1 ? urlParts[cotisationIndex + 1] : null;
    }
    
    function getFromURL() {
        const match = window.location.pathname.match(/cotisations\/(\d+)/);
        return match ? match[1] : null;
    }
    
    function hideOriginalElements() {
        // Cacher les éléments de l'interface originale qui sont remplacés
        const elementsToHide = [
            elements.typeSelect?.closest('.form-group'),
            elements.niveauInput?.closest('.form-group'),
            document.getElementById('templateDefault')?.closest('.btn-group')
        ];
        
        elementsToHide.forEach(element => {
            if (element) {
                element.style.display = 'none';
            }
        });
    }
    
    function setupAdvancedEventListeners() {
        // Gestionnaires pour les contrôles de l'interface
        const btnTogglePreview = document.getElementById('btn-toggle-preview');
        const btnToggleValidation = document.getElementById('btn-toggle-validation');
        const btnToggleAnimations = document.getElementById('btn-toggle-animations');
        const btnShortcuts = document.getElementById('btn-shortcuts');
        const btnFullscreen = document.getElementById('btn-fullscreen');
        
        if (btnTogglePreview) btnTogglePreview.addEventListener('click', togglePreview);
        if (btnToggleValidation) btnToggleValidation.addEventListener('click', toggleValidation);
        if (btnToggleAnimations) btnToggleAnimations.addEventListener('click', toggleAnimations);
        if (btnShortcuts) btnShortcuts.addEventListener('click', showShortcutsModal);
        if (btnFullscreen) btnFullscreen.addEventListener('click', toggleFullscreen);
    }
    
    function toggleValidation() {
        state.validationActive = !state.validationActive;
        
        const btn = document.getElementById('btn-toggle-validation');
        if (btn) {
            btn.classList.toggle('active', state.validationActive);
            btn.title = state.validationActive ? 
                'Désactiver la validation temps réel' : 
                'Activer la validation temps réel';
        }
        
        console.log(`🛡️ Validation temps réel: ${state.validationActive ? 'activée' : 'désactivée'}`);
    }
    
    // ==================== API PUBLIQUE INTÉGRÉE ====================
    
    // API publique
    return {
        init,
        navigateStep,
        applyTemplate,
        togglePreview,
        toggleValidation,
        getCurrentState: () => ({ ...state }),
        // Méthodes d'intégration
        integrateWithExisting,
        syncWithConstraints: integrateWithConstraints,
        updateFromExternal: handleTypeChangedFromConstraints
    };
    
    /**
     * Méthode d'intégration avec l'existant
     */
    function integrateWithExisting() {
        // Synchroniser avec les valeurs existantes du formulaire
        if (elements.typeSelect?.value) {
            state.currentType = elements.typeSelect.value;
        }
        if (elements.niveauInput?.value) {
            state.currentNiveau = parseInt(elements.niveauInput.value);
        }
        
        // Déclencher les mises à jour
        if (state.currentType) {
            updateTypeSelection(state.currentType);
            loadTypeConstraintsIntegrated(state.currentType);
        }
        
        console.log('🔗 Intégration avec l\'existant terminée');
    }
})();

// Auto-initialisation avec vérification de compatibilité
document.addEventListener('DOMContentLoaded', function() {
    // Attendre que les contraintes intelligentes soient prêtes
    const initWhenReady = () => {
        if (typeof ContraintesIntelligentesManager !== 'undefined' || 
            document.querySelector('[data-constraints-ready]')) {
            InterfaceAdaptativeManager.init();
        } else {
            setTimeout(initWhenReady, 100);
        }
    };
    
    setTimeout(initWhenReady, 100);
});