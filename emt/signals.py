# emt/signals.py

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import EventProposal # Make sure this import is correct for your models

logger = logging.getLogger(__name__)

@receiver(post_save, sender=EventProposal)
def log_proposal_submission(sender, instance, created, **kwargs):
    """
    Logs a message when a new EventProposal is created.
    """
    # The 'created' flag is True only when a new record is made
    if created:
        # Check if the user who submitted is available
        submitted_by_info = (f"by user '{instance.submitted_by.username}'" 
                             if hasattr(instance, 'submitted_by') and instance.submitted_by 
                             else "without a specified user")
        
        logger.info(
            f"New event proposal '{instance.title}' (ID: {instance.id}) was created {submitted_by_info}."
        )