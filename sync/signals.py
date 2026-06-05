import json
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.serializers.json import DjangoJSONEncoder
from django.forms.models import model_to_dict
from django.apps import apps
import sys
from sync.models import SyncQueue

# We don't want to track sync app models or auth models
EXCLUDED_APPS = ['sync', 'admin', 'contenttypes', 'sessions', 'auth']

from datetime import datetime, date
from decimal import Decimal
from django.db.utils import OperationalError, ProgrammingError

from django.db.models.fields.files import FieldFile

def serialize_instance(instance):
    data = model_to_dict(instance)
    # Handle UUIDs and other non-JSON serializable types
    for key, value in data.items():
        if hasattr(value, 'hex'):
            data[key] = value.hex
        elif isinstance(value, (datetime, date)):
            data[key] = value.isoformat()
        elif isinstance(value, Decimal):
            data[key] = str(value)
        elif isinstance(value, FieldFile):
            try:
                data[key] = value.url if value else None
            except ValueError:
                data[key] = None
        elif hasattr(value, '__iter__') and not isinstance(value, str):
            # For ManyToMany fields
            data[key] = [str(v.pk) if hasattr(v, 'pk') else (v.hex if hasattr(v, 'hex') else str(v)) for v in value]
    return data

def record_sync_event(instance, action):
    app_label = instance._meta.app_label
    if app_label in EXCLUDED_APPS:
        return

    model_name = instance._meta.object_name
    object_id = str(instance.pk)
    
    data = None
    if action != 'DELETE':
        try:
            data = serialize_instance(instance)
        except Exception as e:
            print(f"Error serializing {model_name} {object_id}: {e}")
            return

    # Delete any pending updates for this object so we only sync the latest state
    if action == 'UPDATE':
        try:
            SyncQueue.objects.filter(model_name=model_name, object_id=object_id, status='PENDING', action='UPDATE').delete()
        except (OperationalError, ProgrammingError):
            pass
        
    # If we are deleting, we don't need to sync the creates or updates
    if action == 'DELETE':
        try:
            SyncQueue.objects.filter(model_name=model_name, object_id=object_id, status='PENDING').delete()
        except (OperationalError, ProgrammingError):
            pass

    try:
        SyncQueue.objects.create(
            model_name=model_name,
            object_id=object_id,
            action=action,
            data=data,
            status='PENDING'
        )
    except (OperationalError, ProgrammingError):
        pass

@receiver(post_save)
def handle_post_save(sender, instance, created, **kwargs):
    if 'migrate' in sys.argv or 'makemigrations' in sys.argv:
        return
    if sys.argv and 'upgrade_beta_db.py' in sys.argv[0]:
        return
    if kwargs.get('raw', False): # Don't track fixtures
        return
    # Avoid tracking SyncQueue itself inside the handler to prevent recursion (handled by EXCLUDED_APPS but good to be safe)
    if sender._meta.app_label in EXCLUDED_APPS:
        return
        
    action = 'CREATE' if created else 'UPDATE'
    record_sync_event(instance, action)

@receiver(post_delete)
def handle_post_delete(sender, instance, **kwargs):
    if 'migrate' in sys.argv or 'makemigrations' in sys.argv:
        return
    if sys.argv and 'upgrade_beta_db.py' in sys.argv[0]:
        return
    if sender._meta.app_label in EXCLUDED_APPS:
        return
    record_sync_event(instance, 'DELETE')
