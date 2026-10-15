from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

#dFALTA REVISAR dashboard subdividido por roles --> ppt1 paso 4 u2
#visitante
#usuario autenticado
# crear o reutilizar dashboard?
# proteger con login_required

@login_required #paso5 ppt1 -u2
def dashboard(request):
    profile = getattr(request.user, "profile", None)
    if profile is None:
        raise PermissionDenied("La cuenta no posee un perfil habilitado.")

    # #paso 7 guardar valor temp con request.session (revisar si el anterior cuenta u agregar otra con el CRUD) --> PTT1 U2
    visits = request.session.get("dashboard_visits",0)
    request.session["dashboard_visits"] = visits + 1

    return render(
        request,
        "dashboard/index.html",
        {
            "organization": profile.organization,
            "visits": visits + 1,
            "mode": request.session.get("dashboard_mode", "normal"),
            },
    )

       
@login_required
@require_POST
def remember_preference(request):
    request.session[
        "dashboard_mode"
    ] = "compact"
    #paso 8 mostrar al menos un mensaje con messages.succes  ppt1 -u2 
    #agregar otro mensaje segun crud
    messages.success(
        request,
    "Preferencia guardada correctamente.",
    )
    return redirect("dashboard:dashboard")

