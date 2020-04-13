from django.contrib import admin
from django.contrib.auth import get_user_model

from accounts.serializers import (InstructorCreateAccountSerializer, ParentCreateAccountSerializer,
                                  StudentCreateAccountSerializer)

from .constants import BENEFIT_PENDING, ROLE_INSTRUCTOR, ROLE_PARENT, ROLE_STUDENT
from .forms import CreateUserForm
from .models import UserBenefits
from .utils import generate_random_password

User = get_user_model()


class ProfileListFilter(admin.SimpleListFilter):
    title = 'Profile Type'
    parameter_name = 'profile'

    def lookups(self, request, model_admin):
        return (
            ('instructor', 'Instructor'),
            ('parent', 'Parent'),
            ('student', 'Student'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'instructor':
            return queryset.filter(instructor__isnull=False)
        if self.value() == 'parent':
            return queryset.filter(parent__isnull=False)
        if self.value() == 'student':
            return queryset.filter(student__isnull=False)


class UserAdmin(admin.ModelAdmin):
    """Copied from django.contrib.auth.admin.UserAdmin"""
    fieldsets = (
        (None, {'fields': ('email', 'first_name', 'last_name', 'profile',)}),
        ('Permissions', {'fields': ('is_superuser', 'is_active',)}),
        ('Refer info', {'fields': ('referral_token', 'referred_by',)}),
    )
    add_fieldsets = (
        (None, {'fields': ('email', 'first_name', 'last_name',)}),
        ('Additional data', {'fields': ('role', 'birthday', 'referringCode',)}),
    )
    list_display = ('pk', 'email', 'first_name', 'last_name', 'profile', 'is_active',)
    list_filter = ('is_active', ProfileListFilter,)
    search_fields = ('email', 'first_name', 'last_name',)
    readonly_fields = ('profile', 'referral_token', 'referred_by',)
    ordering = ('pk',)
    add_form = CreateUserForm

    def profile(self, instance):
        return instance.get_role()

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)

    def get_form(self, request, obj=None, **kwargs):
        """
        Use special form during user creation
        """
        defaults = {}
        if obj is None:
            defaults['form'] = self.add_form
        defaults.update(kwargs)
        return super().get_form(request, obj, **defaults)

    def save_model(self, request, obj, form, change):
        if not change:
            role = form.cleaned_data.pop('role')
            form.cleaned_data['password'] = generate_random_password(10)
            if role == ROLE_INSTRUCTOR:
                ser = InstructorCreateAccountSerializer(data=form.cleaned_data)
            if role == ROLE_PARENT:
                ser = ParentCreateAccountSerializer(data=form.cleaned_data)
            if role == ROLE_STUDENT:
                ser = StudentCreateAccountSerializer(data=form.cleaned_data)
            if ser.is_valid():
                ser.save()
            else:
                raise Exception(f'{ser.errors}')
        else:
            super().save_model(request, obj, form, change)


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


admin.site.register(User, UserAdmin)
admin.site.register(UserBenefits, UserBenefitsAdmin)
