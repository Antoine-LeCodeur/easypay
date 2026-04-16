from django.contrib import admin

from .models import Historique, Utilisateur

admin.site.register(Utilisateur)
admin.site.register(Historique)
