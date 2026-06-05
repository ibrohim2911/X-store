from django.db import models
from common.models import BaseModel
from django.core.serializers.json import DjangoJSONEncoder

class SyncQueue(BaseModel):
    ACTION_CHOICES = (
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
    )
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('SYNCED', 'Synced'),
        ('CONFLICT', 'Conflict'),
    )

    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100) # Store UUID as string
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    data = models.JSONField(blank=True, null=True, encoder=DjangoJSONEncoder)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    conflict_reason = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.action} {self.model_name} ({self.object_id}) - {self.status}"
