import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
from django.core.asgi import get_asgi_application
django_application = get_asgi_application()
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.urls import path
from boards.consumers import WorkspaceConsumer

application = ProtocolTypeRouter({
    'http': django_application,
    'websocket': AllowedHostsOriginValidator(AuthMiddlewareStack(URLRouter([
        path('ws/workspace/', WorkspaceConsumer.as_asgi()),
    ]))),
})
