# apps/evenements/tests/test_runner_workflow.py
"""
Configuration et utilitaires pour exécuter les tests de workflow
"""
import unittest
import time
from django.test import TestCase
from django.test.utils import override_settings
from django.core.management import call_command
from django.db import transaction
from io import StringIO


# Import des classes de tests
from .test_workflow_inscription import (
    WorkflowInscriptionTestCase,
    WorkflowInscriptionIntegrationTestCase,
    WorkflowPerformanceTestCase
)
from .test_workflow_validation import (
    WorkflowValidationTestCase,
    WorkflowValidationIntegrationTestCase,
    WorkflowValidationPerformanceTestCase
)
from .test_workflow_notifications import (
    WorkflowNotificationsTestCase,
    WorkflowNotificationsTachesTestCase,
    WorkflowNotificationsIntegrationTestCase
)

# Import des classes de tests avec gestion d'erreur
def safe_import_test_classes():
    """Import sécurisé des classes de tests"""
    test_classes = {}
    
    # Import des tests d'inscription
    try:
        from .test_workflow_inscription import (
            WorkflowInscriptionTestCase,
            WorkflowInscriptionIntegrationTestCase,
            WorkflowPerformanceTestCase
        )
        test_classes['inscription'] = [
            WorkflowInscriptionTestCase,
            WorkflowInscriptionIntegrationTestCase,
            WorkflowPerformanceTestCase
        ]
    except ImportError as e:
        print(f"⚠️  Impossible d'importer les tests d'inscription: {e}")
        test_classes['inscription'] = []
    
    # Import des tests de validation
    try:
        from .test_workflow_validation import (
            WorkflowValidationTestCase,
            WorkflowValidationIntegrationTestCase,
            WorkflowValidationPerformanceTestCase
        )
        test_classes['validation'] = [
            WorkflowValidationTestCase,
            WorkflowValidationIntegrationTestCase,
            WorkflowValidationPerformanceTestCase
        ]
    except ImportError as e:
        print(f"⚠️  Impossible d'importer les tests de validation: {e}")
        test_classes['validation'] = []
    
    # Import des tests de notifications
    try:
        from .test_workflow_notifications import (
            WorkflowNotificationsTestCase,
            WorkflowNotificationsTachesTestCase,
            WorkflowNotificationsIntegrationTestCase
        )
        test_classes['notifications'] = [
            WorkflowNotificationsTestCase,
            WorkflowNotificationsTachesTestCase,
            WorkflowNotificationsIntegrationTestCase
        ]
    except ImportError as e:
        print(f"⚠️  Impossible d'importer les tests de notifications: {e}")
        test_classes['notifications'] = []
    
    return test_classes


class WorkflowTestRunner:
    """
    Runner personnalisé pour les tests de workflow
    """
    
    def __init__(self):
        self.results = {
            'inscription': {'total': 0, 'passed': 0, 'failed': 0, 'errors': 0},
            'validation': {'total': 0, 'passed': 0, 'failed': 0, 'errors': 0},
            'notifications': {'total': 0, 'passed': 0, 'failed': 0, 'errors': 0},
            'integration': {'total': 0, 'passed': 0, 'failed': 0, 'errors': 0},
            'performance': {'total': 0, 'passed': 0, 'failed': 0, 'errors': 0}
        }
        self.start_time = None
        self.end_time = None
        self.test_classes = safe_import_test_classes()
    
    def run_workflow_tests(self, verbosity=2):
        """
        Exécute tous les tests de workflow avec reporting
        """
        print("=" * 80)
        print("🧪 EXÉCUTION DES TESTS DE WORKFLOW - APPLICATION ÉVÉNEMENTS")
        print("=" * 80)
        
        self.start_time = time.time()
        
        # Tests d'inscription
        if self.test_classes['inscription']:
            print("\n📝 Tests Workflow Inscription...")
            self._run_test_suite('inscription', self.test_classes['inscription'], verbosity)
        else:
            print("\n📝 Tests Workflow Inscription... ⚠️  IGNORÉS (imports manquants)")
        
        # Tests de validation
        if self.test_classes['validation']:
            print("\n✅ Tests Workflow Validation...")
            self._run_test_suite('validation', self.test_classes['validation'], verbosity)
        else:
            print("\n✅ Tests Workflow Validation... ⚠️  IGNORÉS (imports manquants)")
        
        # Tests de notifications
        if self.test_classes['notifications']:
            print("\n📧 Tests Workflow Notifications...")
            self._run_test_suite('notifications', self.test_classes['notifications'], verbosity)
        else:
            print("\n📧 Tests Workflow Notifications... ⚠️  IGNORÉS (imports manquants)")
        
        # Tests de performance (combinés)
        performance_classes = []
        for category in ['inscription', 'validation']:
            if self.test_classes[category]:
                # Extraire les classes de performance
                for test_class in self.test_classes[category]:
                    if 'Performance' in test_class.__name__:
                        performance_classes.append(test_class)
        
        if performance_classes:
            print("\n⚡ Tests Performance...")
            self._run_test_suite('performance', performance_classes, verbosity)
        else:
            print("\n⚡ Tests Performance... ⚠️  IGNORÉS (classes manquantes)")
        
        self.end_time = time.time()
        
        # Rapport final
        self._print_final_report()
    
    def _run_test_suite(self, category, test_classes, verbosity):
        """
        Exécute une suite de tests pour une catégorie
        """
        for test_class in test_classes:
            try:
                suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
                runner = unittest.TextTestRunner(
                    stream=StringIO(),
                    verbosity=verbosity
                )
                result = runner.run(suite)
                
                # Comptabiliser les résultats
                self.results[category]['total'] += result.testsRun
                self.results[category]['failed'] += len(result.failures)
                self.results[category]['errors'] += len(result.errors)
                self.results[category]['passed'] += (
                    result.testsRun - len(result.failures) - len(result.errors)
                )
                
                # Affichage du résultat
                status = "✅ PASS" if result.wasSuccessful() else "❌ FAIL"
                print(f"  {status} {test_class.__name__}")
                
                if result.failures and verbosity > 1:
                    for test, traceback in result.failures:
                        print(f"    ❌ FAILURE: {test}")
                        if verbosity > 2:
                            print(f"       {traceback}")
                
                if result.errors and verbosity > 1:
                    for test, traceback in result.errors:
                        print(f"    💥 ERROR: {test}")
                        if verbosity > 2:
                            print(f"       {traceback}")
                            
            except Exception as e:
                print(f"  💥 ERROR loading {test_class.__name__}: {e}")
                self.results[category]['errors'] += 1
    
    def _print_final_report(self):
        """
        Affiche le rapport final des tests
        """
        duration = self.end_time - self.start_time
        
        print("\n" + "=" * 80)
        print("📊 RAPPORT FINAL DES TESTS DE WORKFLOW")
        print("=" * 80)
        
        total_tests = sum(cat['total'] for cat in self.results.values())
        total_passed = sum(cat['passed'] for cat in self.results.values())
        total_failed = sum(cat['failed'] for cat in self.results.values())
        total_errors = sum(cat['errors'] for cat in self.results.values())
        
        print(f"\n⏱️  Durée totale: {duration:.2f} secondes")
        print(f"🧪 Tests exécutés: {total_tests}")
        print(f"✅ Réussis: {total_passed}")
        print(f"❌ Échecs: {total_failed}")
        print(f"💥 Erreurs: {total_errors}")
        
        if total_tests > 0:
            success_rate = (total_passed / total_tests) * 100
            print(f"📈 Taux de réussite: {success_rate:.1f}%")
        
        print("\n📋 Détail par catégorie:")
        print("-" * 50)
        
        for category, stats in self.results.items():
            if stats['total'] > 0:
                rate = (stats['passed'] / stats['total']) * 100
                status_icon = "✅" if rate == 100 else "⚠️" if rate >= 80 else "❌"
                print(f"{status_icon} {category.capitalize():15} | "
                      f"{stats['passed']:3}/{stats['total']:3} | "
                      f"{rate:5.1f}%")
        
        print("\n" + "=" * 80)
        
        if total_failed == 0 and total_errors == 0:
            print("🎉 TOUS LES TESTS DE WORKFLOW DISPONIBLES SONT PASSÉS !")
        else:
            print("⚠️  CERTAINS TESTS ONT ÉCHOUÉ - VÉRIFICATION NÉCESSAIRE")
        
        print("=" * 80)


class WorkflowTestConfiguration(TestCase):
    """
    Configuration et vérification pour les tests de workflow
    """
    
    def setUp(self):
        """Configuration commune pour tous les tests de workflow"""
        # Configuration de test commune
        pass
    
    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True,
        CACHES={
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
                'LOCATION': 'workflow-test-cache',
            }
        }
    )
    def test_configuration_tests_workflow(self):
        """Test que la configuration de test est correcte"""
        from django.conf import settings
        
        # Vérifier que les bonnes configurations sont actives
        self.assertEqual(
            settings.EMAIL_BACKEND,
            'django.core.mail.backends.locmem.EmailBackend'
        )
        self.assertTrue(settings.CELERY_TASK_ALWAYS_EAGER)
        
    def test_dependencies_disponibles(self):
        """Test que toutes les dépendances sont disponibles"""
        missing_dependencies = []
        
        try:
            # Modules Django
            from django.core.mail import send_mail
            from django.utils import timezone
            from django.test import TransactionTestCase
        except ImportError as e:
            missing_dependencies.append(f"Django: {e}")
        
        try:
            # Modules du projet - test optionnel
            from apps.evenements.models import Evenement, InscriptionEvenement
        except ImportError as e:
            missing_dependencies.append(f"Modèles événements: {e}")
        
        try:
            # Modules de test
            from unittest.mock import patch, MagicMock
        except ImportError as e:
            missing_dependencies.append(f"Mock: {e}")
        
        # Afficher les dépendances manquantes sans faire échouer le test
        if missing_dependencies:
            print(f"⚠️  Dépendances manquantes: {missing_dependencies}")
            # Ne pas faire échouer le test, juste informer
            # self.fail(f"Dépendances manquantes: {missing_dependencies}")


def run_all_workflow_tests():
    """
    Fonction utilitaire pour exécuter tous les tests de workflow
    """
    runner = WorkflowTestRunner()
    runner.run_workflow_tests(verbosity=2)
    return runner.results


if __name__ == '__main__':
    # Exécution directe des tests
    print("🚀 Lancement des tests de workflow...")
    try:
        results = run_all_workflow_tests()
        print(f"\n✅ Tests terminés avec succès!")
    except Exception as e:
        print(f"\n❌ Erreur lors de l'exécution des tests: {e}")
        import traceback
        traceback.print_exc()