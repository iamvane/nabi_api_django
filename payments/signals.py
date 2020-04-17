from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import UserPaymentMethod


@receiver(pre_save, sender=UserPaymentMethod)
def set_main_payment_method(sender, instance, **kwargs):
    UserPaymentMethod.objects.filter(user=instance.user).exclude(id=instance.id).update(is_main=False)
    instance.is_main = True
