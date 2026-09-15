from django.db import models
from core.models import BaseModel

# Create your models here.
class Device(BaseModel):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="devices",
    )
