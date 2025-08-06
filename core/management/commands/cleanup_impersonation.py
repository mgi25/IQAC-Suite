from django.core.management.base import BaseCommand
from django.contrib.sessions.models import Session
from django.contrib.auth.models import User
import json

class Command(BaseCommand):
    help = 'Clean up orphaned impersonation sessions'

    def handle(self, *args, **options):
        cleaned_count = 0
        
        for session in Session.objects.all():
            try:
                session_data = session.get_decoded()
                impersonate_user_id = session_data.get('impersonate_user_id')
                original_user_id = session_data.get('original_user_id')
                
                if impersonate_user_id:
                    # Check if impersonated user still exists
                    try:
                        User.objects.get(id=impersonate_user_id, is_active=True)
                    except User.DoesNotExist:
                        session.delete()
                        cleaned_count += 1
                        continue
                
                if original_user_id:
                    # Check if original user still exists
                    try:
                        User.objects.get(id=original_user_id, is_active=True)
                    except User.DoesNotExist:
                        session.delete()
                        cleaned_count += 1
                        continue
                        
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'Error processing session {session.session_key}: {e}')
                )
                
        self.stdout.write(
            self.style.SUCCESS(f'Successfully cleaned up {cleaned_count} orphaned sessions')
        )