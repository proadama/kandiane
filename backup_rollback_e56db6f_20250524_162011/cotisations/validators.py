# apps\cotisations\validators.py
"""
Validateurs intelligents pour les rappels selon leur type.
Validation automatique basée sur les contraintes définies.
"""

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.core.validators import URLValidator
from django.utils import timezone
from datetime import datetime, timedelta
import re
import html

from .type_rappel_config import TypeRappelConfig


class RappelTypeValidator:
    """
    Validateur principal qui orchestre la validation selon le type de rappel.
    """
    
    def __init__(self, type_rappel):
        self.type_rappel = type_rappel.lower() if type_rappel else 'email'
        self.config = TypeRappelConfig.get_config(self.type_rappel)
    
    def __call__(self, value):
        """
        Point d'entrée principal de validation.
        """
        if not self.config:
            raise ValidationError(_("Type de rappel non supporté : {}").format(self.type_rappel))
        
        # Déléguer à la validation spécialisée
        if hasattr(self, f'_valider_{self.type_rappel}'):
            validator_method = getattr(self, f'_valider_{self.type_rappel}')
            validator_method(value)
    
    def _valider_email(self, contenu):
        """Validation spécialisée pour les emails."""
        longueur = len(contenu)
        
        # Validation de longueur
        if longueur < self.config['longueur_min']:
            raise ValidationError(
                _("Email trop court. Minimum {} caractères (actuel: {})").format(
                    self.config['longueur_min'], longueur
                )
            )
        
        if longueur > self.config['longueur_max']:
            raise ValidationError(
                _("Email trop long. Maximum {} caractères (actuel: {})").format(
                    self.config['longueur_max'], longueur
                )
            )
        
        # Validation HTML basique si présent
        if self.config['html_permis'] and ('<' in contenu and '>' in contenu):
            self._valider_html_basique(contenu)
        
        # Validation des liens
        if self.config['validation_liens']:
            self._valider_liens_email(contenu)
    
    def _valider_sms(self, contenu):
        """Validation spécialisée pour les SMS."""
        # Calcul de longueur réelle (emojis comptent double)
        longueur_reelle = self._calculer_longueur_sms(contenu)
        
        if longueur_reelle < self.config['longueur_min']:
            raise ValidationError(
                _("SMS trop court. Minimum {} caractères").format(self.config['longueur_min'])
            )
        
        if longueur_reelle > self.config['longueur_max']:
            raise ValidationError(
                _("SMS trop long. Maximum {} caractères (actuel: {} avec emojis)").format(
                    self.config['longueur_max'], longueur_reelle
                )
            )
        
        # Validation des caractères spéciaux
        if self.config['validation_caracteres_speciaux']:
            self._valider_caracteres_sms(contenu)
        
        # Validation des liens courts
        self._valider_liens_sms(contenu)
    
    def _valider_courrier(self, contenu):
        """Validation spécialisée pour les courriers."""
        longueur = len(contenu)
        
        # Validation de longueur
        if longueur < self.config['longueur_min']:
            raise ValidationError(
                _("Courrier trop court. Minimum {} caractères").format(self.config['longueur_min'])
            )
        
        if longueur > self.config['longueur_max']:
            raise ValidationError(
                _("Courrier trop long. Maximum {} caractères").format(self.config['longueur_max'])
            )
        
        # Validation du format lettre officielle
        self._valider_format_courrier(contenu)
        
        # Validation absence HTML/emojis
        if '<' in contenu or '>' in contenu:
            raise ValidationError(_("Les courriers ne peuvent pas contenir de HTML"))
        
        # Vérifier emojis interdits
        if self._contient_emojis(contenu):
            raise ValidationError(_("Les courriers officiels ne peuvent pas contenir d'emojis"))
    
    def _calculer_longueur_sms(self, contenu):
        """Calcule la longueur réelle d'un SMS (emojis comptent double)."""
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
        
        nb_emojis = len(emoji_pattern.findall(contenu))
        return len(contenu) + nb_emojis  # Chaque emoji compte double
    
    def _valider_html_basique(self, contenu):
        """Validation HTML basique pour les emails."""
        try:
            # Vérifier que le HTML n'est pas complètement cassé
            html.parser.HTMLParser().feed(contenu)
        except Exception:
            raise ValidationError(_("Structure HTML invalide"))
        
        # Vérifier les balises dangereuses
        balises_interdites = ['<script', '<iframe', '<embed', '<object']
        for balise in balises_interdites:
            if balise.lower() in contenu.lower():
                raise ValidationError(_("Balise HTML interdite détectée : {}").format(balise))
    
    def _valider_liens_email(self, contenu):
        """Validation des liens dans les emails."""
        # Détecter URLs
        url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
            re.IGNORECASE
        )
        
        urls = url_pattern.findall(contenu)
        validator = URLValidator()
        
        for url in urls:
            try:
                validator(url)
            except ValidationError:
                raise ValidationError(_("URL invalide détectée : {}").format(url))
    
    def _valider_liens_sms(self, contenu):
        """Validation des liens dans les SMS."""
        # Les SMS devraient avoir des liens courts
        url_pattern = re.compile(r'https?://\S+', re.IGNORECASE)
        urls = url_pattern.findall(contenu)
        
        for url in urls:
            if len(url) > 30:  # Liens longs dans SMS
                raise ValidationError(
                    _("Utilisez des liens courts dans les SMS (max 30 chars) : {}").format(url)
                )
    
    def _valider_caracteres_sms(self, contenu):
        """Validation des caractères spéciaux dans SMS."""
        # Caractères qui posent problème dans les SMS
        caracteres_problematiques = ['€', '£', '¢', '¥', '§', '°', 'µ']
        
        for char in caracteres_problematiques:
            if char in contenu:
                raise ValidationError(
                    _("Caractère problématique dans SMS : '{}'. Utilisez 'EUR' au lieu de '€'").format(char)
                )
    
    def _valider_format_courrier(self, contenu):
        """Validation du format standard d'un courrier officiel."""
        contenu_lower = contenu.lower()
        
        # Éléments obligatoires d'un courrier formel
        elements_requis = {
            'objet': ['objet :', 'objet:', 'object :'],
            'civilite': ['madame', 'monsieur'],
            'formule_politesse': ['salutations', 'cordialement', 'respectueusement']
        }
        
        for element, variantes in elements_requis.items():
            if not any(variante in contenu_lower for variante in variantes):
                raise ValidationError(
                    _("Élément manquant dans le courrier : {}").format(element)
                )
    
    def _contient_emojis(self, text):
        """Vérifie si le texte contient des emojis."""
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
        return bool(emoji_pattern.search(text))


class SujetRappelValidator:
    """
    Validateur spécialisé pour les sujets de rappel.
    """
    
    def __init__(self, type_rappel):
        self.type_rappel = type_rappel.lower() if type_rappel else 'email'
        self.config = TypeRappelConfig.get_config(self.type_rappel)
    
    def __call__(self, value):
        if not self.config:
            return
        
        # SMS n'ont pas de sujet
        if self.type_rappel == 'sms' and value:
            raise ValidationError(_("Les SMS n'ont pas de sujet"))
        
        # Sujet obligatoire pour email et courrier
        if self.config['sujet_obligatoire'] and not value.strip():
            raise ValidationError(_("Le sujet est obligatoire pour ce type de rappel"))
        
        # Longueur du sujet
        if self.type_rappel == 'email' and len(value) > 100:
            raise ValidationError(_("Sujet trop long pour un email (max 100 caractères)"))
        
        if self.type_rappel == 'courrier' and len(value) > 150:
            raise ValidationError(_("Objet trop long pour un courrier (max 150 caractères)"))


class DateEnvoiRappelValidator:
    """
    Validateur pour les dates et heures d'envoi selon le type de rappel.
    """
    
    def __init__(self, type_rappel):
        self.type_rappel = type_rappel.lower() if type_rappel else 'email'
        self.config = TypeRappelConfig.get_config(self.type_rappel)
    
    def __call__(self, value):
        if not self.config or not value:
            return
        
        # Convertir en datetime si nécessaire
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                raise ValidationError(_("Format de date invalide"))
        
        # Vérifier que c'est dans le futur
        if value <= timezone.now():
            raise ValidationError(_("La date d'envoi doit être dans le futur"))
        
        # Vérifier weekend
        if not self.config['envoi_weekend'] and value.weekday() >= 5:
            raise ValidationError(
                _("Envoi interdit le weekend pour ce type de rappel")
            )
        
        # Vérifier horaires
        if not self.config['envoi_nocturne']:
            heure = value.hour
            heure_debut = int(self.config.get('heure_debut', '08:00').split(':')[0])
            heure_fin = int(self.config.get('heure_fin', '20:00').split(':')[0])
            
            if heure < heure_debut or heure >= heure_fin:
                raise ValidationError(
                    _("Envoi autorisé uniquement entre {}h et {}h pour ce type").format(
                        heure_debut, heure_fin
                    )
                )


class VariablesRappelValidator:
    """
    Validateur pour vérifier la présence et validité des variables dans les templates.
    """
    
    def __init__(self, type_rappel):
        self.type_rappel = type_rappel.lower() if type_rappel else 'email'
        self.variables_config = TypeRappelConfig.get_variables_disponibles(self.type_rappel)
    
    def __call__(self, value):
        if not value:
            return
        
        # Détecter les variables dans le contenu
        pattern = re.compile(r'\{([^}]+)\}')
        variables_trouvees = pattern.findall(value)
        
        # Variables autorisées
        variables_autorisees = self.variables_config['toutes']
        
        # Vérifier variables inconnues
        variables_inconnues = []
        for var in variables_trouvees:
            if var not in variables_autorisees:
                variables_inconnues.append(var)
        
        if variables_inconnues:
            raise ValidationError(
                _("Variables inconnues détectées : {}. Variables disponibles : {}").format(
                    ', '.join(variables_inconnues),
                    ', '.join(variables_autorisees)
                )
            )
        
        # Vérifier variables recommandées manquantes
        variables_recommandees = ['prenom', 'nom', 'reference', 'montant']
        variables_manquantes = []
        
        for var in variables_recommandees:
            if var not in variables_trouvees:
                variables_manquantes.append(var)
        
        # Avertissement pour variables manquantes (pas d'erreur bloquante)
        if variables_manquantes and len(variables_trouvees) > 0:
            # On peut logger un warning ici, mais pas lever d'exception
            import logging
            logger = logging.getLogger('cotisations.validators')
            logger.warning(
                f"Variables recommandées manquantes dans template {self.type_rappel}: "
                f"{', '.join(variables_manquantes)}"
            )


class CoutRappelValidator:
    """
    Validateur pour estimer et contrôler les coûts d'envoi.
    """
    
    def __init__(self, type_rappel, nb_destinataires=1):
        self.type_rappel = type_rappel.lower() if type_rappel else 'email'
        self.nb_destinataires = nb_destinataires
        self.config = TypeRappelConfig.get_config(self.type_rappel)
    
    def __call__(self, value):
        if not self.config:
            return
        
        # Calculer le coût estimé
        cout_estime = TypeRappelConfig.estimer_cout(self.type_rappel, self.nb_destinataires)
        
        # Limites de coût (à configurer selon votre budget)
        limites_cout = {
            'sms': 50.0,      # 50€ max pour campagne SMS
            'courrier': 200.0, # 200€ max pour campagne courrier
            'email': 0.0       # Email gratuit
        }
        
        limite = limites_cout.get(self.type_rappel, 0)
        
        if cout_estime > limite and limite > 0:
            raise ValidationError(
                _("Coût estimé trop élevé : {:.2f}€ (limite: {:.2f}€). "
                  "Réduisez le nombre de destinataires ou changez de type.").format(
                    cout_estime, limite
                )
            )


# ==================== FONCTIONS UTILITAIRES ====================

def valider_rappel_complet(type_rappel, sujet, contenu, date_envoi=None, nb_destinataires=1):
    """
    Fonction utilitaire pour valider un rappel complet.
    """
    erreurs = []
    
    try:
        # Validation du contenu
        validator_contenu = RappelTypeValidator(type_rappel)
        validator_contenu(contenu)
    except ValidationError as e:
        erreurs.append(('contenu', str(e)))
    
    try:
        # Validation du sujet
        validator_sujet = SujetRappelValidator(type_rappel)
        validator_sujet(sujet)
    except ValidationError as e:
        erreurs.append(('sujet', str(e)))
    
    try:
        # Validation de la date
        if date_envoi:
            validator_date = DateEnvoiRappelValidator(type_rappel)
            validator_date(date_envoi)
    except ValidationError as e:
        erreurs.append(('date_envoi', str(e)))
    
    try:
        # Validation des variables
        validator_variables = VariablesRappelValidator(type_rappel)
        validator_variables(contenu)
    except ValidationError as e:
        erreurs.append(('variables', str(e)))
    
    try:
        # Validation du coût
        validator_cout = CoutRappelValidator(type_rappel, nb_destinataires)
        validator_cout(contenu)
    except ValidationError as e:
        erreurs.append(('cout', str(e)))
    
    return len(erreurs) == 0, erreurs


def obtenir_conseils_optimisation(type_rappel, contenu, sujet=""):
    """
    Retourne des conseils pour optimiser un rappel selon son type.
    """
    config = TypeRappelConfig.get_config(type_rappel)
    if not config:
        return []
    
    conseils = []
    longueur = len(contenu)
    
    # Conseils de longueur
    if longueur < config['longueur_optimale'] * 0.8:
        conseils.append({
            'type': 'info',
            'message': _("Contenu court. Considérez ajouter plus de détails (optimal: {} chars)").format(
                config['longueur_optimale']
            )
        })
    elif longueur > config['longueur_optimale'] * 1.2:
        conseils.append({
            'type': 'warning',
            'message': _("Contenu long. Considérez raccourcir pour plus d'impact")
        })
    
    # Conseils spécifiques par type
    if type_rappel == 'sms':
        if longueur > 140:
            conseils.append({
                'type': 'warning',
                'message': _("SMS proche de la limite. Vérifiez que tous les caractères sont nécessaires")
            })
        
        if any(ord(char) > 127 for char in contenu):
            conseils.append({
                'type': 'info',
                'message': _("Caractères spéciaux détectés. Ils peuvent augmenter la taille du SMS")
            })
    
    elif type_rappel == 'email':
        if not sujet:
            conseils.append({
                'type': 'error',
                'message': _("Sujet manquant. Essentiel pour les emails")
            })
        
        if 'http' in contenu and 'cliquez' not in contenu.lower():
            conseils.append({
                'type': 'info',
                'message': _("Lien détecté. Pensez à ajouter un texte d'incitation ('cliquez ici')")
            })
    
    elif type_rappel == 'courrier':
        if 'objet' not in contenu.lower():
            conseils.append({
                'type': 'warning',
                'message': _("Pensez à inclure un 'Objet :' clair dans votre courrier")
            })
    
    return conseils