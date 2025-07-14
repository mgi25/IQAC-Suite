from django.db import models

# ─────────────────────────────────────────────────────────────
# Graduate Attribute and Character Strength
# ─────────────────────────────────────────────────────────────
class GraduateAttribute(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return str(self.name)

class CharacterStrength(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return str(self.name)

# ─────────────────────────────────────────────────────────────
# Mapping: Attribute → VIA Strength
# ─────────────────────────────────────────────────────────────
class AttributeStrengthMap(models.Model):
    graduate_attribute = models.ForeignKey(GraduateAttribute, on_delete=models.CASCADE)
    character_strength = models.ForeignKey(CharacterStrength, on_delete=models.CASCADE)
    weight = models.FloatField()

    def __str__(self):
        return f"{self.graduate_attribute} → {self.character_strength} = {self.weight}"

# ─────────────────────────────────────────────────────────────
# Academic Structure: Year, School, Course
# ─────────────────────────────────────────────────────────────
class AcademicYear(models.Model):
    year = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return self.year

class School(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Course(models.Model):
    name = models.CharField(max_length=100)
    school = models.ForeignKey(School, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('name', 'school')

    def __str__(self):
        return f"{self.name} ({self.school.name})"

# ─────────────────────────────────────────────────────────────
# Event Model
# ─────────────────────────────────────────────────────────────
class Event(models.Model):
    name = models.CharField(max_length=200)
    date = models.DateField()
    attributes = models.ManyToManyField(GraduateAttribute)

    def __str__(self):
        return f"{self.name} - {self.date}"

# ─────────────────────────────────────────────────────────────
# Student (with school, course, academic year)
# ─────────────────────────────────────────────────────────────
class Student(models.Model):
    roll_no = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    photo = models.ImageField(upload_to='student_pics/', null=True, blank=True)  # 👈 Add this line

    # ✅ These are now nullable so you don’t get migration prompts:
    school = models.ForeignKey(School, on_delete=models.CASCADE, null=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.roll_no} - {self.name}"

# ─────────────────────────────────────────────────────────────
# Role with Multiplication Factor
# ─────────────────────────────────────────────────────────────
class Role(models.Model):
    ROLE_CHOICES = [
        ('First Level', 'First Level Worker'),
        ('High Level', 'High Level Worker'),
        ('Medium Level', 'Medium Level Worker'),
        ('Low Level', 'Low Level Worker'),
        ('Attendee', 'Audience/Attendee'),
    ]
    name = models.CharField(max_length=50, choices=ROLE_CHOICES, unique=True)
    factor = models.FloatField()

    def __str__(self):
        return f"{self.name} (x{self.factor})"

# ─────────────────────────────────────────────────────────────
# Participation: Links Student, Event, and Role
# ─────────────────────────────────────────────────────────────
class Participation(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.student} → {self.event} ({self.role})"
