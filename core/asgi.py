import os
import django

# Step 1: point to settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Step 2: fully initialize Django before any app imports
django.setup()

# Step 3: now safe to import everything else
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import workspace.routing

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter(
            workspace.routing.websocket_urlpatterns
        )
    ),
})