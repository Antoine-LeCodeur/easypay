from decimal import Decimal, InvalidOperation

from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from .models import Historique, Utilisateur
import json


def index(request):
    return render(request, 'blog/index.html')


def calendrier(request):
    return render(request, 'blog/calendrier.html')


def historique(request):
    return render(request, 'blog/historique.html')


@ensure_csrf_cookie
def payes(request):
    today = timezone.localdate()
    utilisateurs_enregistres = Historique.objects.filter(
        mois=today.month,
        annee=today.year,
    ).values_list('utilisateur_id', flat=True)
    utilisateurs = Utilisateur.objects.exclude(id__in=utilisateurs_enregistres)
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
    
    context = {
        'utilisateurs': utilisateurs,
        'services': services,
        'utilisateurs_json': utilisateurs_json
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
    
    # Noms des mois en français
    mois_noms = {
        1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril", 5: "Mai", 6: "Juin",
        7: "Juillet", 8: "Août", 9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"
    }
    
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
        'mois': mois_noms.get(mois, 'Mois inconnu'),
        'prime_totale': prime_totale,
        'heures_sup_totale': heures_sup_totale,
        'total_payes': total_payes,
        'total_salaire': total_salaire,
        'salaire_moyen': salaire_moyen
    }
    return render(request, 'blog/stat.html', context)