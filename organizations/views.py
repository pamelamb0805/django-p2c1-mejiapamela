from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.utils import timezone
from .models import Organization, Department, Zone


# ==========================================
# 1. ORGANIZACIONES (RF-01, RF-04)
# ==========================================

@login_required
def organization_list(request):
    """Listado general de organizaciones cliente (para administradores)."""
    if request.user.is_superuser:
        organizations = Organization.objects.filter(deleted_at__isnull=True)
    else:
        # Si es usuario normal, solo ve su propia organización
        profile = getattr(request.user, "profile", None)
        if profile and profile.organization:
            organizations = Organization.objects.filter(id=profile.organization.id, deleted_at__isnull=True)
        else:
            organizations = Organization.objects.none()
            
    return render(request, 'organizations/organization_list.html', {'organizations': organizations})


@login_required
def organization_detail(request, pk):
    """Detalle de la organización seleccionada."""
    organization = get_object_or_404(Organization, pk=pk, deleted_at__isnull=True)
    departments = Department.objects.filter(organization=organization, deleted_at__isnull=True)
    zones = Zone.objects.filter(organization=organization, deleted_at__isnull=True)
    
    context = {
        'organization': organization,
        'departments': departments,
        'zones': zones,
    }
    return render(request, 'organizations/organization_detail.html', context)


@login_required
def organization_create(request):
    """Creación de una nueva organización cliente (RF-01)."""
    if request.method == 'POST':
        legal_name = request.POST.get('legal_name')
        tax_identifier = request.POST.get('tax_identifier')
        commercial_name = request.POST.get('commercial_name')
        contact_email = request.POST.get('contact_email')
        
        Organization.objects.create(
            legal_name=legal_name,
            tax_identifier=tax_identifier,
            commercial_name=commercial_name,
            contact_email=contact_email
        )
        messages.success(request, "Organización creada exitosamente.")
        return redirect('organizations:organization_list')
        
    return render(request, 'organizations/organization_form.html')


@login_required
def organization_update(request, pk):
    """Actualización de datos de una organización."""
    organization = get_object_or_404(Organization, pk=pk, deleted_at__isnull=True)
    
    if request.method == 'POST':
        organization.legal_name = request.POST.get('legal_name', organization.legal_name)
        organization.tax_identifier = request.POST.get('tax_identifier', organization.tax_identifier)
        organization.commercial_name = request.POST.get('commercial_name', organization.commercial_name)
        organization.contact_email = request.POST.get('contact_email', organization.contact_email)
        organization.save()
        
        messages.success(request, "Datos de la organización actualizados correctamente.")
        return redirect('organizations:organization_detail', pk=organization.pk)
        
    return render(request, 'organizations/organization_form.html', {'organization': organization})


# ==========================================
# 2. DEPARTAMENTOS (RF-02, RN-02, RN-05)
# ==========================================

@login_required
def department_list(request):
    """Listado de departamentos filtrados por la organización del usuario (RN-01)."""
    profile = getattr(request.user, "profile", None)
    
    if request.user.is_superuser:
        departments = Department.objects.filter(deleted_at__isnull=True)
    elif profile and profile.organization:
        departments = Department.objects.filter(organization=profile.organization, deleted_at__isnull=True)
    else:
        departments = Department.objects.none()

    return render(request, 'organizations/department_list.html', {'departments': departments})


@login_required
def department_create(request):
    """Creación de departamentos dentro de la organización del usuario."""
    profile = getattr(request.user, "profile", None)
    organization = getattr(profile, "organization", None) if profile else None

    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        
        # Validación de nombre duplicado en el mismo contexto organizacional (RN-05)
        if Department.objects.filter(organization=organization, name=name, deleted_at__isnull=True).exists():
            messages.error(request, "Ya existe un departamento con ese nombre en tu organización.")
        else:
            Department.objects.create(
                organization=organization,
                name=name,
                description=description
            )
            messages.success(request, "Departamento registrado exitosamente.")
            return redirect('organizations:department_list')

    return render(request, 'organizations/department_form.html')


# ==========================================
# 3. ZONAS FÍSICAS (RF-03, RN-02, RN-05)
# ==========================================

@login_required
def zone_list(request):
    """Listado de zonas pertenecientes a la estructura interna de la organización."""
    profile = getattr(request.user, "profile", None)
    
    if request.user.is_superuser:
        zones = Zone.objects.filter(deleted_at__isnull=True)
    elif profile and profile.organization:
        zones = Zone.objects.filter(organization=profile.organization, deleted_at__isnull=True)
    else:
        zones = Zone.objects.none()

    return render(request, 'organizations/zone_list.html', {'zones': zones})


@login_required
def zone_create(request):
    """Creación de zonas asociadas a la organización y departamento opcional (RF-03)."""
    profile = getattr(request.user, "profile", None)
    organization = getattr(profile, "organization", None) if profile else None

    if request.method == 'POST':
        name = request.POST.get('name')
        limit_kwh = request.POST.get('limit_kwh', 0.0)
        department_id = request.POST.get('department_id')
        
        department = Department.objects.filter(id=department_id, organization=organization).first() if department_id else None

        # Validación RN-05 (nombres únicos dentro del contexto organizacional)
        if Zone.objects.filter(organization=organization, name=name, deleted_at__isnull=True).exists():
            messages.error(request, "Ya existe una zona con ese nombre en tu organización.")
        else:
            Zone.objects.create(
                organization=organization,
                department=department,
                name=name,
                limit_kwh=limit_kwh
            )
            messages.success(request, "Zona creada exitosamente.")
            return redirect('organizations:zone_list')

    departments = Department.objects.filter(organization=organization, deleted_at__isnull=True) if organization else []
    return render(request, 'organizations/zone_form.html', {'departments': departments})