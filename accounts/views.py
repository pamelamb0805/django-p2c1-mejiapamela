from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages

def registro(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'El nombre de usuario ya está en uso.')
        else:
            User.objects.create_user(username=username, email=email, password=password)
            messages.success(request, '¡Cuenta creada con éxito!')
            # Redirige a la URL nombrada 'login' (/accounts/login/)
            return redirect('login')
            
    return render(request, 'registration/registro.html')