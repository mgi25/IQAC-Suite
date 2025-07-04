from django.contrib import admin
from .models import (
    Student,
    Event,
    Participation,
    GraduateAttribute,
    CharacterStrength,
    AttributeStrengthMap,
    Role,
    School,           # ✅ Added
    Course,           # ✅ Added
    AcademicYear      # ✅ Added
)

# ✅ Register all models
admin.site.register(Student)
admin.site.register(Event)
admin.site.register(Participation)
admin.site.register(GraduateAttribute)
admin.site.register(CharacterStrength)
admin.site.register(AttributeStrengthMap)
admin.site.register(Role)
admin.site.register(School)        # ✅ Registered
admin.site.register(Course)        # ✅ Registered
admin.site.register(AcademicYear)  # ✅ Registered
