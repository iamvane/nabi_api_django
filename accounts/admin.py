from django.contrib.auth import get_user_model
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from accounts.models import Instructor

User = get_user_model()


class InstructorInterviewAdmin(admin.ModelAdmin):
    fields = ('user', 'display_name', 'interviewed', )
    list_display = ('pk', 'user', 'display_name', )
    list_filter = ('interviewed', )
    list_select_related = ('user', )
    search_fields = ['user__email', 'display_name', ]
    readonly_fields = ('user', 'display_name', )
    ordering = ('pk', )


admin.site.register(User, UserAdmin)
admin.site.register(Instructor, InstructorInterviewAdmin)
