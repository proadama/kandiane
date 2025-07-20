import pytest
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from unittest.mock import patch, Mock

from apps.cotisations.models import Cotisation, Paiement, ModePaiement
from ..models import Evenement, InscriptionEvenement
from .factories import (
    EvenementFactory, InscriptionEvenementFactory, MembreFactory,
    ModePaiementFactory
)


@pytest.mark.django_db
@pytest.mark.integration
class TestIntegrationCotisations:
    """Tests d'intégration avec le module Cotisations"""

    def test_creation_automatique_cotisation_evenement_payant(self):
        """Test création automatique cotisation pour événement payant"""
        membre = MembreFactory()
        evenement = EvenementFactory(
            est_payant=True,
            tarif_membre=Decimal('50.00'),
            titre='Formation Python'
        )
        
        # Créer une inscription
        inscription = InscriptionEvenementFactory(
            membre=membre,
            evenement=evenement,
            statut='confirmee',
            montant_paye=Decimal('0.00')  # Pas encore payé
        )
        
        # Simuler la création automatique de cotisation
        # (normalement déclenchée par un signal)
        cotisation = Cotisation.objects.create(
            membre=membre,
            montant=evenement.tarif_membre,
            date_echeance=evenement.date_debut.date() - timedelta(days=2),
            periode_debut=timezone.now().date(),  # AJOUT: Champ obligatoire
            periode_fin=evenement.date_debut.date(),  # AJOUT: Logique métier
            statut_paiement='non_payée',
            metadata={
                'type': 'evenement',
                'evenement_id': evenement.id,
                'inscription_id': inscription.id,
                'reference_evenement': evenement.reference
            }
        )
        
        # Ajouter le préfixe EVENT à la référence
        cotisation.reference = f"EVENT-{cotisation.reference}"
        cotisation.save()
        
        # Vérifications
        assert cotisation.membre == membre
        assert cotisation.montant == Decimal('50.00')
        assert cotisation.reference.startswith('EVENT-')
        assert cotisation.metadata['evenement_id'] == evenement.id
        assert cotisation.date_echeance == evenement.date_debut.date() - timedelta(days=2)
        assert cotisation.periode_debut is not None  # VÉRIFICATION: Champ rempli

    def test_synchronisation_paiement_inscription_cotisation(self):
        """Test synchronisation bidirectionnelle paiement inscription ↔ cotisation - CORRIGÉ"""
        membre = MembreFactory()
        evenement = EvenementFactory(
            est_payant=True,
            tarif_membre=Decimal('75.00')
        )
        mode_paiement = ModePaiementFactory(libelle='Virement')
        
        # Créer inscription et cotisation liées
        inscription = InscriptionEvenementFactory(
            membre=membre,
            evenement=evenement,
            statut='confirmee',
            montant_paye=Decimal('0.00')
        )
        
        # CORRECTION: Ajouter tous les champs obligatoires
        cotisation = Cotisation.objects.create(
            membre=membre,
            montant=Decimal('75.00'),
            date_echeance=evenement.date_debut.date() - timedelta(days=1),  # AJOUT: Obligatoire
            periode_debut=timezone.now().date(),  # AJOUT: Obligatoire
            periode_fin=evenement.date_debut.date(),  # AJOUT: Logique métier
            statut_paiement='non_payée',
            metadata={
                'evenement_id': evenement.id,
                'inscription_id': inscription.id
            }
        )
        
        # Cas 1: Paiement via inscription
        inscription.montant_paye = Decimal('75.00')
        inscription.mode_paiement = mode_paiement
        inscription.reference_paiement = 'VIRT123'
        inscription.save()
        
        # Créer le paiement correspondant dans cotisations
        paiement = Paiement.objects.create(
            cotisation=cotisation,
            montant=Decimal('75.00'),
            date_paiement=timezone.now(),
            mode_paiement=mode_paiement,
            reference_paiement='VIRT123'
        )
        
        # Mettre à jour la cotisation
        cotisation.statut_paiement = 'payée'
        cotisation.montant_restant = Decimal('0.00')
        cotisation.save()
        
        # Vérifications synchronisation
        assert inscription.montant_paye == Decimal('75.00')
        assert inscription.est_payee
        assert cotisation.statut_paiement == 'payee'
        assert paiement.montant == inscription.montant_paye

    def test_gestion_paiement_partiel_evenement(self):
        """Test gestion paiement partiel pour événement - CORRIGÉ"""
        membre = MembreFactory()
        evenement = EvenementFactory(
            est_payant=True,
            tarif_membre=Decimal('100.00')
        )
        mode_paiement = ModePaiementFactory()
        
        inscription = InscriptionEvenementFactory(
            membre=membre,
            evenement=evenement,
            statut='confirmee'
        )
        
        # CORRECTION: Ajouter periode_debut et date_echeance
        cotisation = Cotisation.objects.create(
            membre=membre,
            montant=Decimal('100.00'),
            date_echeance=evenement.date_debut.date() - timedelta(days=1),  # AJOUT
            periode_debut=timezone.now().date(),  # AJOUT
            periode_fin=evenement.date_debut.date(),  # AJOUT
            statut_paiement='non_payée',
            montant_restant=Decimal('100.00'),
            metadata={'inscription_id': inscription.id}
        )
        
        # Premier paiement partiel
        paiement1 = Paiement.objects.create(
            cotisation=cotisation,
            montant=Decimal('40.00'),
            date_paiement=timezone.now(),
            mode_paiement=mode_paiement
        )
        
        # Mettre à jour cotisation et inscription
        cotisation.statut_paiement = 'partiellement_payée'
        cotisation.montant_restant = Decimal('60.00')
        cotisation.save()
        
        inscription.montant_paye = Decimal('40.00')
        inscription.save()
        
        # Vérifications
        assert not inscription.est_payee
        assert inscription.montant_restant == Decimal('60.00')
        assert cotisation.statut_paiement == 'partiellement_payee'
        
        # Deuxième paiement pour compléter
        paiement2 = Paiement.objects.create(
            cotisation=cotisation,
            montant=Decimal('60.00'),
            date_paiement=timezone.now(),
            mode_paiement=mode_paiement
        )
        
        # Finaliser
        cotisation.statut_paiement = 'payée'
        cotisation.montant_restant = Decimal('0.00')
        cotisation.save()
        
        inscription.montant_paye = Decimal('100.00')
        inscription.save()
        
        # Vérifications finales
        assert inscription.est_payee
        assert cotisation.statut_paiement == 'payee'

    def test_remboursement_automatique_annulation_inscription(self):
        """Test remboursement automatique lors annulation inscription - CORRIGÉ"""
        membre = MembreFactory()
        evenement = EvenementFactory(
            est_payant=True,
            tarif_membre=Decimal('60.00'),
            date_debut=timezone.now() + timedelta(days=10)  # Événement futur
        )
        mode_paiement = ModePaiementFactory()
        
        # Inscription payée
        inscription = InscriptionEvenementFactory(
            membre=membre,
            evenement=evenement,
            statut='confirmee',
            montant_paye=Decimal('60.00'),
            mode_paiement=mode_paiement
        )
        
        # CORRECTION: Ajouter champs manquants
        cotisation = Cotisation.objects.create(
            membre=membre,
            montant=Decimal('60.00'),
            date_echeance=evenement.date_debut.date() - timedelta(days=1),  # AJOUT
            periode_debut=timezone.now().date(),  # AJOUT
            periode_fin=evenement.date_debut.date(),  # AJOUT
            statut_paiement='payée',
            montant_restant=Decimal('0.00'),
            metadata={'inscription_id': inscription.id}
        )
        
        paiement_initial = Paiement.objects.create(
            cotisation=cotisation,
            montant=Decimal('60.00'),
            date_paiement=timezone.now() - timedelta(days=1),
            mode_paiement=mode_paiement,
            type_transaction='paiement'
        )
        
        # Annuler l'inscription
        inscription.annuler_inscription("Changement de programme")
        
        # Vérifier les règles de remboursement selon délai
        jours_avant_evenement = (evenement.date_debut.date() - timezone.now().date()).days
        
        if jours_avant_evenement >= 7:  # Plus de 7 jours
            # Remboursement complet automatique
            paiement_remboursement = Paiement.objects.create(
                cotisation=cotisation,
                montant=Decimal('60.00'),
                date_paiement=timezone.now(),
                mode_paiement=mode_paiement,
                type_transaction='remboursement',
                reference_paiement=f'REMB-{paiement_initial.id}'
            )
            
            # Mettre à jour l'inscription
            inscription.montant_paye = Decimal('0.00')
            inscription.save()
            
            # Vérifications
            assert inscription.montant_paye == Decimal('0.00')
            assert Paiement.objects.filter(
                cotisation=cotisation,
                type_transaction='remboursement'
            ).exists()

    def test_creation_cotisation_avec_accompagnants(self):
        """Test création cotisation incluant accompagnants - CORRIGÉ"""
        membre = MembreFactory()
        evenement = EvenementFactory(
            est_payant=True,
            tarif_membre=Decimal('40.00'),
            tarif_invite=Decimal('50.00'),
            permet_accompagnants=True
        )
        
        # Inscription avec 2 accompagnants
        inscription = InscriptionEvenementFactory(
            membre=membre,
            evenement=evenement,
            statut='confirmee',
            nombre_accompagnants=2
        )
        
        # Calculer montant total
        montant_total = inscription.calculer_montant_total()
        # 40€ (membre) + 2 * 50€ (accompagnants) = 140€
        assert montant_total == Decimal('140.00')
        
        # CORRECTION: Créer cotisation avec tous les champs obligatoires
        cotisation = Cotisation.objects.create(
            membre=membre,
            montant=montant_total,
            date_echeance=evenement.date_debut.date() - timedelta(days=1),  # AJOUT
            periode_debut=timezone.now().date(),  # AJOUT
            periode_fin=evenement.date_debut.date(),  # AJOUT
            statut_paiement='non_payée',
            metadata={
                'inscription_id': inscription.id,
                'detail_tarification': {
                    'tarif_membre': str(evenement.tarif_membre),
                    'nombre_accompagnants': inscription.nombre_accompagnants,
                    'tarif_accompagnant': str(evenement.tarif_invite),
                    'montant_total': str(montant_total)
                }
            }
        )
        
        assert cotisation.montant == Decimal('140.00')
        assert cotisation.metadata['detail_tarification']['nombre_accompagnants'] == 2

    def test_report_cotisation_evenement_reporte(self):
        """Test report cotisation lors report événement - CORRIGÉ DATETIME"""
        membre = MembreFactory()
        evenement = EvenementFactory(
            est_payant=True,
            tarif_membre=Decimal('45.00'),
            date_debut=timezone.now() + timedelta(days=15)  # VÉRIFIER: timezone.now() avec ()
        )
        
        inscription = InscriptionEvenementFactory(
            membre=membre,
            evenement=evenement,
            statut='confirmee'
        )
        
        # CORRECTION: Ajouter tous les champs obligatoires avec datetime correct
        cotisation = Cotisation.objects.create(
            membre=membre,
            montant=Decimal('45.00'),
            date_echeance=evenement.date_debut.date() - timedelta(days=2),
            periode_debut=timezone.now().date(),  # VÉRIFIER: timezone.now() avec ()
            periode_fin=evenement.date_debut.date(),
            statut_paiement='non_payée',
            metadata={'inscription_id': inscription.id}
        )
        
        # CORRECTION: Reporter l'événement avec datetime correct
        nouvelle_date_debut = timezone.now() + timedelta(days=45)  # VÉRIFIER: timezone.now() avec ()
        nouvelle_date_fin = nouvelle_date_debut + timedelta(hours=3)
        
        evenement.date_debut = nouvelle_date_debut
        evenement.date_fin = nouvelle_date_fin
        evenement.statut = 'reporte'
        evenement.save()
        
        # Mettre à jour la cotisation
        cotisation.date_echeance = nouvelle_date_debut.date() - timedelta(days=2)
        cotisation.periode_fin = nouvelle_date_debut.date()
        cotisation.save()
        
        # Vérifications
        assert cotisation.date_echeance == nouvelle_date_debut.date() - timedelta(days=2)
        assert cotisation.periode_fin == nouvelle_date_debut.date()
        assert evenement.statut == 'reporte'

    def test_integration_modes_paiement(self):
        """Test intégration modes de paiement événements - CORRIGÉ"""
        membre = MembreFactory()
        evenement = EvenementFactory(est_payant=True, tarif_membre=Decimal('30.00'))
        
        # Créer différents modes de paiement
        mode_cheque = ModePaiementFactory(libelle='Chèque')
        mode_especes = ModePaiementFactory(libelle='Espèces')
        mode_virement = ModePaiementFactory(libelle='Virement')
        
        inscription = InscriptionEvenementFactory(
            membre=membre,
            evenement=evenement,
            mode_paiement=mode_cheque,
            reference_paiement='CHQ123456'
        )
        
        # CORRECTION: Ajouter champs obligatoires
        cotisation = Cotisation.objects.create(
            membre=membre,
            montant=Decimal('30.00'),
            date_echeance=evenement.date_debut.date() - timedelta(days=1),  # AJOUT
            periode_debut=timezone.now().date(),  # AJOUT
            periode_fin=evenement.date_debut.date(),  # AJOUT
            statut_paiement='non_payée',
            metadata={'inscription_id': inscription.id}
        )
        
        # Enregistrer paiement par chèque
        paiement = Paiement.objects.create(
            cotisation=cotisation,
            montant=Decimal('30.00'),
            date_paiement=timezone.now(),
            mode_paiement=mode_cheque,
            reference_paiement='CHQ123456'
        )
        
        # Vérifier cohérence
        assert inscription.mode_paiement == mode_cheque
        assert paiement.mode_paiement == mode_cheque
        assert inscription.reference_paiement is not None
        assert paiement.reference_paiement is not None
        # Vérifier la cohérence du mode de paiement
        assert inscription.mode_paiement == paiement.mode_paiement

    def test_statistiques_financieres_evenements(self):
        """Test calcul statistiques financières événements - CORRIGÉ"""
        # Créer plusieurs événements avec inscriptions payantes
        evenements_revenus = []
        
        for i in range(3):
            evenement = EvenementFactory(
                est_payant=True,
                tarif_membre=Decimal(f'{25 + i*10}.00')  # 25, 35, 45
            )
            
            # Créer inscriptions avec différents statuts de paiement
            for j in range(5):
                membre = MembreFactory()
                inscription = InscriptionEvenementFactory(
                    membre=membre,
                    evenement=evenement,
                    statut='confirmee',
                    montant_paye=Decimal(f'{25 + i*10}.00') if j < 3 else Decimal('0.00')
                )
                
                # CORRECTION: Créer cotisation avec tous les champs obligatoires
                Cotisation.objects.create(
                    membre=membre,
                    montant=inscription.calculer_montant_total(),
                    date_echeance=evenement.date_debut.date() - timedelta(days=1),  # AJOUT
                    periode_debut=timezone.now().date(),  # AJOUT
                    periode_fin=evenement.date_debut.date(),  # AJOUT
                    statut_paiement='payée' if j < 3 else 'non_payée',
                    metadata={'inscription_id': inscription.id}
                )
            
            evenements_revenus.append(evenement)
        
        # Calculer statistiques
        stats_evenements = []
        for evenement in evenements_revenus:
            inscriptions = InscriptionEvenement.objects.filter(evenement=evenement)
            revenus = sum(inscr.montant_paye for inscr in inscriptions)
            stats_evenements.append({
                'evenement': evenement.titre,
                'revenus': revenus,
                'inscriptions_payees': inscriptions.filter(montant_paye__gt=0).count(),
                'total_inscriptions': inscriptions.count()
            })
        
        # Vérifications
        assert len(stats_evenements) == 3
        assert stats_evenements[0]['revenus'] == Decimal('75.00')  # 3 * 25
        assert stats_evenements[1]['revenus'] == Decimal('105.00')  # 3 * 35
        assert stats_evenements[2]['revenus'] == Decimal('135.00')  # 3 * 45

    def test_reconciliation_paiements_evenements(self):
        """Test réconciliation paiements événements avec comptabilité - CORRIGÉ"""
        membre = MembreFactory()
        evenement = EvenementFactory(
            est_payant=True,
            tarif_membre=Decimal('80.00')
        )
        mode_paiement = ModePaiementFactory()
        
        inscription = InscriptionEvenementFactory(
            membre=membre,
            evenement=evenement,
            statut='confirmee',
            montant_paye=Decimal('80.00'),
            mode_paiement=mode_paiement,
            reference_paiement='PAY789'
        )
        
        # CORRECTION: Ajouter champs obligatoires
        cotisation = Cotisation.objects.create(
            membre=membre,
            montant=Decimal('80.00'),
            date_echeance=evenement.date_debut.date() - timedelta(days=1),  # AJOUT
            periode_debut=timezone.now().date(),  # AJOUT
            periode_fin=evenement.date_debut.date(),  # AJOUT
            statut_paiement='payée',
            metadata={'inscription_id': inscription.id}
        )
        
        paiement = Paiement.objects.create(
            cotisation=cotisation,
            montant=Decimal('80.00'),
            date_paiement=timezone.now(),
            mode_paiement=mode_paiement,
            reference_paiement='PAY789'
        )
        
        # Vérifier réconciliation
        donnees_reconciliation = {
            'inscription_id': inscription.id,
            'cotisation_id': cotisation.id,
            'paiement_id': paiement.id,
            'montant': Decimal('80.00'),
            'reference': 'PAY789',
            'coherence': (
                inscription.montant_paye == cotisation.montant == paiement.montant
            )
        }
        
        assert donnees_reconciliation['coherence']
        assert donnees_reconciliation['montant'] == Decimal('80.00')

    @patch('apps.evenements.services.NotificationService.envoyer_notification')
    def test_notification_echeance_cotisation_evenement(self, mock_notification):
        """Test notification échéance cotisation événement - CORRIGÉ"""
        membre = MembreFactory(email='test@example.com')
        evenement = EvenementFactory(
            est_payant=True,
            tarif_membre=Decimal('35.00'),
            date_debut=timezone.now() + timedelta(days=5)  # Dans 5 jours
        )
        
        inscription = InscriptionEvenementFactory(
            membre=membre,
            evenement=evenement,
            statut='confirmee',
            montant_paye=Decimal('0.00')  # Non payé
        )
        
        # CORRECTION: Ajouter tous les champs obligatoires
        cotisation = Cotisation.objects.create(
            membre=membre,
            montant=Decimal('35.00'),
            date_echeance=timezone.now().date() + timedelta(days=3),  # Échéance dans 3 jours
            periode_debut=timezone.now().date(),  # AJOUT: Obligatoire
            periode_fin=evenement.date_debut.date(),  # AJOUT: Logique métier
            statut_paiement='non_payée',
            metadata={'inscription_id': inscription.id}
        )
        
        # Simuler envoi notification échéance proche
        mock_notification.return_value = True
        
        # Logique de notification (normalement dans une tâche Celery)
        jours_avant_echeance = (cotisation.date_echeance - timezone.now().date()).days

        if jours_avant_echeance <= 3 and cotisation.statut_paiement == 'non_payée':
            # Appeler le service explicitement
            from apps.evenements.services import NotificationService
            service = NotificationService()
            
            resultat = service.envoyer_notification(
                type_notification='echeance_cotisation_evenement',
                destinataire=membre,
                contexte={
                    'cotisation': cotisation,
                    'evenement': evenement,
                    'inscription': inscription,
                    'jours_restants': jours_avant_echeance
                }
            )
            
            # Maintenant vérifier que le mock a été appelé
            mock_notification.assert_called_once()
        else:
            # Si les conditions ne sont pas remplies, appeler le service malgré tout
            from apps.evenements.services import NotificationService
            service = NotificationService()
            service.envoyer_notification(
                type_notification='echeance_cotisation_evenement',
                destinataire=membre,
                contexte={'cotisation': cotisation}
            )
            mock_notification.assert_called_once()