# Mise à jour de apps/cotisations/management/commands/create_rappel_templates.py
from django.core.management.base import BaseCommand
from django.utils.translation import gettext as _
from apps.cotisations.models import RappelTemplate


class Command(BaseCommand):
    """
    Commande pour créer les templates de rappel matriciels (3 types × 3 niveaux).
    Usage: python manage.py create_rappel_templates
    """
    help = 'Crée les templates de rappel matriciels par défaut (Email/SMS/Courrier × Standard/Urgent/Formel)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force la recréation des templates existants',
        )
        parser.add_argument(
            '--langue',
            type=str,
            default='fr',
            help='Langue des templates à créer (défaut: fr)',
        )
        parser.add_argument(
            '--type',
            type=str,
            choices=['email', 'sms', 'courrier', 'all'],
            default='all',
            help='Type de templates à créer (défaut: all)',
        )
    
    def handle(self, *args, **options):
        force = options['force']
        langue = options['langue']
        type_filter = options['type']
        
        self.stdout.write(f'🚀 Création des templates matriciels en {langue}...')
        
        if force:
            # Supprimer les templates existants si force est activé
            count_deleted = RappelTemplate.objects.filter(langue=langue).count()
            RappelTemplate.objects.filter(langue=langue).delete()
            self.stdout.write(f'❌ Supprimé {count_deleted} templates existants')
        
        # Créer les templates matriciels
        templates_crees = self._creer_templates_matriciels(langue, type_filter)
        
        if templates_crees > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ {templates_crees} templates matriciels créés avec succès!'
                )
            )
            self._afficher_matrice_templates(langue)
        else:
            self.stdout.write(
                self.style.WARNING('⚠️  Aucun template créé (ils existent peut-être déjà)')
            )
    
    def _creer_templates_matriciels(self, langue='fr', type_filter='all'):
        """Crée les templates matriciels 3×3."""
        
        templates_matriciels = self._get_templates_definition(langue)
        
        # Filtrer par type si spécifié
        if type_filter != 'all':
            templates_matriciels = [
                t for t in templates_matriciels 
                if t['type_rappel'] == type_filter
            ]
        
        # Créer les templates
        count = 0
        for template_data in templates_matriciels:
            template, created = RappelTemplate.objects.get_or_create(
                nom=template_data['nom'],
                type_template=template_data['type_template'],
                type_rappel=template_data['type_rappel'],
                langue=langue,
                defaults=template_data
            )
            if created:
                count += 1
                self.stdout.write(f'  ✓ {template.nom}')
        
        return count
    
    def _get_templates_definition(self, langue='fr'):
        """Définit les 9 templates matriciels."""
        
        if langue == 'fr':
            return [
                # ============== TEMPLATES EMAIL ==============
                {
                    'nom': 'Email Standard - Premier rappel',
                    'type_template': 'standard',
                    'type_rappel': 'email',
                    'sujet': '💌 Rappel amical - Cotisation {association_nom}',
                    'contenu': """Bonjour {prenom},

J'espère que ce message vous trouve en bonne santé !

Je me permets de vous rappeler gentiment que votre cotisation (référence {reference}) d'un montant de {montant} € était due le {date_echeance}.

📋 **Détails de votre cotisation :**
• Référence : {reference}
• Montant : {montant} €
• Échéance : {date_echeance}

💳 **Pour régler facilement :**
Vous pouvez effectuer le règlement avant le {date_limite} par les moyens habituels.

N'hésitez pas à nous contacter si vous avez des questions ou des difficultés particulières.

Merci beaucoup pour votre fidélité à {association_nom} !

Bien cordialement,
L'équipe de {association_nom}

---
Ce message est envoyé automatiquement. En cas de règlement récent, merci d'ignorer ce rappel.""",
                    'niveau_min': 1,
                    'niveau_max': 2,
                    'ordre_affichage': 1,
                },
                {
                    'nom': 'Email Urgent - Rappel avec délai',
                    'type_template': 'urgent',
                    'type_rappel': 'email',
                    'sujet': '⚠️ URGENT - Cotisation en retard de {jours_retard} jours',
                    'contenu': """Bonjour {prenom},

🚨 **RAPPEL URGENT**

Votre cotisation (réf. {reference}) est maintenant en retard de **{jours_retard} jours**.

📊 **Situation de votre dossier :**
• Montant dû : {montant} €
• Date d'échéance dépassée : {date_echeance}
• Jours de retard : {jours_retard}

⏰ **ACTION REQUISE AVANT LE {date_limite}**

Pour éviter des complications supplémentaires, nous vous demandons de régulariser cette situation rapidement.

📞 **Besoin d'aide ?**
Si vous rencontrez des difficultés, contactez-nous immédiatement :
• Email : contact@{association_nom}.fr
• Téléphone : [À compléter]

⚖️ **Important :** Passé le {date_limite}, nous serons contraints d'appliquer notre procédure de recouvrement.

Nous restons à votre disposition pour trouver une solution ensemble.

Cordialement,
L'équipe de {association_nom}

---
⚠️ Ce rappel urgent nécessite une action de votre part.""",
                    'niveau_min': 2,
                    'niveau_max': 4,
                    'ordre_affichage': 2,
                },
                {
                    'nom': 'Email Formel - Mise en demeure',
                    'type_template': 'formal',
                    'type_rappel': 'email',
                    'sujet': '⚖️ MISE EN DEMEURE - Cotisation impayée {reference}',
                    'contenu': """Madame, Monsieur {nom},

**OBJET : MISE EN DEMEURE - COTISATION IMPAYÉE**

Nous constatons qu'à ce jour, et malgré nos précédents rappels, votre cotisation demeure impayée.

📋 **DÉTAILS DE LA CRÉANCE :**
• Référence : {reference}
• Montant total dû : {montant} €
• Date d'échéance initiale : {date_echeance}
• Nombre de jours de retard : {jours_retard}

⚖️ **MISE EN DEMEURE**

Par la présente, nous vous METTONS EN DEMEURE de procéder au règlement intégral de la somme de {montant} € avant le **{date_limite}**, dernier délai.

📧 **RAPPELS PRÉCÉDENTS :**
Plusieurs rappels vous ont été adressés sans succès.

⚠️ **CONSÉQUENCES EN CAS DE NON-PAIEMENT :**

À défaut de règlement dans le délai imparti, nous nous verrons contraints d'engager :
• Une procédure de recouvrement judiciaire
• L'application de pénalités de retard
• La suspension de vos droits d'adhérent
• Le recouvrement par voie d'huissier

Ces démarches entraîneront des frais supplémentaires à votre charge.

📞 **DERNIÈRE POSSIBILITÉ :**
Pour éviter ces désagréments, contactez-nous immédiatement au [téléphone] ou répondez à ce message.

Nous espérons un règlement rapide de cette situation.

Veuillez agréer, Madame, Monsieur, l'expression de nos salutations distinguées.

**{association_nom}**
La Direction

---
⚖️ Document à valeur juridique - Conservez précieusement ce message.""",
                    'niveau_min': 3,
                    'niveau_max': 5,
                    'ordre_affichage': 3,
                },
                
                # ============== TEMPLATES SMS ==============
                {
                    'nom': 'SMS Standard - Rappel simple',
                    'type_template': 'standard',
                    'type_rappel': 'sms',
                    'sujet': '',
                    'contenu': """Bonjour {prenom} ! 😊
Petit rappel : votre cotisation {reference} de {montant}€ était due le {date_echeance}.
Merci de régulariser avant le {date_limite}.
{association_nom}""",
                    'niveau_min': 1,
                    'niveau_max': 2,
                    'ordre_affichage': 4,
                },
                {
                    'nom': 'SMS Urgent - Rappel pressant',
                    'type_template': 'urgent',
                    'type_rappel': 'sms',
                    'sujet': '',
                    'contenu': """⚠️ URGENT {prenom}
Cotisation {reference} en retard de {jours_retard} jours !
Montant : {montant}€
RÉGULARISEZ avant le {date_limite}
Contact : [tel]
{association_nom}""",
                    'niveau_min': 2,
                    'niveau_max': 4,
                    'ordre_affichage': 5,
                },
                {
                    'nom': 'SMS Formel - Avis officiel',
                    'type_template': 'formal',
                    'type_rappel': 'sms',
                    'sujet': '',
                    'contenu': """AVIS OFFICIEL - M./Mme {nom}
MISE EN DEMEURE
Cotisation {reference} : {montant}€
Retard : {jours_retard} jours
DERNIER DÉLAI : {date_limite}
{association_nom}""",
                    'niveau_min': 3,
                    'niveau_max': 5,
                    'ordre_affichage': 6,
                },
                
                # ============== TEMPLATES COURRIER ==============
                {
                    'nom': 'Courrier Standard - Lettre cordiale',
                    'type_template': 'standard',
                    'type_rappel': 'courrier',
                    'sujet': 'Rappel de cotisation',
                    'contenu': """{association_nom}
[Adresse de l'association]
[Code postal, Ville]
[Téléphone - Email]

                                                    Le [date du jour]

Madame, Monsieur {nom}
{adresse}
[Code postal] [Ville]

Objet : Rappel de cotisation - Référence {reference}

Madame, Monsieur,

Nous espérons que cette lettre vous trouve en bonne santé.

Nous nous permettons de vous rappeler que votre cotisation annuelle d'adhérent, d'un montant de {montant} €, était échue le {date_echeance}.

Nous sommes convaincus qu'il s'agit d'un simple oubli de votre part, et nous vous saurions gré de bien vouloir procéder au règlement avant le {date_limite}.

Votre fidélité et votre soutien sont précieux pour notre association, et nous tenons à maintenir d'excellentes relations avec tous nos membres.

Si vous avez déjà effectué ce règlement, nous vous prions d'excuser ce rappel et de ne pas en tenir compte.

En cas de difficultés particulières, n'hésitez pas à nous contacter afin que nous puissions étudier ensemble les solutions possibles.

Nous vous remercions par avance de votre diligence et vous prions d'agréer, Madame, Monsieur, l'expression de nos sentiments les meilleurs.

                                        Le Président,
                                        [Nom du Président]
                                        
---
Pièce jointe : Bordereau de règlement""",
                    'niveau_min': 1,
                    'niveau_max': 2,
                    'ordre_affichage': 7,
                },
                {
                    'nom': 'Courrier Urgent - Lettre Recommandée',
                    'type_template': 'urgent',
                    'type_rappel': 'courrier',
                    'sujet': 'URGENT - Cotisation en retard',
                    'contenu': """{association_nom}
[Adresse de l'association]
[Code postal, Ville]
[Téléphone - Email]

                                        LETTRE RECOMMANDÉE AVEC A.R.
                                        
                                                    Le [date du jour]

Madame, Monsieur {nom}
{adresse}
[Code postal] [Ville]

Objet : RAPPEL URGENT - Cotisation en retard de {jours_retard} jours
Référence : {reference}

Madame, Monsieur,

Nous constatons avec regret que votre cotisation d'un montant de {montant} €, dont l'échéance était fixée au {date_echeance}, demeure impayée à ce jour.

Cette situation nous préoccupe d'autant plus que cette cotisation accuse maintenant un retard de {jours_retard} jours.

MISE EN GARDE :

Nous vous rappelons que le règlement des cotisations conditionne :
• Le maintien de vos droits d'adhérent
• Votre participation aux activités de l'association  
• L'accès aux services réservés aux membres

DÉLAI IMPÉRATIF :

Nous vous accordons un délai de grâce jusqu'au {date_limite} pour régulariser cette situation.

Passé cette date, nous serons contraints d'appliquer les mesures suivantes :
• Suspension de vos droits d'adhérent
• Engagement d'une procédure de recouvrement
• Application des pénalités prévues dans nos statuts

CONTACT URGENT :

Pour éviter ces désagréments, nous vous invitons à nous contacter au plus vite :
• Téléphone : [numéro d'urgence]
• Email : [email de contact]

Nous espérons vivement une régularisation rapide de votre situation.

Veuillez agréer, Madame, Monsieur, l'expression de nos salutations distinguées.

                                        Le Président,
                                        [Nom du Président]
                                        
---
⚠️ IMPORTANT : Cette lettre constitue un rappel officiel.
Conservez-la précieusement.""",
                    'niveau_min': 2,
                    'niveau_max': 4,
                    'ordre_affichage': 8,
                },
                {
                    'nom': 'Courrier Formel - Mise en demeure officielle',
                    'type_template': 'formal',
                    'type_rappel': 'courrier',
                    'sujet': 'MISE EN DEMEURE OFFICIELLE',
                    'contenu': """{association_nom}
[Adresse complète de l'association]
[Code postal, Ville]
SIRET : [numéro SIRET]
Téléphone : [téléphone]

                                LETTRE RECOMMANDÉE AVEC ACCUSÉ DE RÉCEPTION
                                
                                                            Le [date du jour]

Madame, Monsieur {nom}
{adresse}
[Code postal] [Ville]

OBJET : MISE EN DEMEURE DE PAYER - DERNIÈRE SOMMATION
RÉFÉRENCE DOSSIER : {reference}

Madame, Monsieur,

RAPPEL DES FAITS :

Vous êtes redevable envers notre association d'une cotisation d'un montant de {montant} € dont l'échéance était fixée au {date_echeance}.

Malgré nos précédents courriers de rappel, cette somme demeure impayée à ce jour, soit un retard de {jours_retard} jours.

MISE EN DEMEURE FORMELLE :

En conséquence, nous vous METTONS EN DEMEURE de procéder au paiement intégral de la somme de {montant} € dans un délai de QUINZE (15) JOURS à compter de la réception de la présente lettre, soit avant le {date_limite}.

FONDEMENT JURIDIQUE :

Cette mise en demeure est effectuée en application de l'article 1344 du Code Civil et conformément à nos statuts associatifs.

CONSÉQUENCES EN CAS DE NON-PAIEMENT :

À défaut de règlement dans le délai susmentionné, nous nous verrons contraints, à notre grand regret, de :

1. Radier votre nom de nos registres d'adhérents
2. Engager contre vous une procédure de recouvrement judiciaire  
3. Réclamer le remboursement des frais occasionnés par cette procédure
4. Demander des dommages et intérêts pour le préjudice subi

DERNIÈRE OPPORTUNITÉ :

Avant d'engager ces démarches, nous vous offrons une dernière possibilité de régulariser votre situation en prenant contact avec nous dans les 48 heures.

En cas de difficultés financières avérées, un échéancier de paiement pourra exceptionnellement être étudié, sous réserve d'un accord écrit préalable.

VALEUR JURIDIQUE :

La présente lettre vaut mise en demeure au sens de l'article 1344 du Code Civil et fait courir les intérêts de retard à compter de sa réception.

Nous espérons qu'il ne sera pas nécessaire d'aller plus loin dans cette procédure et qu'une solution amiable pourra encore être trouvée.

Veuillez agréer, Madame, Monsieur, l'expression de nos salutations distinguées.

                                        Pour {association_nom}
                                        Le Président,
                                        
                                        [Signature et cachet]
                                        [Nom du Président]

---
PIÈCES JOINTES :
- Copie de la facture originale
- Relevé de compte démontrant l'absence de paiement
- Statuts de l'association (extrait)

⚖️ DOCUMENT JURIDIQUE - À CONSERVER OBLIGATOIREMENT""",
                    'niveau_min': 3,
                    'niveau_max': 5,
                    'ordre_affichage': 9,
                }
            ]
        
        elif langue == 'en':
            # Templates en anglais (version simplifiée)
            return [
                {
                    'nom': 'Email Standard - Friendly Reminder',
                    'type_template': 'standard',
                    'type_rappel': 'email',
                    'sujet': '💌 Friendly Reminder - {association_nom} Membership',
                    'contenu': """Hello {prenom},

I hope this message finds you well!

This is a gentle reminder that your membership fee (reference {reference}) of {montant} € was due on {date_echeance}.

Please proceed with payment before {date_limite}.

Thank you for your continued support of {association_nom}!

Best regards,
The {association_nom} team""",
                    'niveau_min': 1,
                    'niveau_max': 2,
                    'ordre_affichage': 1,
                },
                # Ajouter d'autres templates en anglais selon les besoins...
            ]
        
        return []
    
    def _afficher_matrice_templates(self, langue='fr'):
        """Affiche un tableau récapitulatif des templates créés."""
        self.stdout.write('\n📊 MATRICE DES TEMPLATES CRÉÉS :\n')
        
        # En-têtes
        headers = ['Type/Niveau', 'Standard', 'Urgent', 'Formel']
        self.stdout.write('├─' + '─' * 15 + '┬─' + '─' * 15 + '┬─' + '─' * 15 + '┬─' + '─' * 15 + '─┤')
        self.stdout.write(f'│ {"Type/Niveau":<13} │ {"Standard":<13} │ {"Urgent":<13} │ {"Formel":<13} │')
        self.stdout.write('├─' + '─' * 15 + '┼─' + '─' * 15 + '┼─' + '─' * 15 + '┼─' + '─' * 15 + '─┤')
        
        # Lignes de données
        types = ['email', 'sms', 'courrier']
        niveaux = ['standard', 'urgent', 'formal']
        
        for type_rappel in types:
            row = [type_rappel.upper().ljust(13)]
            
            for type_template in niveaux:
                template = RappelTemplate.objects.filter(
                    type_rappel=type_rappel,
                    type_template=type_template,
                    langue=langue
                ).first()
                
                if template:
                    row.append('✅ Créé'.ljust(13))
                else:
                    row.append('❌ Absent'.ljust(13))
            
            self.stdout.write(f'│ {row[0]} │ {row[1]} │ {row[2]} │ {row[3]} │')
        
        self.stdout.write('└─' + '─' * 15 + '┴─' + '─' * 15 + '┴─' + '─' * 15 + '┴─' + '─' * 15 + '─┘')
        
        # Statistiques
        total_templates = RappelTemplate.objects.filter(langue=langue).count()
        self.stdout.write(f'\n📈 TOTAL : {total_templates} templates dans la matrice')
        
        # Répartition par type
        for type_rappel in types:
            count = RappelTemplate.objects.filter(type_rappel=type_rappel, langue=langue).count()
            self.stdout.write(f'   • {type_rappel.upper()} : {count} templates')