from django.contrib import admin
from .models import (
    Student,
    Event,
    Participation,
    GraduateAttribute,
    CharacterStrength,
    AttributeStrengthMap,
    Role  # ✅ Import the new Role model
)

# ✅ Register all models
admin.site.register(Student)
admin.site.register(Event)
admin.site.register(Participation)
admin.site.register(GraduateAttribute)
admin.site.register(CharacterStrength)
admin.site.register(AttributeStrengthMap)
admin.site.register(Role)  # ✅ Register Role model
