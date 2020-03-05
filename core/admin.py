from django.contrib import admin

from core.constants import BENEFIT_PENDING

from .models import UserBenefits


class BuggedDependentBenefitFilter(admin.SimpleListFilter):
    title = 'dependent benefit without relation'
    parameter_name = 'depends_on'

    def lookups(self, request, model_admin):
        return (
            ('with', 'with depends_on value'),
            ('without', 'without depends_on value'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'with':
            return queryset.filter(provider__isnull=False, status=BENEFIT_PENDING, depends_on__isnull=False)
        if self.value() == 'without':
            return queryset.filter(provider__isnull=False, status=BENEFIT_PENDING, depends_on__isnull=True)


class UserBenefitsAdmin(admin.ModelAdmin):
    readonly_fields = ('created_at', 'modified_at')
    list_display = ('pk', 'benefit_type', 'beneficiary', 'provider', 'status', )
    list_filter = ('benefit_type', 'status', BuggedDependentBenefitFilter)
    ordering = ('pk',)
    search_fields = ('beneficiary__email', 'provider__email')


admin.site.register(UserBenefits, UserBenefitsAdmin)
