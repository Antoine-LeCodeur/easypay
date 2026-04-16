from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('index.html', views.index, name='index_html'),
    path('calendrier.html', views.calendrier, name='calendrier'),
    path('historique.html', views.historique, name='historique'),
    path('payes.html', views.payes, name='payes'),
    path('stat.html', views.stat, name='stat'),
    path('api/utilisateurs-by-service/', views.get_utilisateurs_by_service, name='utilisateurs_by_service'),
    path('api/utilisateur-detail/', views.get_utilisateur_detail, name='utilisateur_detail'),
]