from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def chat_view(request):
    """
    Vista protegida para renderizar la sala de chat del WebSocket.
    Requiere que el usuario haya iniciado sesión.
    """
    return render(request, 'websocket/chat.html', {
        'user': request.user
    })