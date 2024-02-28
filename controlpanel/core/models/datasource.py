from django.db import models


class Datasource(models.Model):
    name = models.CharField(max_length=255)
    user = models.ForeignKey(to="core.User", on_delete=models.CASCADE)

    def __str__(self) -> str:
        return self.name
