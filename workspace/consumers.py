import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import Room, Message, Document, ActivityLog, RoomMembership


class RoomConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'room_{self.room_name}'
        self.user = self.scope['user']

        # Reject unauthenticated connections
        if not self.user.is_authenticated:
            await self.close()
            return

        # Join the channel group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        # Notify group that this user connected
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_join',
                'username': self.user.username,
            }
        )

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            # Notify group that this user disconnected
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_leave',
                    'username': self.user.username,
                }
            )
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """Handle incoming messages from the WebSocket client."""
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        msg_type = data.get('type')

        if msg_type == 'chat_message':
            await self.handle_chat(data)

        elif msg_type == 'document_update':
            await self.handle_document(data)

        elif msg_type == 'typing':
            await self.handle_typing(data)
        elif msg_type == 'whiteboard_draw':
            await self.handle_whiteboard(data)

    # ── CHAT ──────────────────────────────────────

    async def handle_chat(self, data):
        content = data.get('content', '').strip()
        if not content:
            return

        room = await self.get_room()
        if not room:
            return

        # Save message to DB
        message = await self.save_message(room, content)

        # Broadcast to group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'username': self.user.username,
                'content': content,
                'timestamp': message.timestamp.strftime('%H:%M'),
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'username': event['username'],
            'content': event['content'],
            'timestamp': event['timestamp'],
        }))

    # ── DOCUMENT ──────────────────────────────────

    async def handle_document(self, data):
        content = data.get('content', '')
        room = await self.get_room()
        if not room:
            return

        # Save to DB
        await self.save_document(room, content)

        # Broadcast update to everyone else in the room
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'document_update',
                'content': content,
                'username': self.user.username,
            }
        )

    async def document_update(self, event):
        # Don't echo back to the sender
        if event['username'] != self.user.username:
            await self.send(text_data=json.dumps({
                'type': 'document_update',
                'content': event['content'],
                'username': event['username'],
            }))

    # ── TYPING INDICATOR ──────────────────────────

    async def handle_typing(self, data):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'username': self.user.username,
                'is_typing': data.get('is_typing', False),
            }
        )

    async def typing_indicator(self, event):
        if event['username'] != self.user.username:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'username': event['username'],
                'is_typing': event['is_typing'],
            }))

    # ── PRESENCE ──────────────────────────────────

    async def user_join(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_join',
            'username': event['username'],
        }))

    async def user_leave(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_leave',
            'username': event['username'],
        }))

    # ── DB HELPERS ────────────────────────────────

    @database_sync_to_async
    def get_room(self):
        try:
            return Room.objects.get(slug=self.room_name)
        except Room.DoesNotExist:
            return None

    @database_sync_to_async
    def save_message(self, room, content):
        msg = Message.objects.create(
            room=room,
            user=self.user,
            content=content
        )
        ActivityLog.objects.create(
            room=room,
            user=self.user,
            action='messaged',
            detail=f'{self.user.username} sent a message.'
        )
        return msg

    @database_sync_to_async
    def save_document(self, room, content):
        doc, _ = Document.objects.get_or_create(room=room)
        doc.content = content
        doc.last_edited_by = self.user
        doc.save()
        ActivityLog.objects.create(
            room=room,
            user=self.user,
            action='edited',
            detail=f'{self.user.username} edited the document.'
        )
        
    # --- WHITEBOARD ---
    async def handle_whiteboard(self, data):
        # We broadcast the drawing coordinates in real-time
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'whiteboard_draw',
                'username': self.user.username,
                'draw_data': data.get('draw_data')
            }
        )

    async def whiteboard_draw(self, event):
        # Don't echo the drawing back to the person who drew it
        if event['username'] != self.user.username:
            await self.send(text_data=json.dumps({
                'type': 'whiteboard_draw',
                'username': event['username'],
                'draw_data': event['draw_data']
            }))