from django.db import models

class GraduateAttribute(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return str(self.name)

class CharacterStrength(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return str(self.name)

class AttributeStrengthMap(models.Model):
    graduate_attribute = models.ForeignKey(GraduateAttribute, on_delete=models.CASCADE)
    character_strength = models.ForeignKey(CharacterStrength, on_delete=models.CASCADE)
    weight = models.FloatField()

    def __str__(self):
        return f"{self.graduate_attribute} → {self.character_strength} = {self.weight}"

class Event(models.Model):
    name = models.CharField(max_length=200)
    date = models.DateField()
    attributes = models.ManyToManyField(GraduateAttribute)

    def __str__(self):
        return f"{self.name} - {self.date}"

class Student(models.Model):
    roll_no = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.roll_no} - {self.name}"

# 🆕 Role model with multiplication factor
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

# 🔁 Updated Participation with Role
class Participation(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)  # 👈 added role

    def __str__(self):
        return f"{self.student} → {self.event} ({self.role})"
