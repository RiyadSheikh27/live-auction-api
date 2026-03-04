"""
ASGI config for live_auction_drf project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'live_auction_drf.settings')


# Initialize Django ASGI application early to populate apps registry
django_asgi_app = get_asgi_application()

# Import after django_asgi_app to avoid AppRegistryNotReady error
from apps.bidding.routing import websocket_urlpatterns


# ProtocolTypeRouter decides what to do based on protocol type
# "http" -> Regular Django views
# "websocket" -> Channels consumers
application = ProtocolTypeRouter({
    # HTTP requests go to standard Django
    "http": django_asgi_app,
    
    # WebSocket requests go to Channels
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(  # Provides user authentication for WebSockets
            URLRouter(websocket_urlpatterns)
        )
    ),
})
