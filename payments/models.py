import stripe

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models

from accounts.utils import get_stripe_customer_id
from core.constants import PY_REGISTERED, PY_STATUSES

User = get_user_model()
stripe.api_key = settings.STRIPE_SECRET_KEY


class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=9, decimal_places=4)
    description = models.CharField(max_length=300)
    stripe_payment_method = models.CharField(max_length=200)   # payment method id
    operation_id = models.CharField(max_length=300)
    status = models.CharField(max_length=100, choices=PY_STATUSES, default=PY_REGISTERED)
    payment_date = models.DateTimeField(auto_now_add=True)

    @classmethod
    def make_and_register(cls, user, amount, description, stripe_payment_method):
        """Return status(result of operation) and created payment instance or message (when error)"""
        # verify if there is a registered payment, not used before
        payment = cls.objects.filter(user=user, amount=amount, status=PY_REGISTERED).first()
        if not payment:
            # make payment and register it
            st_customer_id = get_stripe_customer_id(user)
            try:
                st_payment = stripe.PaymentIntent.create(amount=int(round(amount * 100, 0)),
                                                         currency='usd',
                                                         customer=st_customer_id,
                                                         payment_method=stripe_payment_method,
                                                         off_session=True,
                                                         confirm=True)
            except (stripe.error.InvalidRequestError, stripe.error.StripeError) as error:
                status = 'error'
                payment = error.user_message
            except Exception as ex:
                status = 'error'
                payment = str(ex)
            else:
                # register the charge made
                payment = cls.objects.create(user=user, amount=amount,
                                             stripe_payment_method=stripe_payment_method,
                                             description=description,
                                             operation_id=st_payment.get('id')
                                             )
                status = 'success'
        else:
            status = 'success'
        return status, payment
