from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async

class WorkspaceConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope['user']
        if not user.is_authenticated:
            await self.close(code=4401)
            return
        self.group = f'user_{user.pk}'
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, 'group'):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def workspace_changed(self, event):
        # Session validity is rechecked before every delivery (logout/recovery revokes access).
        if not await self.session_valid():
            await self.close(code=4401)
            return
        await self.send_json({'type':'workspace.changed'})

    async def receive_json(self, content, **kwargs):
        if content.get('type') == 'ping':
            if not await self.session_valid():
                await self.close(code=4401)
                return
            await self.channel_layer.group_add(self.group, self.channel_name)
            await self.send_json({'type':'pong'})

    @database_sync_to_async
    def session_valid(self):
        from django.contrib.auth import get_user
        from django.conf import settings
        from importlib import import_module
        from types import SimpleNamespace
        store = import_module(settings.SESSION_ENGINE).SessionStore(session_key=self.scope['session'].session_key)
        return get_user(SimpleNamespace(session=store)).is_authenticated
