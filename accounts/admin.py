from django.contrib import admin

from accounts.models import Instructor


class InstructorAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)


admin.site.register(Instructor, InstructorAdmin)
