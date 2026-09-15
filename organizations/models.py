from django.db import models
from core.models import BaseModel
# Create your models here.


class Organization(BaseModel):
    name = models.CharField(max_length=150)
    tax_id = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)
    def __str__(self):
        return self.name