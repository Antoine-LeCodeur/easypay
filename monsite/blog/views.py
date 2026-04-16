from django.shortcuts import render
from django.core import serializers
from .models import Utilisateur
import json


def index(request):
    return render(request, 'blog/index.html')


def calendrier(request):
    return render(request, 'blog/calendrier.html')


def historique(request):
    return render(request, 'blog/historique.html')


def payes(request):
    utilisateurs = Utilisateur.objects.all()
    services = Utilisateur.objects.values_list('service', flat=True).distinct()
    
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


def stat(request):
    return render(request, 'blog/stat.html')