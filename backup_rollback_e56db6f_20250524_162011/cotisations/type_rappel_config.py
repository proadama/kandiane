"""
Configuration des contraintes intelligentes par type de rappel.
Définit les règles métier, validations et comportements pour chaque type.
"""

from django.utils.translation import gettext_lazy as _
import re


class TypeRappelConfig:
    """
    Configuration centralisée des contraintes par type de rappel.
    """
    
    # ==================== CONTRAINTES EMAIL ====================
    EMAIL_CONFIG = {
        'nom': 'Email',
        'icone': '📧',
        'couleur': '#0d6efd',  # Bleu Bootstrap
        'description': _('Rappel par courrier électronique'),
        
        # Contraintes de contenu
        'longueur_min': 200,
        'longueur_max': 5000,
        'longueur_optimale': 800,
        
        # Champs obligatoires
        'sujet_obligatoire': True,
        'contenu_obligatoire': True,
        
        # Formats autorisés
        'html_permis': True,
        'formatage_riche': True,
        'emojis_autorises': True,
        'liens_autorises': True,
        
        # Variables spécialisées
        'variables_speciales': [
            'lien_paiement', 'signature_html', 'bouton_contact',
            'tracking_pixel', 'lien_desabonnement', 'logo_association'
        ],
        
        # Validation spécifique
        'validation_html': True,
        'validation_liens': True,
        'validation_images': True,
        
        # Règles métier
        'envoi_weekend': True,
        'envoi_nocturne': True,
        'heure_optimale': '09:00',
        'delai_min_entre_envois': 24,  # heures
        
        # Limites système
        'nb_destinataires_max': 1000,
        'taille_max_mb': 10,
        'pieces_jointes_autorisees': True,
        
        # Tracking et analytics
        'tracking_ouverture': True,
        'tracking_clics': True,
        'accuse_reception': False,
    }
    
    # ==================== CONTRAINTES SMS ====================
    SMS_CONFIG = {
        'nom': 'SMS',
        'icone': '📱',
        'couleur': '#198754',  # Vert Bootstrap
        'description': _('Rappel par message texte'),
        
        # Contraintes de contenu strictes
        'longueur_min': 10,
        'longueur_max': 160,
        'longueur_optimale': 140,  # Marge de sécurité
        
        # Champs obligatoires
        'sujet_obligatoire': False,
        'contenu_obligatoire': True,
        
        # Formats interdits
        'html_permis': False,
        'formatage_riche': False,
        'emojis_autorises': True,  # Mais comptent double
        'liens_autorises': True,   # Mais raccourcis uniquement
        
        # Variables spécialisées
        'variables_speciales': [
            'lien_court', 'tel_urgence', 'ref_courte',
            'nom_court', 'montant_simple'
        ],
        
        # Validation spécifique
        'validation_longueur_stricte': True,
        'validation_caracteres_speciaux': True,
        'validation_emojis': True,
        
        # Règles métier strictes
        'envoi_weekend': False,
        'envoi_nocturne': False,
        'heure_debut': '08:00',
        'heure_fin': '20:00',
        'delai_min_entre_envois': 4,  # heures
        
        # Limites système
        'nb_destinataires_max': 100,
        'cout_par_sms': 0.08,  # €
        'pieces_jointes_autorisees': False,
        
        # Tracking limité
        'tracking_ouverture': False,
        'tracking_clics': True,  # Via liens courts
        'accuse_reception': True,
    }
    
    # ==================== CONTRAINTES COURRIER ====================
    COURRIER_CONFIG = {
        'nom': 'Courrier',
        'icone': '📮',
        'couleur': '#6f42c1',  # Violet Bootstrap
        'description': _('Rappel par courrier postal'),
        
        # Contraintes de contenu
        'longueur_min': 300,
        'longueur_max': 3000,
        'longueur_optimale': 1200,
        
        # Champs obligatoires
        'sujet_obligatoire': True,  # Objet de la lettre
        'contenu_obligatoire': True,
        'adresse_obligatoire': True,
        
        # Formats spéciaux
        'html_permis': False,  # Texte brut pour impression
        'formatage_riche': False,
        'emojis_autorises': False,
        'liens_autorises': False,
        
        # Variables spécialisées
        'variables_speciales': [
            'adresse_complete', 'mentions_legales', 'cachet',
            'signature_manuscrite', 'en_tete_officiel', 'date_envoi_courrier'
        ],
        
        # Validation spécifique
        'validation_adresse_postale': True,
        'validation_format_lettre': True,
        'validation_mentions_legales': True,
        
        # Règles métier
        'envoi_weekend': False,  # Pas de distribution weekend
        'envoi_nocturne': False,
        'heure_optimale': '14:00',  # Après collecte postale
        'delai_min_entre_envois': 168,  # 1 semaine
        
        # Limites système
        'nb_destinataires_max': 500,
        'cout_moyen': 1.50,  # € (timbre + papier)
        'pieces_jointes_autorisees': True,
        
        # Tracking postal
        'tracking_ouverture': False,
        'tracking_clics': False,
        'accuse_reception': True,  # Recommandé AR
        'recommande_automatique': True,  # Pour niveau formel
    }
    
    @classmethod
    def get_config(cls, type_rappel):
        """
        Récupère la configuration pour un type de rappel donné.
        """
        configs = {
            'email': cls.EMAIL_CONFIG,
            'sms': cls.SMS_CONFIG,
            'courrier': cls.COURRIER_CONFIG,
        }
        return configs.get(type_rappel.lower(), {})
    
    @classmethod
    def get_all_configs(cls):
        """
        Récupère toutes les configurations disponibles.
        """
        return {
            'email': cls.EMAIL_CONFIG,
            'sms': cls.SMS_CONFIG,
            'courrier': cls.COURRIER_CONFIG,
        }
    
    @classmethod
    def valider_longueur(cls, type_rappel, contenu):
        """
        Valide la longueur du contenu selon le type.
        """
        config = cls.get_config(type_rappel)
        if not config:
            return True, ""
        
        longueur = len(contenu)
        
        # Calcul spécial pour SMS (emojis comptent double)
        if type_rappel.lower() == 'sms':
            # Compter les emojis qui prennent plus de place
            emoji_pattern = re.compile(
                "["
                "\U0001F600-\U0001F64F"  # emoticons
                "\U0001F300-\U0001F5FF"  # symbols & pictographs
                "\U0001F680-\U0001F6FF"  # transport & map symbols
                "\U0001F1E0-\U0001F1FF"  # flags (iOS)
                "\U00002702-\U000027B0"  # dingbats
                "\U000024C2-\U0001F251"
                "]+", flags=re.UNICODE
            )
            emojis = emoji_pattern.findall(contenu)
            longueur_reelle = longueur + len(emojis)  # Chaque emoji compte double
        else:
            longueur_reelle = longueur
        
        # Vérifications
        if longueur_reelle < config['longueur_min']:
            return False, _("Contenu trop court (minimum {} caractères)").format(config['longueur_min'])
        
        if longueur_reelle > config['longueur_max']:
            return False, _("Contenu trop long (maximum {} caractères)").format(config['longueur_max'])
        
        return True, ""
    
    @classmethod
    def valider_sujet(cls, type_rappel, sujet):
        """
        Valide le sujet selon le type.
        """
        config = cls.get_config(type_rappel)
        if not config:
            return True, ""
        
        if config['sujet_obligatoire'] and not sujet.strip():
            return False, _("Le sujet est obligatoire pour ce type de rappel")
        
        # Validation spécifique SMS (pas de sujet)
        if type_rappel.lower() == 'sms' and sujet.strip():
            return False, _("Les SMS n'ont pas de sujet")
        
        # Longueur du sujet pour email
        if type_rappel.lower() == 'email' and len(sujet) > 100:
            return False, _("Sujet trop long (maximum 100 caractères)")
        
        return True, ""
    
    @classmethod
    def valider_horaire_envoi(cls, type_rappel, date_envoi):
        """
        Valide l'horaire d'envoi selon le type.
        """
        config = cls.get_config(type_rappel)
        if not config:
            return True, ""
        
        from datetime import datetime
        
        if isinstance(date_envoi, str):
            try:
                date_envoi = datetime.fromisoformat(date_envoi.replace('Z', '+00:00'))
            except ValueError:
                return False, _("Format de date invalide")
        
        # Vérifier weekend
        if not config['envoi_weekend'] and date_envoi.weekday() >= 5:  # Samedi=5, Dimanche=6
            return False, _("Envoi interdit le weekend pour ce type de rappel")
        
        # Vérifier horaires nocturnes
        if not config['envoi_nocturne']:
            heure = date_envoi.hour
            heure_debut = int(config.get('heure_debut', '08:00').split(':')[0])
            heure_fin = int(config.get('heure_fin', '20:00').split(':')[0])
            
            if heure < heure_debut or heure >= heure_fin:
                return False, _("Envoi autorisé uniquement entre {}h et {}h").format(
                    heure_debut, heure_fin
                )
        
        return True, ""
    
    @classmethod
    def get_variables_disponibles(cls, type_rappel):
        """
        Récupère les variables disponibles pour un type donné.
        """
        config = cls.get_config(type_rappel)
        
        # Variables communes
        variables_communes = [
            'prenom', 'nom', 'email', 'reference', 'montant', 'montant_total',
            'date_echeance', 'jours_retard', 'date_limite', 'association_nom'
        ]
        
        # Variables spécialisées
        variables_speciales = config.get('variables_speciales', [])
        
        return {
            'communes': variables_communes,
            'speciales': variables_speciales,
            'toutes': variables_communes + variables_speciales
        }
    
    @classmethod
    def get_contraintes_ui(cls, type_rappel):
        """
        Récupère les contraintes pour l'interface utilisateur.
        """
        config = cls.get_config(type_rappel)
        if not config:
            return {}
        
        return {
            'longueur_min': config['longueur_min'],
            'longueur_max': config['longueur_max'],
            'longueur_optimale': config['longueur_optimale'],
            'sujet_obligatoire': config['sujet_obligatoire'],
            'html_permis': config['html_permis'],
            'emojis_autorises': config['emojis_autorises'],
            'liens_autorises': config['liens_autorises'],
            'couleur': config['couleur'],
            'icone': config['icone'],
            'nom': config['nom'],
            'description': config['description'],
            'heure_optimale': config.get('heure_optimale'),
            'envoi_weekend': config['envoi_weekend'],
            'envoi_nocturne': config['envoi_nocturne'],
        }
    
    @classmethod
    def estimer_cout(cls, type_rappel, nb_destinataires=1):
        """
        Estime le coût d'envoi selon le type et le nombre de destinataires.
        """
        config = cls.get_config(type_rappel)
        if not config:
            return 0
        
        cout_unitaire = 0
        
        if type_rappel.lower() == 'sms':
            cout_unitaire = config.get('cout_par_sms', 0.08)
        elif type_rappel.lower() == 'courrier':
            cout_unitaire = config.get('cout_moyen', 1.50)
        # Email généralement gratuit
        
        return cout_unitaire * nb_destinataires
    
    @classmethod
    def get_niveau_recommande(cls, type_rappel, jours_retard=0):
        """
        Recommande un niveau de rappel selon le type et les jours de retard.
        """
        if jours_retard <= 7:
            return 'standard'
        elif jours_retard <= 21:
            return 'urgent'
        else:
            return 'formal'
    
    @classmethod
    def valider_contenu_complet(cls, type_rappel, sujet, contenu, date_envoi=None):
        """
        Validation complète d'un rappel selon son type.
        """
        erreurs = []
        
        # Validation du sujet
        valide, message = cls.valider_sujet(type_rappel, sujet)
        if not valide:
            erreurs.append(('sujet', message))
        
        # Validation du contenu
        valide, message = cls.valider_longueur(type_rappel, contenu)
        if not valide:
            erreurs.append(('contenu', message))
        
        # Validation de l'horaire
        if date_envoi:
            valide, message = cls.valider_horaire_envoi(type_rappel, date_envoi)
            if not valide:
                erreurs.append(('date_envoi', message))
        
        # Validations spécifiques par type
        if type_rappel.lower() == 'sms':
            # Vérifier les caractères spéciaux
            if any(ord(char) > 127 for char in contenu):
                erreurs.append(('contenu', _("Évitez les caractères spéciaux dans les SMS")))
        
        elif type_rappel.lower() == 'email':
            # Vérifier la structure HTML basique si HTML activé
            if '<' in contenu and '>' in contenu:
                if not contenu.strip().startswith('<') or not contenu.strip().endswith('>'):
                    erreurs.append(('contenu', _("Structure HTML incomplète")))
        
        elif type_rappel.lower() == 'courrier':
            # Vérifier la présence d'éléments formels
            elements_requis = ['Objet', 'Madame', 'Monsieur']
            for element in elements_requis:
                if element.lower() not in contenu.lower():
                    erreurs.append(('contenu', _("Élément manquant pour courrier formel : {}").format(element)))
        
        return len(erreurs) == 0, erreurs