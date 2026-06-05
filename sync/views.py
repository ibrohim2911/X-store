from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.apps import apps
from sync.models import SyncQueue
import json

class SyncPushView(APIView):
    """
    Receives a list of operations from a local client to apply to the VDS.
    """
    def post(self, request):
        operations = request.data.get('operations', [])
        results = []
        
        for op in operations:
            model_name = op.get('model_name')
            object_id = op.get('object_id')
            action = op.get('action')
            data = op.get('data')
            
            # Find the model class
            ModelClass = None
            for app_config in apps.get_app_configs():
                try:
                    ModelClass = app_config.get_model(model_name)
                    break
                except LookupError:
                    continue
            
            if not ModelClass:
                results.append({'object_id': object_id, 'status': 'ERROR', 'reason': 'Model not found'})
                continue
                
            try:
                if action == 'CREATE':
                    # Create or update if exists (to be safe against duplicates)
                    obj, created = ModelClass.objects.update_or_create(pk=object_id, defaults=data)
                    results.append({'object_id': object_id, 'status': 'SYNCED'})
                    
                elif action == 'UPDATE':
                    # Find and update
                    try:
                        obj = ModelClass.objects.get(pk=object_id)
                        for k, v in data.items():
                            setattr(obj, k, v)
                        obj.save()
                        results.append({'object_id': object_id, 'status': 'SYNCED'})
                    except ModelClass.DoesNotExist:
                        # If doesn't exist on server, we should probably create it
                        obj = ModelClass.objects.create(pk=object_id, **data)
                        results.append({'object_id': object_id, 'status': 'SYNCED'})
                        
                elif action == 'DELETE':
                    ModelClass.objects.filter(pk=object_id).delete()
                    results.append({'object_id': object_id, 'status': 'SYNCED'})
            except Exception as e:
                # If there's a conflict or error, return it
                results.append({'object_id': object_id, 'status': 'CONFLICT', 'reason': str(e)})
                
        return Response({'results': results})

class SyncPullView(APIView):
    """
    Returns changes that the client should download.
    (To be fully implemented later, requires tracking last sync time per client/store)
    """
    def get(self, request):
        return Response({'operations': []})
