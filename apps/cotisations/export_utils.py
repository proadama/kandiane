# apps/cotisations/export_utils.py
import io
import csv
from datetime import timedelta
from decimal import Decimal

from django.http import HttpResponse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum, F
from django.template.loader import get_template
from django.conf import settings

# Pour Excel
import xlsxwriter

# Pour PDF
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm

def export_cotisations_csv(queryset):
    """
    Exporte une liste de cotisations au format CSV.

    Args:
        queryset: QuerySet de cotisations à exporter

    Returns:
        HttpResponse: Réponse HTTP avec le fichier CSV attaché
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="cotisations_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    
    # En-tête - CORRECTION: Chaque en-tête doit être un élément distinct
    writer.writerow([
        str(_('Référence')), 
        str(_('Membre')), 
        str(_('Courriel')), 
        str(_('Montant')),
        str(_('Montant restant')), 
        str(_('Date émission')), 
        str(_('Date échéance')),
        str(_('Statut paiement')), 
        str(_('Type de membre'))
    ])
    
    # Données
    for cotisation in queryset:
        writer.writerow([
            cotisation.reference,
            f"{cotisation.membre.prenom} {cotisation.membre.nom}",
            cotisation.membre.email,
            cotisation.montant,
            cotisation.montant_restant,
            cotisation.date_emission,
            cotisation.date_echeance,
            cotisation.get_statut_paiement_display(),
            cotisation.type_membre.libelle if cotisation.type_membre else ''
        ])
    
    return response

def export_cotisations_excel(queryset):
    """
    Exporte une liste de cotisations au format Excel (XLSX).

    Args:
        queryset: QuerySet de cotisations à exporter

    Returns:
        HttpResponse: Réponse HTTP avec le fichier Excel attaché
    """
    # Créer un buffer en mémoire pour stocker le fichier Excel
    output = io.BytesIO()
    
    # Créer un nouveau workbook et ajouter une feuille de calcul
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet(str(_("Cotisations")))
    
    # Formats
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#F2F2F2',
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'text_wrap': True
    })
    
    date_format = workbook.add_format({'num_format': 'dd/mm/yyyy'})
    money_format = workbook.add_format({'num_format': '# ##0.00 €'})
    
    # En-têtes
    headers = [
        str(_('Référence')),
        str(_('Membre')),
        str(_('Courriel')),
        str(_('Montant')),
        str(_('Montant restant')),
        str(_('Date émission')),
        str(_('Date échéance')),
        str(_('Statut paiement')),
        str(_('Type de membre'))
    ]
    
    # Largeurs des colonnes
    column_widths = [20, 30, 35, 15, 15, 15, 15, 20, 20]
    
    # Écrire les en-têtes et définir les largeurs de colonnes
    for col_num, (header, width) in enumerate(zip(headers, column_widths)):
        worksheet.write(0, col_num, header, header_format)
        worksheet.set_column(col_num, col_num, width)
    
    # Écrire les données
    for row_num, cotisation in enumerate(queryset, 1):
        worksheet.write(row_num, 0, cotisation.reference)
        worksheet.write(row_num, 1, f"{cotisation.membre.prenom} {cotisation.membre.nom}")
        worksheet.write(row_num, 2, cotisation.membre.email)
        worksheet.write(row_num, 3, float(cotisation.montant), money_format)
        worksheet.write(row_num, 4, float(cotisation.montant_restant), money_format)
        worksheet.write_datetime(row_num, 5, cotisation.date_emission, date_format)
        worksheet.write_datetime(row_num, 6, cotisation.date_echeance, date_format)
        worksheet.write(row_num, 7, cotisation.get_statut_paiement_display())
        worksheet.write(row_num, 8, cotisation.type_membre.libelle if cotisation.type_membre else '')
    
    # Filtres automatiques sur les en-têtes
    worksheet.autofilter(0, 0, len(queryset), len(headers) - 1)
    
    # Fermer le workbook
    workbook.close()
    
    # Préparer la réponse HTTP
    output.seek(0)
    
    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="cotisations_{timezone.now().strftime("%Y%m%d")}.xlsx"'
    
    return response

def export_paiements_csv(queryset):
    """
    Exporte une liste de paiements au format CSV.

    Args:
        queryset: QuerySet de paiements à exporter

    Returns:
        HttpResponse: Réponse HTTP avec le fichier CSV attaché
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="paiements_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    
    # En-tête
    writer.writerow([
        str(_('Référence cotisation')),
        str(_('Membre')),
        str(_('Date de paiement')),
        str(_('Montant')),
        str(_('Mode de paiement')),
        str(_('Type de transaction')),
        str(_('Référence de paiement')),
        str(_('Devise'))
    ])
    
    # Données
    for paiement in queryset:
        writer.writerow([
            paiement.cotisation.reference,
            f"{paiement.cotisation.membre.prenom} {paiement.cotisation.membre.nom}",
            paiement.date_paiement.strftime('%d/%m/%Y %H:%M'),
            paiement.montant,
            paiement.mode_paiement.libelle if paiement.mode_paiement else '',
            paiement.get_type_transaction_display(),
            paiement.reference_paiement or '',
            paiement.devise
        ])
    
    return response

def export_paiements_excel(queryset):
    """
    Exporte une liste de paiements au format Excel (XLSX).

    Args:
        queryset: QuerySet de paiements à exporter

    Returns:
        HttpResponse: Réponse HTTP avec le fichier Excel attaché
    """
    # Créer un buffer en mémoire pour stocker le fichier Excel
    output = io.BytesIO()
    
    # Créer un nouveau workbook et ajouter une feuille de calcul
    # Ajout de l'option remove_timezone=True pour éviter les erreurs avec les datetimes
    workbook = xlsxwriter.Workbook(output, {'remove_timezone': True})
    worksheet = workbook.add_worksheet(str(_("Paiements")))
    
    # Formats
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#F2F2F2',
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'text_wrap': True
    })
    
    date_format = workbook.add_format({'num_format': 'dd/mm/yyyy hh:mm'})
    money_format = workbook.add_format({'num_format': '# ##0.00 €'})
    
    # En-têtes
    headers = [
        str(_('Référence cotisation')),
        str(_('Membre')),
        str(_('Date de paiement')),
        str(_('Montant')),
        str(_('Mode de paiement')),
        str(_('Type de transaction')),
        str(_('Référence de paiement')),
        str(_('Devise'))
    ]
    
    # Largeurs des colonnes
    column_widths = [20, 30, 20, 15, 20, 20, 25, 10]
    
    # Écrire les en-têtes et définir les largeurs de colonnes
    for col_num, (header, width) in enumerate(zip(headers, column_widths)):
        worksheet.write(0, col_num, header, header_format)
        worksheet.set_column(col_num, col_num, width)
    
    # Écrire les données
    for row_num, paiement in enumerate(queryset, 1):
        worksheet.write(row_num, 0, paiement.cotisation.reference)
        worksheet.write(row_num, 1, f"{paiement.cotisation.membre.prenom} {paiement.cotisation.membre.nom}")
        
        # Écrire la date avec le format date défini
        worksheet.write_datetime(row_num, 2, paiement.date_paiement, date_format)
        
        worksheet.write(row_num, 3, float(paiement.montant), money_format)
        worksheet.write(row_num, 4, paiement.mode_paiement.libelle if paiement.mode_paiement else '')
        worksheet.write(row_num, 5, paiement.get_type_transaction_display())
        worksheet.write(row_num, 6, paiement.reference_paiement or '')
        worksheet.write(row_num, 7, paiement.devise)
    
    # Filtres automatiques sur les en-têtes
    worksheet.autofilter(0, 0, len(queryset), len(headers) - 1)
    
    # Fermer le workbook
    workbook.close()
    
    # Préparer la réponse HTTP
    output.seek(0)
    
    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="paiements_{timezone.now().strftime("%Y%m%d")}.xlsx"'
    
    return response

def generer_rapport_cotisations_pdf(queryset):
    """
    Génère un rapport PDF détaillé des cotisations.
    
    Args:
        queryset: QuerySet de cotisations à inclure dans le rapport
        
    Returns:
        HttpResponse: Réponse HTTP avec le fichier PDF attaché
    """
    # Créer un buffer pour le PDF
    buffer = io.BytesIO()
    
    # Créer le document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    # Récupérer les styles
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    subtitle_style = styles['Heading2']
    normal_style = styles['Normal']
    
    # Créer une liste d'éléments à ajouter au document
    elements = []
    
    # Titre
    elements.append(Paragraph(str(_("Rapport des cotisations")), title_style))
    elements.append(Spacer(1, 0.5*cm))
    
    # Date du rapport
    date_rapport = timezone.now().strftime("%d/%m/%Y %H:%M")
    elements.append(Paragraph(f"{str(_('Date du rapport'))}: {date_rapport}", normal_style))
    elements.append(Spacer(1, 0.5*cm))
    
    # Statistiques
    elements.append(Paragraph(str(_("Statistiques")), subtitle_style))
    
    total_cotisations = queryset.count()
    montant_total = queryset.aggregate(total=Sum('montant')).get('total') or Decimal('0.00')
    montant_paye = queryset.aggregate(total=Sum(F('montant') - F('montant_restant'))).get('total') or Decimal('0.00')
    montant_restant = montant_total - montant_paye
    
    taux_recouvrement = 0
    if montant_total > 0:
        taux_recouvrement = (montant_paye / montant_total * 100).quantize(Decimal('0.01'))
    
    stats_data = [
        [str(_("Nombre de cotisations")), str(total_cotisations)],
        [str(_("Montant total")), f"{montant_total} €"],
        [str(_("Montant payé")), f"{montant_paye} €"],
        [str(_("Montant restant à payer")), f"{montant_restant} €"],
        [str(_("Taux de recouvrement")), f"{taux_recouvrement} %"]
    ]
    
    # Créer le tableau de statistiques
    stats_table = Table(stats_data, colWidths=[doc.width/2.0, doc.width/2.0])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(stats_table)
    elements.append(Spacer(1, 1*cm))
    
    # Liste des cotisations
    elements.append(Paragraph(str(_("Liste des cotisations")), subtitle_style))
    
    # En-têtes du tableau
    headers = [
        str(_('Référence')),
        str(_('Membre')),
        str(_('Montant')),
        str(_('Reste à payer')),
        str(_('Statut')),
        str(_('Date échéance'))
    ]
    
    data = [headers]
    
    # Ajouter les données des cotisations
    for cotisation in queryset:
        data.append([
            cotisation.reference,
            f"{cotisation.membre.prenom} {cotisation.membre.nom}",
            f"{cotisation.montant} €",
            f"{cotisation.montant_restant} €",
            cotisation.get_statut_paiement_display(),
            cotisation.date_echeance.strftime("%d/%m/%Y")
        ])
    
    # Créer le tableau des cotisations
    cotisations_table = Table(data, colWidths=[doc.width/6.0]*6)
    cotisations_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(cotisations_table)
    
    # Construire le PDF
    doc.build(elements)
    
    # Récupérer le contenu du buffer
    buffer.seek(0)
    
    # Créer la réponse HTTP
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="rapport_cotisations_{timezone.now().strftime("%Y%m%d")}.pdf"'
    response.write(buffer.getvalue())
    
    return response

def export_rappels_csv(queryset, filename=None):
    """
    Exporte les rappels au format CSV.
    
    Args:
        queryset: QuerySet de Rappel à exporter
        filename: Nom du fichier (par défaut: 'rappels_YYYYMMDD.csv')
        
    Returns:
        HttpResponse avec le fichier CSV
    """
    if not filename:
        filename = f"rappels_{timezone.now().strftime('%Y%m%d')}.csv"
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(response, delimiter=';')
    
    # En-tête
    writer.writerow([
        _('ID'), _('Cotisation'), _('Membre'), _('Email'),
        _('Date envoi'), _('Type'), _('État'), _('Niveau')
    ])
    
    # Données
    for rappel in queryset:
        writer.writerow([
            rappel.id,
            rappel.cotisation.reference,
            f"{rappel.membre.prenom} {rappel.membre.nom}",
            rappel.membre.email,
            rappel.date_envoi.strftime('%d/%m/%Y %H:%M') if rappel.date_envoi else '',
            rappel.get_type_rappel_display(),
            rappel.get_etat_display(),
            rappel.niveau
        ])
    
    return response

def export_rappels_excel(queryset, filename=None):
    """
    Exporte les rappels au format Excel.
    
    Args:
        queryset: QuerySet de Rappel à exporter
        filename: Nom du fichier (par défaut: 'rappels_YYYYMMDD.xlsx')
        
    Returns:
        HttpResponse avec le fichier Excel
    """
    if not filename:
        filename = f"rappels_{timezone.now().strftime('%Y%m%d')}.xlsx"
    
    # Créer un buffer pour stocker le fichier Excel
    output = io.BytesIO()
    
    # Créer un classeur Excel et ajouter une feuille
    workbook = xlsxwriter.Workbook(output, {'remove_timezone': True})
    worksheet = workbook.add_worksheet(_("Rappels"))
    
    # Formats
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#F0F0F0',
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'text_wrap': True
    })
    
    datetime_format = workbook.add_format({'num_format': 'dd/mm/yyyy hh:mm'})
    
    # En-têtes
    headers = [
        _('ID'), _('Cotisation'), _('Membre'), _('Email'),
        _('Date envoi'), _('Type'), _('État'), _('Niveau')
    ]
    
    for col_num, header in enumerate(headers):
        worksheet.write(0, col_num, header, header_format)
    
    # Données
    for row_num, rappel in enumerate(queryset, 1):
        worksheet.write(row_num, 0, rappel.id)
        worksheet.write(row_num, 1, rappel.cotisation.reference)
        worksheet.write(row_num, 2, f"{rappel.membre.prenom} {rappel.membre.nom}")
        worksheet.write(row_num, 3, rappel.membre.email)
        
        if rappel.date_envoi:
            worksheet.write_datetime(row_num, 4, rappel.date_envoi, datetime_format)
        
        worksheet.write(row_num, 5, rappel.get_type_rappel_display())
        worksheet.write(row_num, 6, rappel.get_etat_display())
        worksheet.write(row_num, 7, rappel.niveau)
    
    # Ajuster la largeur des colonnes
    for col_num, _ in enumerate(headers):
        worksheet.set_column(col_num, col_num, 15)
    
    # Fermer le classeur et obtenir le contenu
    workbook.close()
    output.seek(0)
    
    # Créer la réponse HTTP
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response

def generer_recu_pdf(paiement, filename=None):
    """
    Génère un reçu PDF pour un paiement.
    
    Args:
        paiement: Instance de Paiement
        filename: Nom du fichier (par défaut: 'recu_paiement_ID.pdf')
        
    Returns:
        HttpResponse avec le fichier PDF
    """
    if not filename:
        filename = f"recu_paiement_{paiement.id}.pdf"
    
    # Créer un buffer pour stocker le PDF
    buffer = io.BytesIO()
    
    # Créer le document PDF
    pagesize = A4
    doc = SimpleDocTemplate(
        buffer,
        pagesize=pagesize,
        topMargin=2*cm,
        bottomMargin=2*cm,
        leftMargin=2*cm,
        rightMargin=2*cm
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=1,  # Centré
        spaceAfter=12
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Heading2'],
        fontSize=12,
        alignment=1,
        spaceAfter=6
    )
    
    normal_style = styles["Normal"]
    heading_style = styles["Heading3"]
    
    # Contenu du document
    content = []
    
    # Titre
    content.append(Paragraph(_("REÇU DE PAIEMENT"), title_style))
    content.append(Spacer(1, 12))
    
    # Référence
    content.append(Paragraph(
        f"{_('Référence')}: {paiement.reference_paiement or paiement.id}",
        subtitle_style
    ))
    content.append(Spacer(1, 12))
    
    # Informations de base
    infos = [
        [_("Date de paiement:"), paiement.date_paiement.strftime('%d/%m/%Y %H:%M')],
        [_("Mode de paiement:"), paiement.mode_paiement.libelle if paiement.mode_paiement else '-'],
        [_("Montant:"), f"{paiement.montant} {paiement.devise}"],
        [_("Type de transaction:"), paiement.get_type_transaction_display()],
        [_("Cotisation associée:"), paiement.cotisation.reference]
    ]
    
    # Ajouter les informations du membre
    membre = paiement.cotisation.membre
    infos.extend([
        [_("Membre:"), f"{membre.prenom} {membre.nom}"],
        [_("Email:"), membre.email],
        [_("ID membre:"), str(membre.id)]
    ])
    
    # Créer un tableau avec ces informations
    table = Table(infos, colWidths=[150, 350])
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey)
    ]))
    
    content.append(table)
    content.append(Spacer(1, 20))
    
    # Informations complémentaires
    if paiement.commentaire:
        content.append(Paragraph(_("Commentaire:"), heading_style))
        content.append(Paragraph(paiement.commentaire, normal_style))
        content.append(Spacer(1, 12))
    
    # Note légale
    content.append(Spacer(1, 30))
    content.append(Paragraph(
        _("Ce reçu fait office de justificatif de paiement. Conservez-le précieusement."),
        ParagraphStyle('Note', parent=normal_style, fontName='Helvetica-Oblique')
    ))
    
    # Générer le PDF
    doc.build(content)
    buffer.seek(0)
    
    # Créer la réponse HTTP
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response