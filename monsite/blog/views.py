from django.shortcuts import render


def index(request):
    return render(request, 'blog/index.html')


def calendrier(request):
    return render(request, 'blog/calendrier.html')


def historique(request):
    return render(request, 'blog/historique.html')


def payes(request):
    return render(request, 'blog/payes.html')


def stat(request):
    return render(request, 'blog/stat.html')