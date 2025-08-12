"""
🔗 WebSocket URL Routing
Bu dosya WebSocket bağlantıları için URL yönlendirmelerini tanımlar.
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Bildirim sistemi
    re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
    
    # Chat sistemi (trade ID ile)
    re_path(r'ws/chat/(?P<trade_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
    
    # Canlı aktivite feed
    re_path(r'ws/activities/$', consumers.LiveActivityConsumer.as_asgi()),
]
