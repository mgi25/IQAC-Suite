from django.db import models
from django.contrib.auth.models import User

class EventProposal(models.Model):
    user        = models.ForeignKey(User, on_delete=models.CASCADE)
    title       = models.CharField(max_length=200)
    description = models.TextField()
    date_submitted = models.DateTimeField(auto_now_add=True)
    # add any fields you need…
