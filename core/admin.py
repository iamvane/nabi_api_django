from django.contrib import admin
from django.contrib.auth import get_user_model

from accounts.models import PhoneNumber
from accounts.serializers import (InstructorCreateAccountSerializer, ParentCreateAccountSerializer,
                                  StudentCreateAccountSerializer)

from .constants import BENEFIT_PENDING, ROLE_INSTRUCTOR, ROLE_PARENT, ROLE_STUDENT
from .forms import CreateUserForm
from .models import ScheduledTask, UserBenefits
from .utils import generate_random_password, send_email_template

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


class PhoneNumberAdmin(admin.TabularInline):
    model = PhoneNumber
    extra = 1


def send_email_reset_password(user):
    params = {
        'email': user.email,
        'first_name': user.first_name
    }
    headers = {'Authorization': 'Bearer {}'.format(settings.EMAIL_HOST_PASSWORD), 'Content-Type': 'application/json'}
    response = requests.post(settings.SENDGRID_API_BASE_URL + 'mail/send', headers=headers,
                            data=json.dumps({"from": {"email": settings.DEFAULT_FROM_EMAIL, "name": 'Nabi Music'},
                                              "template_id": settings.SENDGRID_EMAIL_TEMPLATES_USER['account_creation_admin'],
                                              "personalizations": [{"to": [{"email": user.email}],
                                                                    "dynamic_template_data": params}]
                                            })
                            )
    if response.status_code != 202:
        send_admin_email("""[INFO] Could not send account creation email to {}
                        The status_code for API's response was {} and content: {}""".format(
                             user.email,
                             response.status_code,
                             response.content.decode())
                         )
        return None         


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
    list_select_related = ('phonenumber',)
    search_fields = ('email', 'first_name', 'last_name',)
    readonly_fields = ('profile', 'referral_token', 'referred_by',)
    add_form = CreateUserForm
    inlines = [PhoneNumberAdmin, ]

    def profile(self, instance):
        return instance.get_role()

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)

    def get_formsets_with_inlines(self, request, obj=None):   # for hide phone number when a new user is created
        if obj is not None:
            for inline in self.get_inline_instances(request, obj):
                yield inline.get_formset(request, obj), inline

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
        if not change:   # call on create, not update
            role = form.cleaned_data.pop('role')
            form.cleaned_data['password'] = generate_random_password(10)
            ser = None
            if role == ROLE_INSTRUCTOR:
                ser = InstructorCreateAccountSerializer(data=form.cleaned_data)
            if role == ROLE_PARENT:
                ser = ParentCreateAccountSerializer(data=form.cleaned_data)
            if role == ROLE_STUDENT:
                ser = StudentCreateAccountSerializer(data=form.cleaned_data)
            if ser:   # just in case
                if ser.is_valid():
                    account = ser.save()
                    send_email_reset_password(account.user)
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


class ScheduledTaskAdmin(admin.ModelAdmin):
    list_display = ('function_name', 'schedule', 'executed', )
    fields = ('function_name', 'schedule', 'limit_execution', 'parameters', 'executed', )
    list_filter = ('executed', )
    search_fields = ('function_name', )


admin.site.register(ScheduledTask, ScheduledTaskAdmin)
admin.site.register(User, UserAdmin)
admin.site.register(UserBenefits, UserBenefitsAdmin)
