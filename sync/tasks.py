import threading
import time
import requests
from django.conf import settings
from django.db import transaction

# Replace with actual VDS URL in production (e.g. from SystemSettings)
VDS_URL = getattr(settings, 'VDS_URL', 'http://vds-server.com') 

def sync_worker():
    from sync.models import SyncQueue
    
    while True:
        try:
            # 1. Get pending operations
            pending_items = SyncQueue.objects.filter(status='PENDING').order_by('created_at')[:50]
            
            if pending_items.exists():
                operations = []
                for item in pending_items:
                    operations.append({
                        'id': str(item.id),
                        'model_name': item.model_name,
                        'object_id': item.object_id,
                        'action': item.action,
                        'data': item.data
                    })
                
                # 2. Push to VDS
                # Note: This is disabled unless VDS_URL is actually configured, so it doesn't spam errors locally
                if 'vds-server.com' not in VDS_URL:
                    response = requests.post(
                        f"{VDS_URL}/api/sync/push/", 
                        json={"operations": operations},
                        timeout=5
                    )
                    
                    if response.status_code == 200:
                        results = response.json().get('results', [])
                        
                        # 3. Process results
                        with transaction.atomic():
                            for result in results:
                                status = result.get('status')
                                object_id = result.get('object_id')
                                reason = result.get('reason', '')
                                
                                # We need to update the queue item based on the result
                                # Since we might have multiple operations for the same object, we match by object_id
                                # Ideally we'd match by SyncQueue item ID, but VDS doesn't know SyncQueue IDs
                                # A more robust system would pass the SyncQueue ID to VDS and get it back
                                
                                queue_items = pending_items.filter(object_id=object_id)
                                for q in queue_items:
                                    q.status = status
                                    q.conflict_reason = reason
                                    q.save()
        except Exception as e:
            # Silently ignore connection errors in background
            pass
            
        # Wait before next sync attempt
        time.sleep(10)

def start_sync_worker():
    thread = threading.Thread(target=sync_worker, daemon=True)
    thread.start()
