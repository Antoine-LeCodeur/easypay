from django import template
from decimal import Decimal

register = template.Library()

MOIS_NOMS = {
    1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril", 5: "Mai", 6: "Juin",
    7: "Juillet", 8: "Août", 9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"
}

@register.filter
def mois_name(mois_number):
    """Retourne le nom du mois en français"""
    return MOIS_NOMS.get(int(mois_number), "Mois inconnu")

@register.filter
def salaire_total(historique):
    """Calcule le salaire total : salaire_base + prime + (heures_sup * 100)"""
    salaire_base = Decimal(str(historique.utilisateur.paye))
    prime = Decimal(str(historique.prime))
    heures_sup_bonus = Decimal(str(historique.heures_sup)) * Decimal('100')
    total = salaire_base + prime + heures_sup_bonus
    return "{:.2f}".format(total)

