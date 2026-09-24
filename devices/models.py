from django.db import models
from core.models import BaseModel
# Create your models here.

class Device(BaseModel):
    device_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    name = models.CharField(max_length=150, blank=True, null=True)
    
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="devices",
    )

    def __str__(self):
        return self.name


# Creación de la tabla Organization -- Alexander
class History(BaseModel):
    history_id = models.CharField(max_length=50, unique=True)
    start_date = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)
    reason = models.CharField(max_length=255, blank=True, null=True)

    device = models.ForeignKey(
        "Device",
        on_delete=models.PROTECT,
        related_name="histories"
    )
    
    zone = models.ForeignKey(
        "zones.Zone",
        on_delete=models.PROTECT,
        related_name="histories",
        blank=True,
        null=True
    )

    def __str__(self):
        return self.history_id


# Creación de la tabla Organization -- Alexander
# Falta creaciones de foreigKey
class MaintenanceRequest(BaseModel):
    maintenance_request_id = models.CharField(max_length=50, unique=True)
    type = models.CharField(max_length=100, blank=True, null=True)
    reason = models.CharField(max_length=255, blank=True, null=True)
    priority = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=50, blank=True, null=True)
    scheduled_date = models.DateTimeField(blank=True, null=True)
    actual_date = models.DateTimeField(blank=True, null=True)
    diagnosis = models.TextField(blank=True, null=True)
    actions_text = models.TextField(blank=True, null=True) # actions_taken según diagrama
    observations = models.TextField(blank=True, null=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    closed_at = models.DateTimeField(blank=True, null=True)
    
    device = models.ForeignKey(
        "Device",
        on_delete=models.PROTECT,
        related_name="maintenance_requests",
        blank=True,
        null=True
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="maintenance_requests"
    )

    def __str__(self):
        return self.maintenance_request_id