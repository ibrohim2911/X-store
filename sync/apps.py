from django.apps import AppConfig


class SyncConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sync'

    def ready(self):
        import sync.signals
        
        # Avoid running twice with auto-reloader
        import os
        if os.environ.get('RUN_MAIN', None) != 'true':
            from sync.tasks import start_sync_worker
            start_sync_worker()
