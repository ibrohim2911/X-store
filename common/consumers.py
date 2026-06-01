import json
from channels.generic.websocket import AsyncWebsocketConsumer

class DashboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = 'updates'
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def broadcast_update(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': event['message_type'],
            'payload': event.get('payload', {})
        }))
