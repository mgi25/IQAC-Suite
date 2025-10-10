from django.contrib import admin
from django.utils.html import format_html

from .models import (
    AcademicYear,
    AttributeStrengthMap,
    CharacterStrength,
    Course,
    Event,
    GraduateAttribute,
    Participation,
    Role,
    School,
    Student,
)


# Custom admin for Student to display photo.
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        "roll_no",
        "name",
        "course",
        "academic_year",
        "school",
        "photo_tag",
    )
    search_fields = ("roll_no", "name")
    list_filter = ("course", "academic_year", "school")

    def photo_tag(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit:cover;border-radius:50%;" />',
                obj.photo.url,
            )
        return "No photo"

    photo_tag.short_description = "Photo"


# Register other models normally.
admin.site.register(Event)
admin.site.register(Participation)
admin.site.register(GraduateAttribute)
admin.site.register(CharacterStrength)
admin.site.register(AttributeStrengthMap)
admin.site.register(Role)
admin.site.register(School)
admin.site.register(Course)
admin.site.register(AcademicYear)
