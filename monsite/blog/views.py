from decimal import Decimal, InvalidOperation
from io import BytesIO

from django.db import IntegrityError
from django.http import JsonResponse, FileResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from django.core.mail import EmailMessage

from .models import Historique, Utilisateur
import json

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# Constantes
MOIS_NOMS = {
    1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril", 5: "Mai", 6: "Juin",
    7: "Juillet", 8: "Août", 9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"
}
TAUX_HEURE_SUP = 100


def index(request):
    return render(request, 'blog/index.html')


def calendrier(request):
    return render(request, 'blog/calendrier.html')


def historique(request):
    # Récupérer les paramètres de filtrage
    nom_filter = request.GET.get('nom', '')
    service_filter = request.GET.get('service', '')
    mois_filter = request.GET.get('mois', '')
    
    # Récupérer tous les utilisateurs et services pour les selects
    utilisateurs = Utilisateur.objects.all()
    services = Utilisateur.objects.values_list('service', flat=True).distinct()
    noms = Utilisateur.objects.values_list('nomprenom', flat=True).distinct().order_by('nomprenom')
    
    # Récupérer les historiques
    historiques = Historique.objects.select_related('utilisateur').all()
    
    # Appliquer les filtres
    if nom_filter and nom_filter != '':
        historiques = historiques.filter(utilisateur__nomprenom=nom_filter)
    
    if service_filter and service_filter != '':
        historiques = historiques.filter(utilisateur__service=service_filter)
    
    if mois_filter and mois_filter != '' and mois_filter.isdigit():
        historiques = historiques.filter(mois=int(mois_filter))
    
    # Ordonner par date décroissante
    historiques = historiques.order_by('-date', '-heure')
    
    context = {
        'historiques': historiques,
        'utilisateurs': utilisateurs,
        'services': services,
        'noms': noms,
        'nom_filter': nom_filter,
        'service_filter': service_filter,
        'mois_filter': mois_filter
    }
    return render(request, 'blog/historique.html', context)


@ensure_csrf_cookie
def payes(request):
    today = timezone.localdate()
    historique_id = request.GET.get("historique_id")
    historique_selectionne = None
    if historique_id:
        try:
            historique_id = int(historique_id)
        except (TypeError, ValueError):
            historique_id = None

    if historique_id:
        try:
            historique_selectionne = Historique.objects.select_related("utilisateur").get(id=historique_id)
        except Historique.DoesNotExist:
            historique_selectionne = None

    utilisateurs_enregistres = Historique.objects.filter(
        mois=today.month,
        annee=today.year,
    ).values_list('utilisateur_id', flat=True)
    utilisateurs = Utilisateur.objects.exclude(id__in=utilisateurs_enregistres)

    if historique_selectionne:
        utilisateurs = (
            utilisateurs
            | Utilisateur.objects.filter(id=historique_selectionne.utilisateur_id)
        ).distinct()

    services = utilisateurs.values_list('service', flat=True).distinct()
    
    # Convertir les utilisateurs en JSON
    utilisateurs_json = json.dumps([
        {
            'id': u.id,
            'nomprenom': u.nomprenom,
            'service': u.service,
            'paye': str(u.paye)
        }
        for u in utilisateurs
    ])

    historique_json = None
    if historique_selectionne:
        historique_json = json.dumps({
            'id': historique_selectionne.id,
            'utilisateur_id': historique_selectionne.utilisateur_id,
            'nomprenom': historique_selectionne.utilisateur.nomprenom,
            'service': historique_selectionne.utilisateur.service,
            'prime': str(historique_selectionne.prime),
            'heures_sup': str(historique_selectionne.heures_sup),
            'mois': historique_selectionne.mois,
            'annee': historique_selectionne.annee,
        })
    
    context = {
        'utilisateurs': utilisateurs,
        'services': services,
        'utilisateurs_json': utilisateurs_json,
        'historique_json': historique_json,
    }
    return render(request, 'blog/payes.html', context)


@require_POST
def enregistrer_paye(request):
    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Donnees invalides."}, status=400)

    utilisateur_id = payload.get("utilisateur_id")
    if not utilisateur_id:
        return JsonResponse({"error": "Utilisateur requis."}, status=400)

    try:
        utilisateur_id = int(utilisateur_id)
    except (TypeError, ValueError):
        return JsonResponse({"error": "Utilisateur invalide."}, status=400)

    try:
        utilisateur = Utilisateur.objects.get(id=utilisateur_id)
    except Utilisateur.DoesNotExist:
        return JsonResponse({"error": "Utilisateur introuvable."}, status=404)

    utilisateur_nom = payload.get("utilisateur_nom")
    if utilisateur_nom and utilisateur.nomprenom != utilisateur_nom:
        return JsonResponse({"error": "Nom utilisateur invalide."}, status=400)

    prime = payload.get("prime", 0)
    heures_sup = payload.get("heures_sup", 0)

    try:
        prime_value = Decimal(str(prime))
    except (InvalidOperation, TypeError, ValueError):
        return JsonResponse({"error": "Prime invalide."}, status=400)

    try:
        heures_sup_value = Decimal(str(heures_sup))
    except (InvalidOperation, TypeError, ValueError):
        return JsonResponse({"error": "Heures sup invalides."}, status=400)

    if prime_value < 0 or heures_sup_value < 0:
        return JsonResponse({"error": "Valeurs negatives interdites."}, status=400)

    historique_id = payload.get("historique_id")
    if historique_id:
        try:
            historique_id = int(historique_id)
        except (TypeError, ValueError):
            return JsonResponse({"error": "Historique invalide."}, status=400)

        try:
            historique = Historique.objects.select_related("utilisateur").get(id=historique_id)
        except Historique.DoesNotExist:
            return JsonResponse({"error": "Historique introuvable."}, status=404)

        if historique.utilisateur_id != utilisateur_id:
            return JsonResponse({"error": "Utilisateur invalide pour cet historique."}, status=400)

        historique.prime = prime_value
        historique.heures_sup = heures_sup_value
        historique.save(update_fields=["prime", "heures_sup"])

        return JsonResponse({"ok": True, "historique_id": historique.pk, "updated": True})

    today = timezone.localdate()
    if Historique.objects.filter(utilisateur_id=utilisateur_id, mois=today.month, annee=today.year).exists():
        return JsonResponse({"error": "Utilisateur deja enregistre pour ce mois."}, status=409)

    try:
        historique = Historique.objects.create(
            utilisateur_id=utilisateur_id,
            prime=prime_value,
            heures_sup=heures_sup_value,
            mois=today.month,
            annee=today.year,
        )
    except IntegrityError:
        return JsonResponse({"error": "Utilisateur deja enregistre pour ce mois."}, status=409)

    return JsonResponse({"ok": True, "historique_id": historique.pk})


def stat(request):
    mois_param = request.GET.get('mois')
    today = timezone.localdate()
    
    # Déterminer le mois à afficher
    if mois_param:
        try:
            mois = int(mois_param)
            if mois < 1 or mois > 12:
                mois = today.month
        except (ValueError, TypeError):
            mois = today.month
    else:
        mois = today.month
    
    # Récupérer les statistiques du mois
    historiques = Historique.objects.filter(mois=mois, annee=today.year)
    
    # Calculer les statistiques
    prime_totale = sum(Decimal(str(h.prime)) for h in historiques)
    heures_sup_totale = sum(Decimal(str(h.heures_sup)) for h in historiques)
    total_payes = historiques.count()
    
    # Calculer le salaire total (somme des salaires de base + primes + heures sup)
    total_salaire = Decimal('0')
    for h in historiques:
        salaire_base = Decimal(str(h.utilisateur.paye))
        prime = Decimal(str(h.prime))
        # Supposer un taux horaire de 15€ par heure supplémentaire
        heures_sup_value = Decimal(str(h.heures_sup)) * Decimal('15')
        total_salaire += salaire_base + prime + heures_sup_value
    
    salaire_moyen = total_salaire / total_payes if total_payes > 0 else Decimal('0')
    
    context = {
        'mois': MOIS_NOMS.get(mois, 'Mois inconnu'),
        'prime_totale': prime_totale,
        'heures_sup_totale': heures_sup_totale,
        'total_payes': total_payes,
        'total_salaire': total_salaire,
        'salaire_moyen': salaire_moyen
    }
    return render(request, 'blog/stat.html', context)


def generer_fiche_paye_pdf(utilisateur, prime, heures_sup):
    """Génère le contenu PDF d'une fiche de paye"""
    # Calcul du salaire
    salaire_base = float(utilisateur.paye)
    taux_heure_sup = 100
    salaire_hs = heures_sup * taux_heure_sup
    salaire_brut = salaire_base + prime + salaire_hs
    
    # Cotisations sociales (approximation France)
    cotisation_salariale = salaire_brut * 0.08  # 8% approximation
    salaire_net = salaire_brut - cotisation_salariale

    # Créer le PDF
    buffer = BytesIO()
    
    # Config page
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4,
        rightMargin=0.8*cm,
        leftMargin=0.8*cm,
        topMargin=0.8*cm,
        bottomMargin=0.8*cm
    )
    
    styles = getSampleStyleSheet()
    elements = []
    
    # ===== EN-TÊTE =====
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#1f4788'),
        fontName='Helvetica-Bold',
        spaceAfter=3,
    )
    
    # Logo/Titre entreprise
    elements.append(Paragraph("<b>EasyPay SARL</b>", ParagraphStyle(
        'CompanyName',
        parent=styles['Normal'],
        fontSize=16,
        textColor=colors.HexColor('#1f4788'),
        fontName='Helvetica-Bold',
    )))
    elements.append(Paragraph("123 Rue de la Paie, 75000 Paris<br/>Tél: 01.23.45.67.89 | Email: contact@easypay.fr", 
        ParagraphStyle('CompanyInfo', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER)))
    elements.append(Spacer(1, 0.5*cm))
    
    # Ligne de séparation
    hr_table = Table([[''], ], colWidths=[19*cm])
    hr_table.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (0, 0), 2, colors.HexColor('#1f4788')),
    ]))
    elements.append(hr_table)
    elements.append(Spacer(1, 0.3*cm))
    
    # Titre
    elements.append(Paragraph("<b>BULLETIN DE SALAIRE</b>", ParagraphStyle(
        'Title',
        parent=styles['Normal'],
        fontSize=14,
        textColor=colors.HexColor('#1f4788'),
        fontName='Helvetica-Bold',
        alignment=TA_CENTER,
    )))
    elements.append(Spacer(1, 0.3*cm))
    
    # ===== INFORMATIONS EMPLOYÉ ET PÉRIODE =====
    today = timezone.localdate()
    
    info_data = [
        ["Nom et Prénom:", utilisateur.nomprenom, "", "Période:", f"{MOIS_NOMS.get(today.month)} {today.year}"],
        ["Service:", utilisateur.service, "", "Date émission:", today.strftime("%d/%m/%Y")],
        ["Email:", utilisateur.mail, "", ""],
    ]
    
    info_table = Table(info_data, colWidths=[3*cm, 5*cm, 1*cm, 3.5*cm, 5*cm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1f4788')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.4*cm))
    
    # ===== TABLEAU RÉMUNÉRATION =====
    elements.append(Paragraph("<b>DÉTAIL DU SALAIRE</b>", ParagraphStyle(
        'SectionTitle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#1f4788'),
        fontName='Helvetica-Bold',
    )))
    elements.append(Spacer(1, 0.15*cm))
    
    remu_data = [
        ["ÉLÉMENT", "QUANTITÉ", "TAUX", "MONTANT"],
        ["Salaire de base", "1", f"{salaire_base:.2f} €", f"{salaire_base:.2f} €"],
        ["Heures supplémentaires", f"{heures_sup:.2f}h", f"{taux_heure_sup:.2f} €/h", f"{salaire_hs:.2f} €"],
        ["Prime", "1", "-", f"{prime:.2f} €"],
        ["", "", "", ""],
        ["TOTAL BRUT", "", "", f"{salaire_brut:.2f} €"],
    ]
    
    remu_table = Table(remu_data, colWidths=[6*cm, 3.5*cm, 3*cm, 3*cm])
    remu_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 5), (-1, 5), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 5), (-1, 5), colors.HexColor('#e8f0f8')),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, 4), 1, colors.HexColor('#cccccc')),
        ('GRID', (0, 5), (-1, 5), 1, colors.HexColor('#1f4788')),
        ('LINEABOVE', (0, 4), (-1, 4), 1, colors.HexColor('#cccccc')),
    ]))
    elements.append(remu_table)
    elements.append(Spacer(1, 0.3*cm))
    
    # ===== TABLEAU RETENUES =====
    elements.append(Paragraph("<b>RETENUES ET COTISATIONS</b>", ParagraphStyle(
        'SectionTitle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#1f4788'),
        fontName='Helvetica-Bold',
    )))
    elements.append(Spacer(1, 0.15*cm))
    
    retenues_data = [
        ["DÉSIGNATION", "BASE", "TAUX", "MONTANT"],
        ["Cotisations sociales salariales", f"{salaire_brut:.2f} €", "8.0%", f"{cotisation_salariale:.2f} €"],
        ["", "", "", ""],
        ["TOTAL RETENUES", "", "", f"{cotisation_salariale:.2f} €"],
    ]
    
    retenues_table = Table(retenues_data, colWidths=[6*cm, 3.5*cm, 3*cm, 3*cm])
    retenues_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ff6b6b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 3), (-1, 3), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#ffe8e8')),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, 2), 1, colors.HexColor('#cccccc')),
        ('GRID', (0, 3), (-1, 3), 1, colors.HexColor('#ff6b6b')),
        ('LINEABOVE', (0, 2), (-1, 2), 1, colors.HexColor('#cccccc')),
    ]))
    elements.append(retenues_table)
    elements.append(Spacer(1, 0.3*cm))
    
    # ===== RÉSUMÉ FINAL =====
    resume_data = [
        ["Salaire brut", f"{salaire_brut:.2f} €"],
        ["Retenues", f"- {cotisation_salariale:.2f} €"],
        ["SALAIRE NET À PAYER", f"{salaire_net:.2f} €"],
    ]
    
    resume_table = Table(resume_data, colWidths=[14*cm, 4*cm])
    resume_styles = [
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8f0f8')),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#ffe8e8')),
        ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#e8f8e8')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#1f4788')),
    ]
    resume_table.setStyle(TableStyle(resume_styles))
    elements.append(resume_table)
    
    elements.append(Spacer(1, 0.5*cm))
    
    # ===== PIED DE PAGE =====
    elements.append(Paragraph("<i>Ce bulletin de salaire a été généré par EasyPay. Les cotisations affichées sont approximatives.</i>", 
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=TA_CENTER)))
    
    # Générer le PDF
    doc.build(elements)
    buffer.seek(0)
    
    return buffer


@require_POST
def telecharger_fiche_paye(request):
    """Génère et télécharge une fiche de paye professionnelle en PDF"""
    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Donnees invalides."}, status=400)

    utilisateur_id = payload.get("utilisateur_id")
    if not utilisateur_id:
        return JsonResponse({"error": "Utilisateur requis."}, status=400)

    try:
        utilisateur_id = int(utilisateur_id)
    except (TypeError, ValueError):
        return JsonResponse({"error": "Utilisateur invalide."}, status=400)

    try:
        utilisateur = Utilisateur.objects.get(id=utilisateur_id)
    except Utilisateur.DoesNotExist:
        return JsonResponse({"error": "Utilisateur introuvable."}, status=404)

    prime = float(payload.get("prime", 0))
    heures_sup = float(payload.get("heures_sup", 0))

    # Générer le PDF
    buffer = generer_fiche_paye_pdf(utilisateur, prime, heures_sup)
    
    today = timezone.localdate()
    
    # Retourner le PDF en téléchargement
    nom_fichier = f"Fiche_Paye_{utilisateur.nomprenom}_{today.month}_{today.year}.pdf"
    response = FileResponse(buffer, as_attachment=True, filename=nom_fichier)
    response['Content-Type'] = 'application/pdf'
    return response


@require_POST
def envoyer_fiche_paye(request):
    """Génère et envoie une fiche de paye par email"""
    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Donnees invalides."}, status=400)

    utilisateur_id = payload.get("utilisateur_id")
    if not utilisateur_id:
        return JsonResponse({"error": "Utilisateur requis."}, status=400)

    try:
        utilisateur_id = int(utilisateur_id)
    except (TypeError, ValueError):
        return JsonResponse({"error": "Utilisateur invalide."}, status=400)

    try:
        utilisateur = Utilisateur.objects.get(id=utilisateur_id)
    except Utilisateur.DoesNotExist:
        return JsonResponse({"error": "Utilisateur introuvable."}, status=404)

    prime = float(payload.get("prime", 0))
    heures_sup = float(payload.get("heures_sup", 0))

    try:
        # Générer le PDF
        buffer = generer_fiche_paye_pdf(utilisateur, prime, heures_sup)
        
        today = timezone.localdate()
        
        # Préparer l'email
        sujet = f"Fiche de paye - {MOIS_NOMS.get(today.month)} {today.year}"
        message = f"""Bonjour {utilisateur.nomprenom},

Veuillez trouver ci-joint votre fiche de paye pour le mois de {MOIS_NOMS.get(today.month).lower()} {today.year}.

Cordialement,
EasyPay"""
        
        email = EmailMessage(
            subject=sujet,
            body=message,
            from_email='easypayofficial92i@gmail.com',
            to=[utilisateur.mail]
        )
        
        # Ajouter la pièce jointe PDF
        nom_fichier = f"Fiche_Paye_{utilisateur.nomprenom}_{today.month}_{today.year}.pdf"
        buffer.seek(0)
        email.attach(nom_fichier, buffer.read(), 'application/pdf')
        
        # Envoyer l'email
        email.send()
        
        return JsonResponse({"ok": True, "message": f"Email envoyé à {utilisateur.mail}"})
    
    except Exception as e:
        return JsonResponse({"error": f"Erreur lors de l'envoi: {str(e)}"}, status=500)