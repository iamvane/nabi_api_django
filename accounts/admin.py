from django.contrib.auth import get_user_model
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from accounts.models import Instructor

User = get_user_model()


class InstructorAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)


admin.site.register(User, UserAdmin)
admin.site.register(Instructor, InstructorAdmin)
