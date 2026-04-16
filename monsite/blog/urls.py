from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('index.html', views.index, name='index_html'),
    path('calendrier.html', views.calendrier, name='calendrier'),
    path('historique.html', views.historique, name='historique'),
    path('payes.html', views.payes, name='payes'),
    path('payes/enregistrer', views.enregistrer_paye, name='enregistrer_paye'),
    path('stat.html', views.stat, name='stat'),
]