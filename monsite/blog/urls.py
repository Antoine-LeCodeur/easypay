from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('submit_payroll/', views.submit_payroll, name='submit_payroll'),
    path('confirmation/', views.confirmation, name='confirmation'),
]