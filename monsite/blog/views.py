from django.shortcuts import render
from django.http import JsonResponse
from .models import Utilisateur


def index(request):
    return render(request, 'blog/index.html')


def calendrier(request):
    return render(request, 'blog/calendrier.html')


def historique(request):
    return render(request, 'blog/historique.html')


def payes(request):
    utilisateurs = Utilisateur.objects.all()
    services = Utilisateur.objects.values_list('service', flat=True).distinct()
    
    context = {
        'utilisateurs': utilisateurs,
        'services': services
    }
    return render(request, 'blog/payes.html', context)


def get_utilisateurs_by_service(request):
    service = request.GET.get('service', 'tous')
    
    if service == 'tous':
        utilisateurs = Utilisateur.objects.all()
    else:
        utilisateurs = Utilisateur.objects.filter(service=service)
    
    data = [
        {
            'id': u.id,
            'nomprenom': u.nomprenom,
            'service': u.service,
            'paye': str(u.paye)
        }
        for u in utilisateurs
    ]
    return JsonResponse(data, safe=False)


def get_utilisateur_detail(request):
    utilisateur_id = request.GET.get('id')
    
    try:
        utilisateur = Utilisateur.objects.get(id=utilisateur_id)
        data = {
            'nomprenom': utilisateur.nomprenom,
            'service': utilisateur.service,
            'mail': utilisateur.mail,
            'paye': str(utilisateur.paye)
        }
        return JsonResponse(data)
    except Utilisateur.DoesNotExist:
        return JsonResponse({'error': 'Utilisateur non trouvé'}, status=404)


def stat(request):
    return render(request, 'blog/stat.html')