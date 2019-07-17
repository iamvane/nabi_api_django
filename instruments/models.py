from django.db import models


class Instrument(models.Model):
    name = models.CharField(max_length=250)
