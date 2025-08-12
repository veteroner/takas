"""
ASGI config for config project - HTTP only mode for Railway deployment.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# ASGI application - HTTP only for Railway
application = get_asgi_application()

# WebSocket support (temporarily disabled for Railway deployment)
# from channels.routing import ProtocolTypeRouter, URLRouter
# from channels.auth import AuthMiddlewareStack
# from channels.security.websocket import AllowedHostsOriginValidator
# import market.routing
#
# django_asgi_app = get_asgi_application()
#
# application = ProtocolTypeRouter({
#     "http": django_asgi_app,
#     "websocket": AllowedHostsOriginValidator(
#         AuthMiddlewareStack(
#             URLRouter(
#                 market.routing.websocket_urlpatterns
#             )
#         )
#     ),
# })
