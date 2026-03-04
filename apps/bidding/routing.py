"""
WebSocket Routing
=================
URL routing for WebSocket connections

CHANNELS ROUTING:
- Similar to Django's urlpatterns
- Maps WebSocket URLs to consumers
- Uses re_path for regex patterns
"""

from django.urls import re_path
from . import consumers

# WebSocket URL patterns
# ws://localhost:8000/ws/auction/<auction_id>/
websocket_urlpatterns = [
    re_path(
        r'ws/auction/(?P<auction_id>\d+)/$',
        consumers.AuctionConsumer.as_asgi()
    ),
]
