from django.test import TransactionTestCase
from django.contrib.auth import get_user_model
from channels.testing import WebsocketCommunicator
from channels.layers import get_channel_layer
from channels.sessions import CookieMiddleware, SessionMiddleware
from channels.auth import AuthMiddleware
from asgiref.sync import async_to_sync
from .consumers import WorkspaceConsumer

class RealtimeTests(TransactionTestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user('live',password='A-strong-pass-928!')
        self.client.force_login(self.user)
        self.cookie=f'sessionid={self.client.cookies["sessionid"].value}'.encode()

    def test_authenticated_delivery(self):
        async def scenario():
            app=CookieMiddleware(SessionMiddleware(AuthMiddleware(WorkspaceConsumer.as_asgi())))
            socket=WebsocketCommunicator(app,'/ws/workspace/',headers=[(b'cookie',self.cookie)])
            connected,_=await socket.connect()
            self.assertTrue(connected)
            await get_channel_layer().group_send(f'user_{self.user.pk}',{'type':'workspace.changed'})
            self.assertEqual(await socket.receive_json_from(),{'type':'workspace.changed'})
            await socket.disconnect()
        async_to_sync(scenario)()

    def test_anonymous_is_rejected(self):
        async def scenario():
            from django.contrib.auth.models import AnonymousUser
            app=WorkspaceConsumer.as_asgi()
            socket=WebsocketCommunicator(app,'/ws/workspace/')
            socket.scope['user']=AnonymousUser()
            self.assertFalse((await socket.connect())[0])
            await socket.disconnect()
        async_to_sync(scenario)()

    def test_logout_revokes_open_socket(self):
        async def scenario():
            from channels.db import database_sync_to_async
            app=CookieMiddleware(SessionMiddleware(AuthMiddleware(WorkspaceConsumer.as_asgi())))
            socket=WebsocketCommunicator(app,'/ws/workspace/',headers=[(b'cookie',self.cookie)])
            self.assertTrue((await socket.connect())[0])
            await database_sync_to_async(self.client.logout)()
            await get_channel_layer().group_send(f'user_{self.user.pk}',{'type':'workspace.changed'})
            self.assertEqual((await socket.receive_output())['code'],4401)
            await socket.disconnect()
        async_to_sync(scenario)()
