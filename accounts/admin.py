from django.contrib.auth import get_user_model
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import (Education, Employment, Instructor, InstructorAdditionalQualifications,
                             InstructorAgeGroup, InstructorInstruments, InstructorLessonRate, InstructorLessonSize)

User = get_user_model()


class EducationInline(admin.TabularInline):
    model = Education
    extra = 1


class EmploymentInline(admin.TabularInline):
    model = Employment
    extra = 1


class AdicionalQualificationsAdmin(admin.TabularInline):
    model = InstructorAdditionalQualifications
    extra = 1


class AgeGroupAdmin(admin.TabularInline):
    model = InstructorAgeGroup
    extra = 1


class InstrumentsAdmin(admin.TabularInline):
    model = InstructorInstruments
    extra = 1


class LessonRateAdmin(admin.TabularInline):
    model = InstructorLessonRate
    extra = 1


class LessonSizeAdmin(admin.TabularInline):
    model = InstructorLessonSize
    extra = 1


class InstructorInterviewAdmin(admin.ModelAdmin):
    fields = ('user', 'display_name', 'age', 'avatar', 'bio_title', 'bio_description',
              'music', 'interviewed', 'languages', 'studio_address', 'travel_distance', 'experience_years')
    list_display = ('pk', 'user', 'display_name', )
    list_filter = ('interviewed', )
    list_select_related = ('user', )
    search_fields = ['user__email', 'display_name', ]
    readonly_fields = ('user', 'display_name', 'age', 'experience_years')
    ordering = ('pk', )
    inlines = [EducationInline, EmploymentInline, AdicionalQualificationsAdmin, AgeGroupAdmin,
               InstrumentsAdmin, LessonRateAdmin, LessonSizeAdmin]


admin.site.register(User, UserAdmin)
admin.site.register(Instructor, InstructorInterviewAdmin)
