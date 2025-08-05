from django.apps import AppConfig

class EmtConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'emt'
    
    def ready(self):
        """
        Import signals when the app is ready.
        """
        import emt.signals