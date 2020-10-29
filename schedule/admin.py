from django.contrib import admin

from .models import InstructorParticularAvailability, InstructorRegularAvailability


class InstructorParticularAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('instructor', 'date', )
    fields = ('instructor', 'date', 'schedule')
    search_fields = ('instructor__user__email', )

    class Meta:
        model = InstructorParticularAvailability


class InstructorRegularAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('instructor', 'week_day', )
    fields = ('instructor', 'week_day', 'schedule')
    search_fields = ('instructor__user__email',)

    class Meta:
        model = InstructorRegularAvailability


admin.site.register(InstructorParticularAvailability, InstructorParticularAvailabilityAdmin)
admin.site.register(InstructorRegularAvailability, InstructorRegularAvailabilityAdmin)
