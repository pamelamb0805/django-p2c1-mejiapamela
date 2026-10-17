from django.shortcuts import render

def home_view(request):
    """Vista para la página de inicio que usa el home.html global de la estructura."""
    return render(request, 'home.html')
