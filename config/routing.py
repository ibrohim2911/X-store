from django.urls import path
from common.consumers import DashboardConsumer

websocket_urlpatterns = [
    path('ws/updates/', DashboardConsumer.as_asgi()),
]
