from django.contrib.auth import get_user_model
from django.db import models

from core.constants import PY_APPLIED, PY_STATUSES

User = get_user_model()


class UserPaymentMethod(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_methods')
    stripe_payment_method_id = models.CharField(max_length=200)
    is_main = models.BooleanField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    payment_method = models.ForeignKey(UserPaymentMethod, blank=True, null=True,
                                       on_delete=models.SET_NULL, related_name='charges')
    amount = models.DecimalField(max_digits=9, decimal_places=4)
    description = models.CharField(max_length=300)
    operation_id = models.CharField(max_length=300)
    status = models.CharField(max_length=100, choices=PY_STATUSES, default=PY_APPLIED)
    payment_date = models.DateTimeField(auto_now_add=True)
