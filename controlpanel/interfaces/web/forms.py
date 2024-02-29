from django import forms

from controlpanel.core.models import Datasource


class DatasourceFormView(forms.ModelForm):
    class Meta:
        model = Datasource
        fields = ["name"]

    def __init__(self, *args, **kwargs) -> None:
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)

    def save(self, commit: bool = True) -> Datasource:
        obj = super().save(commit=False)
        obj.user = self.user
        obj.save()
        return obj


class DatasourceQuicksightForm(forms.ModelForm):
    class Meta:
        model = Datasource
        fields = ["is_quicksight_enabled"]
        labels = {"is_quicksight_enabled": "Enabled for use in Quicksight"}
