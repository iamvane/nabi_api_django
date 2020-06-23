from django.contrib import admin
from django.db.models import Q

from core.models import User
from payments.models import Payment


class PaymentAdmin(admin.ModelAdmin):
    fields = ('user', 'amount', 'description', 'stripe_payment_method', 'operation_id', 'payment_date', 'status')
    list_display = ('pk', 'get_user_email', 'amount', 'status', 'payment_date')
    list_filter = ('status',)
    readonly_fields = ('payment_date',)

    def get_user_email(self, instance):
        return instance.user.email

    get_user_email.short_description = 'user email'
    get_user_email.admin_order_field = 'user__email'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'user':
            kwargs['queryset'] = User.objects.filter(Q(student__isnull=False) | Q(parent__isnull=False)
                                                     ).order_by('email')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


admin.site.register(Payment, PaymentAdmin)
