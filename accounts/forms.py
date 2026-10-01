#UserProfileAdminForm con el clean()
#correccion eva2-n3
from django import forms

from .models import UserProfile


class UserProfileAdminForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        organization = cleaned_data.get("organization")
        department = cleaned_data.get("department")

        # El departamento debe pertenecer a la organización elegida
        if (
            organization
            and department
            and department.organization_id != organization.id
        ):
            self.add_error(
                "department",
                "El departamento debe pertenecer a la organización seleccionada.",
            )
        return cleaned_data
    
