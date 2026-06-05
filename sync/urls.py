from django.urls import path
from .views import SyncPushView, SyncPullView

urlpatterns = [
    path('push/', SyncPushView.as_view(), name='sync-push'),
    path('pull/', SyncPullView.as_view(), name='sync-pull'),
]
