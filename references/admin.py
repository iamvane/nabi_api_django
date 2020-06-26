from django.contrib import admin
from django.contrib.auth import get_user_model

from .models import ReferenceRequest

User = get_user_model()


class ReferenceRequestAdmin(admin.ModelAdmin):
    fields = ('user', 'email')
    list_display = ('pk', 'get_user_email', 'get_reference_email')
    search_fields = ('user__email', )

    def get_user_email(self, obj):
        return '{email} (user_id: {id})'.format(email=obj.user.email, id=obj.user_id)

    def get_reference_email(self, obj):
        return obj.email

    get_user_email.short_description = 'user email'
    get_user_email.admin_order_field = 'user__email'
    get_reference_email.short_description = 'reference email'
    get_reference_email.admin_order_field = 'email'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'user':
            kwargs['queryset'] = User.objects.order_by('email')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


admin.site.register(ReferenceRequest, ReferenceRequestAdmin)
