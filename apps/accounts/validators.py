# Créer un nouveau fichier: apps/accounts/validators.py

import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

class StrongPasswordValidator:
    """
    Validateur de mot de passe renforcé qui vérifie:
    - La longueur minimale
    - La présence de lettres majuscules et minuscules
    - La présence de chiffres
    - La présence de caractères spéciaux
    - L'absence de séquences trop courantes
    - L'absence d'informations de l'utilisateur
    """
    
    def __init__(self, min_length=8):
        self.min_length = min_length
        
    def validate(self, password, user=None):
        """
        Valide que le mot de passe respecte les critères de sécurité.
        """
        errors = []
        
        # Vérifier la longueur
        if len(password) < self.min_length:
            errors.append(
                _("Le mot de passe doit contenir au moins %(min_length)d caractères.") % {'min_length': self.min_length}
            )
        
        # Vérifier la présence de lettres minuscules
        if not re.search(r'[a-z]', password):
            errors.append(_("Le mot de passe doit contenir au moins une lettre minuscule."))
        
        # Vérifier la présence de lettres majuscules
        if not re.search(r'[A-Z]', password):
            errors.append(_("Le mot de passe doit contenir au moins une lettre majuscule."))
        
        # Vérifier la présence de chiffres
        if not re.search(r'\d', password):
            errors.append(_("Le mot de passe doit contenir au moins un chiffre."))
        
        # Vérifier la présence de caractères spéciaux
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append(_("Le mot de passe doit contenir au moins un caractère spécial (!@#$%^&*(),.?\":{}|<>)."))
        
        # Vérifier les séquences courantes
        common_sequences = ['123456', 'password', 'qwerty', 'azerty', 'abcdef']
        password_lower = password.lower()
        for sequence in common_sequences:
            if sequence in password_lower:
                errors.append(_("Le mot de passe ne doit pas contenir de séquences trop courantes."))
                break
        
        # Vérifier les informations de l'utilisateur
        if user:
            user_data = [
                user.username.lower() if hasattr(user, 'username') else None,
                user.first_name.lower() if hasattr(user, 'first_name') and user.first_name else None,
                user.last_name.lower() if hasattr(user, 'last_name') and user.last_name else None,
                user.email.lower().split('@')[0] if hasattr(user, 'email') and user.email else None
            ]
            
            user_data = [data for data in user_data if data]
            
            for data in user_data:
                if data and len(data) >= 3 and data in password_lower:
                    errors.append(_("Le mot de passe ne doit pas contenir des informations personnelles."))
                    break
        
        if errors:
            raise ValidationError(errors)
    
    def get_help_text(self):
        """
        Retourne un texte d'aide pour l'utilisateur.
        """
        return _(
            "Votre mot de passe doit respecter les critères suivants :\n"
            "- Au moins %(min_length)d caractères\n"
            "- Au moins une lettre minuscule\n"
            "- Au moins une lettre majuscule\n"
            "- Au moins un chiffre\n"
            "- Au moins un caractère spécial\n"
            "- Ne pas contenir de séquences trop courantes (123456, password, etc.)\n"
            "- Ne pas contenir vos informations personnelles"
        ) % {'min_length': self.min_length}