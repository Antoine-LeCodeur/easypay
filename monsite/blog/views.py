from django.shortcuts import render, redirect

def home(request):
    return render(request, 'blog/home.html')

def submit_payroll(request):
    if request.method == 'POST':
        # Traiter les données du formulaire
        return redirect('confirmation')
    return redirect('home')

def confirmation(request):
    return render(request, 'blog/confirmation.html')