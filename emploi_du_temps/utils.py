from io import BytesIO
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from datetime import datetime

def generer_pdf_emploi(request):
    """Génère un PDF de l'emploi du temps"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=1,
        spaceAfter=30
    )
    
    # Titre
    titre = Paragraph("Emploi du temps - Centre de Formation", title_style)
    elements.append(titre)
    elements.append(Spacer(1, 0.5*cm))
    
    # Date de génération
    date_gen = Paragraph(f"Généré le {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal'])
    elements.append(date_gen)
    elements.append(Spacer(1, 1*cm))
    
    # Tableau des séances
    from .models import Seance
    seances = Seance.objects.all().order_by('date', 'heure_debut')[:50]  # Limite à 50 séances
    
    data = [['Date', 'Heure', 'Groupe', 'Professeur', 'Salle', 'Matière']]
    
    for seance in seances:
        data.append([
            seance.date.strftime('%d/%m/%Y'),
            f"{seance.heure_debut.strftime('%H:%M')} - {seance.heure_fin.strftime('%H:%M')}",
            seance.groupe.nom,
            seance.groupe.professeur.nom_complet,
            seance.salle.nom,
            seance.groupe.matiere.nom
        ])
    
    table = Table(data, colWidths=[4*cm, 4*cm, 3*cm, 4*cm, 3*cm, 4*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    elements.append(table)
    
    # Générer le PDF
    doc.build(elements)
    
    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf')