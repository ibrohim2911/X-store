from django.contrib import admin
from .models import SyncQueue

@admin.register(SyncQueue)
class SyncQueueAdmin(admin.ModelAdmin):
    list_display = ('model_name', 'action', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'action', 'model_name')
    search_fields = ('object_id', 'model_name', 'conflict_reason')
    readonly_fields = ('created_at', 'updated_at')
    
    actions = ['mark_as_pending', 'mark_as_synced']

    def mark_as_pending(self, request, queryset):
        queryset.update(status='PENDING')
    mark_as_pending.short_description = "Mark selected as PENDING (Retry Sync)"

    def mark_as_synced(self, request, queryset):
        queryset.update(status='SYNCED')
    mark_as_synced.short_description = "Mark selected as SYNCED (Ignore Conflict)"
