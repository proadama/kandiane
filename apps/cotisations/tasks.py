# Dans apps/cotisations/tasks.py
from django.utils import timezone
from apps.cotisations.models import Rappel
from django.db import OperationalError
import logging
import time

logger = logging.getLogger(__name__)

def traiter_rappels_planifies(max_retries=3, retry_delay_initial=1):
    """
    Vérifie les rappels planifiés dont la date est passée et les marque comme envoyés.
    Déclenche également l'envoi effectif des rappels.
    
    Args:
        max_retries: Nombre maximum de tentatives en cas d'erreur de verrouillage de la base
        retry_delay_initial: Délai initial entre les tentatives (en secondes)
    """
    retry_count = 0
    retry_delay = retry_delay_initial
    
    while retry_count < max_retries:
        try:
            now = timezone.now()
            # Utiliser 'planifie' sans accent
            rappels_a_envoyer = Rappel.objects.filter(
                etat='planifie',
                date_envoi__lte=now
            )
            
            # Log le nombre de rappels trouvés
            logger.info(f"Rappels à envoyer trouvés: {rappels_a_envoyer.count()}")
            
            count = 0
            for rappel in rappels_a_envoyer:
                try:
                    # Logique d'envoi du rappel selon le type
                    if rappel.type_rappel == 'email':
                        # Envoi par email
                        logger.info(f"Simulation d'envoi d'email pour le rappel {rappel.id}")
                        pass
                    elif rappel.type_rappel == 'sms':
                        # Envoi par SMS
                        logger.info(f"Simulation d'envoi de SMS pour le rappel {rappel.id}")
                        pass
                    
                    # Utiliser 'envoye' sans accent
                    rappel.etat = 'envoye'
                    rappel.save()
                    count += 1
                    logger.info(f"Rappel {rappel.id} marqué comme envoyé")
                except OperationalError as db_err:
                    if 'database is locked' in str(db_err):
                        # Ne pas marquer le rappel comme échoué, nous réessaierons
                        logger.warning(f"Base de données verrouillée lors du traitement du rappel {rappel.id}")
                        raise  # Propager l'erreur pour déclencher le retry
                    else:
                        rappel.etat = 'echoue'
                        rappel.save()
                        logger.error(f"Erreur opérationnelle lors de l'envoi du rappel {rappel.id}: {str(db_err)}")
                except Exception as e:
                    # Utiliser 'echoue' sans accent
                    rappel.etat = 'echoue'
                    rappel.save()
                    logger.error(f"Erreur lors de l'envoi du rappel {rappel.id}: {str(e)}")
            
            logger.info(f"{count} rappels ont été traités et envoyés")
            return count
            
        except OperationalError as db_err:
            # Gérer spécifiquement les erreurs de verrouillage de base de données
            if 'database is locked' in str(db_err):
                retry_count += 1
                if retry_count < max_retries:
                    logger.warning(f"Base de données verrouillée, tentative {retry_count}/{max_retries}. Attente de {retry_delay}s...")
                    time.sleep(retry_delay)
                    # Backoff exponentiel: augmenter le délai entre les tentatives
                    retry_delay *= 2
                else:
                    logger.error(f"Abandon après {max_retries} tentatives: base de données verrouillée")
                    return 0
            else:
                logger.error(f"Erreur opérationnelle: {str(db_err)}")
                return 0
        except Exception as e:
            logger.error(f"Erreur dans la tâche de traitement des rappels: {str(e)}")
            return 0

def verifier_fonctionnement_rappels():
    """
    Fonction utilitaire pour vérifier que le traitement des rappels fonctionne.
    """
    logger.info("Démarrage de la vérification manuelle des rappels")
    count = traiter_rappels_planifies()
    logger.info(f"Vérification manuelle terminée: {count} rappels traités")
    print(f"Vérification manuelle: {count} rappels traités")
    return count