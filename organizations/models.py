from django.db import models
from core.models import BaseModel
# Create your models here.


class Organization(BaseModel):
    name = models.CharField(max_length=150)
    tax_id = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)
    def __str__(self):
        return self.name

class Zone(BaseModel):
    Organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="zones",
    ) 
    name = models.CharField(max_lenght=120)
    limit_kwh= models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
    return f"{self.name} ({self.organization.name})"