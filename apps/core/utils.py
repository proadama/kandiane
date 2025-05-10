# apps/core/utils.py
import os
import uuid
from django.utils.text import slugify
from django.utils import timezone
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.conf import settings


def get_file_path(instance, filename):
    """
    Génère un chemin de fichier unique avec UUID pour le stockage des fichiers.
    """
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    
    # Déterminer le bon nom du dossier à partir du nom du modèle
    model_name = instance.__class__.__name__.lower()
    today = timezone.now().strftime('%Y/%m/%d')
    
    return os.path.join('uploads', model_name, today, filename)

def get_unique_slug(instance, field_name, slug_field='slug', max_length=100):
    """
    Génère un slug unique pour un modèle donné.
    
    Note: Pour le test, nous vérifions si le modèle a le champ slug_field,
    et sinon nous retournons simplement une valeur.
    """
    value = getattr(instance, field_name)
    slug = slugify(value)[:max_length]
    
    # Pour le test, vérifier si le modèle a le champ slug
    field_names = [f.name for f in instance.__class__._meta.fields]
    if slug_field not in field_names:
        return slug
    
    # Tronquer le slug si nécessaire
    if max_length:
        slug = slug[:max_length]
        
    # Vérifier l'unicité du slug
    qs = instance.__class__.objects.filter(**{slug_field: slug})
    if instance.pk:
        qs = qs.exclude(pk=instance.pk)
        
    # Si le slug existe déjà, ajouter un suffixe numérique
    if qs.exists():
        counter = 1
        while qs.filter(**{slug_field: f"{slug}-{counter}"}).exists():
            counter += 1
        slug = f"{slug}-{counter}"
        
    return slug

# Pour implémenter la solution de mot de passe temporaire.
def generate_temp_password_token(user_id, password):
    """Génère un token contenant l'ID utilisateur et le mot de passe temporaire
    
    Le token expire après PASSWORD_RESET_TIMEOUT (2 heures par défaut)
    """
    signer = TimestampSigner()
    token_data = f"{user_id}:{password}"
    return signer.sign(token_data)

def verify_temp_password_token(token):
    """Vérifie la validité du token et extrait les données
    
    Retourne un tuple (user_id, password) si le token est valide
    Retourne None si le token est invalide ou expiré
    """
    signer = TimestampSigner()
    try:
        # max_age est en secondes (2 heures par défaut)
        max_age = getattr(settings, 'PASSWORD_RESET_TIMEOUT', 7200)
        token_data = signer.unsign(token, max_age=max_age)
        
        # Décomposer le token pour obtenir l'ID utilisateur et le mot de passe
        parts = token_data.split(':')
        if len(parts) != 2:
            return None
        
        user_id, password = parts
        return (int(user_id), password)
    except (BadSignature, SignatureExpired, ValueError):
        return None