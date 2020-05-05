from django.contrib.auth import get_user_model
from django.db import models

from core.constants import PY_REGISTERED, PY_STATUSES

User = get_user_model()


class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=9, decimal_places=4)
    description = models.CharField(max_length=300)
    stripe_payment_method = models.CharField(max_length=200)
    operation_id = models.CharField(max_length=300)
    status = models.CharField(max_length=100, choices=PY_STATUSES, default=PY_REGISTERED)
    payment_date = models.DateTimeField(auto_now_add=True)
