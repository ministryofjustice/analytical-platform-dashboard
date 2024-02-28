from django.db import models
from django.urls import reverse


class Datasource(models.Model):
    name = models.CharField(max_length=255)
    user = models.ForeignKey(to="core.User", on_delete=models.CASCADE)
    is_quicksight_enabled = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self):
        return reverse("datasources-manage", kwargs={"pk": self.pk})
