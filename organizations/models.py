from django.db import models
from core.models import BaseModel

# Creación de la tabla Organization -- Alexander
class Organization(BaseModel):
    organization_id = models.CharField(max_length=50, unique=True, verbose_name="Código de organización")
    legal_name = models.CharField(max_length=150, verbose_name="Razón social")
    comercial_name = models.CharField(max_length=150, blank=True, null=True, verbose_name="Nombre comercial")
    contact = models.CharField(max_length=150, blank=True, null=True, verbose_name="Contacto")
    email = models.EmailField(max_length=254, verbose_name="Correo electrónico")
    tax = models.CharField(max_length=50, verbose_name="Identificación fiscal (RUT/Tax ID)")
    status = models.BooleanField(default=True, blank=True, null=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Organización"
        verbose_name_plural = "Organizaciones"
        ordering = ["legal_name"]

    def __str__(self):
        return f"{self.tax} - {self.legal_name}"

# Creación de la tabla User -- Alexander
class User(BaseModel):
    user_id = models.CharField(max_length=50, unique=True, verbose_name="Código de usuario")
    username = models.CharField(max_length=150, verbose_name="Nombre de usuario")
    rut = models.CharField(max_length=20, verbose_name="RUT")
    phone = models.CharField(max_length=30, blank=True, null=True, verbose_name="Teléfono")
    email = models.EmailField(max_length=254, verbose_name="Correo electrónico")  
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name="Dirección")
    role = models.CharField(max_length=50, verbose_name="Rol")
    status = models.BooleanField(default=True, blank=True, null=True, verbose_name="Activo")

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="users",
        verbose_name="Organización"
    )
    department = models.ForeignKey(
        "Department",
        on_delete=models.PROTECT,
        related_name="users",
        blank=True,
        null=True,
        verbose_name="Departamento"
    )
    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        ordering = ["username"]

    def __str__(self):
        return f"{self.username} ({self.rut})"

# Creación de la tabla Department -- Alexander
class Department(BaseModel):
    department_id = models.CharField(max_length=50, unique=True, verbose_name="Código de departamento")
    name = models.CharField(max_length=150, verbose_name="Nombre del departamento")
    description = models.CharField(max_length=255, blank=True, null=True, verbose_name="Descripción")
    status = models.BooleanField(default=True, blank=True, null=True, verbose_name="Activo")
    
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="departments",
        verbose_name="Organización"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="user_departments",  # Evita colisión de nombres inversos
        blank=True,
        null=True,
        verbose_name="Encargado / Responsable"
    )

    class Meta:
        verbose_name = "Departamento"
        verbose_name_plural = "Departamentos"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.organization.legal_name if self.organization else 'Sin org'})"

# Creación de la tabla Zone -- Alexander
class Zone(BaseModel):
    zone_id = models.CharField(max_length=50, unique=True, verbose_name="Código de zona")
    name = models.CharField(max_length=150, verbose_name="Nombre de la zona")
    description = models.CharField(max_length=255, blank=True, null=True, verbose_name="Descripción")
    status = models.BooleanField(default=True, blank=True, null=True, verbose_name="Activa")
    
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="zones",
        verbose_name="Organización"
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="zones",
        blank=True,
        null=True,
        verbose_name="Departamento"
    )

    class Meta:
        verbose_name = "Zona"
        verbose_name_plural = "Zonas"
        ordering = ["name"]

    def __str__(self):
        dept_str = f" - {self.department.name}" if self.department else ""
        return f"{self.name} ({self.organization.legal_name}{dept_str})"