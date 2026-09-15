from django.db import models
from core.models import BaseModel

# Create your models here.
class Device(BaseModel):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="devices",
    )
    zone = models.ForeignKey(
        "organizations.Zone",
        on_delete=models.PROTECT,
        related_name="devices",
    )
    name = models.CharField(max_length=120)
    serial_number = models.CharField(max_length=80, unique=True)
