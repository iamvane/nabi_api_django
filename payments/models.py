from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=9, decimal_places=4)
    description = models.CharField(max_length=300)
    charge_id = models.CharField(max_length=300)
    payment_date = models.DateTimeField(auto_now_add=True)
