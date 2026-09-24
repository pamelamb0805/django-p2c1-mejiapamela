from django.db import models
from core.models import BaseModel
# Create your models here.

# Creación de la tabla Organization -- Alexander
class Organization(BaseModel):
    organization_id = models.CharField(max_length=50, unique=True)
    legal_name = models.CharField(max_length=150)
    comercial_name = models.CharField(max_length=150, blank=True, null=True)
    contact = models.CharField(max_length=150, blank=True, null=True)
    email = models.EmailField(max_length=254)  # <--- Corregido el error tipográfico 'emai' por 'email'
    tax = models.CharField(max_length=50)
    status = models.BooleanField(default=True, blank=True, null=True)

    def __str__(self):
        return self.legal_name


# Creación de la tabla User -- Alexander
class User(BaseModel):
    user_id = models.CharField(max_length=50, unique=True)
    username = models.CharField(max_length=150)
    rut = models.CharField(max_length=20)
    phone = models.CharField(max_length=30, blank=True, null=True)
    email = models.EmailField(max_length=254)  #
    address = models.CharField(max_length=255, blank=True, null=True)
    role = models.CharField(max_length=50)
    status = models.BooleanField(default=True, blank=True, null=True)

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="users"
    )
    department = models.ForeignKey(
        "Department",
        on_delete=models.PROTECT,
        related_name="users",
        blank=True,
        null=True
    )

    def __str__(self):
        return self.username


# Creación de la tabla Department -- Alexander
class Department(BaseModel):
    department_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=150)
    description = models.CharField(max_length=255, blank=True, null=True)
    status = models.BooleanField(default=True, blank=True, null=True)
    
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="departments"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="user_departments",  # Evita colisión de nombres inversos
        blank=True,
        null=True
    )

    def __str__(self):
        return self.name


# Creación de la tabla Zone -- Alexander
class Zone(BaseModel):
    zone_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=150)
    description = models.CharField(max_length=255, blank=True, null=True)
    status = models.BooleanField(default=True, blank=True, null=True)
    
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="zones"
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="zones",
        blank=True,
        null=True
    )

    def __str__(self):
        return self.name