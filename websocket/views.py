from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .services import CHAT_MAX_LENGTH, publish_chat_message


@login_required
def chat_view(request):
    """
    Vista protegida para renderizar la sala de chat del WebSocket.
    Requiere que el usuario haya iniciado sesión.
    """
    return render(request, 'websocket/chat.html', {
        'user': request.user,
        'max_length': CHAT_MAX_LENGTH,
    })


# Clase 11 --> PM
# El formulario del chat envía el mensaje por HTTP (POST + CSRF). La vista solo valida;
# publicar lo hace el servicio y entregarlo a cada navegador lo hace el Consumer por WebSocket.
@login_required
@require_POST
def send_message(request):
    # La organización sale del perfil del usuario autenticado: el navegador NO la elige.
    try:
        org_id = request.user.profile.organization_id
    except ObjectDoesNotExist:
        org_id = None

    if org_id is None:
        return JsonResponse({"error": "Sin organización"}, status=403)

    message = request.POST.get("message", "").strip()
    if not 1 <= len(message) <= CHAT_MAX_LENGTH:
        return JsonResponse({"error": "Mensaje inválido"}, status=400)

    publish_chat_message(request.user, org_id, message)
    return JsonResponse({"ok": True})