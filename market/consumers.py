"""
⚡ Real-time WebSocket Consumers
Bu modül gerçek zamanlı iletişim için WebSocket consumer'larını içerir.
"""

import json
import logging
from datetime import datetime
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from django.utils import timezone

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    """Gerçek zamanlı bildirimler için WebSocket consumer"""
    
    async def connect(self):
        """WebSocket bağlantısı kurulduğunda"""
        self.user = self.scope["user"]
        
        if self.user.is_authenticated:
            # Kullanıcıya özel group
            self.notification_group_name = f"notifications_{self.user.id}"
            
            # Group'a katıl
            await self.channel_layer.group_add(
                self.notification_group_name,
                self.channel_name
            )
            
            # Bağlantıyı kabul et
            await self.accept()
            
            # Kullanıcıyı online olarak işaretle
            await self.set_user_online(True)
            
            logger.info(f"User {self.user.username} connected to notifications")
            
            # Bekleyen bildirimleri gönder
            await self.send_pending_notifications()
            
        else:
            # Misafir kullanıcıları reddet
            await self.close()
    
    async def disconnect(self, close_code):
        """WebSocket bağlantısı kapandığında"""
        if hasattr(self, 'user') and self.user.is_authenticated:
            # Group'dan ayrıl
            await self.channel_layer.group_discard(
                self.notification_group_name,
                self.channel_name
            )
            
            # Kullanıcıyı offline olarak işaretle
            await self.set_user_online(False)
            
            logger.info(f"User {self.user.username} disconnected from notifications")
    
    async def receive(self, text_data):
        """WebSocket'den mesaj alındığında"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'mark_notification_read':
                notification_id = data.get('notification_id')
                await self.mark_notification_read(notification_id)
                
            elif message_type == 'get_unread_count':
                count = await self.get_unread_notifications_count()
                await self.send(text_data=json.dumps({
                    'type': 'unread_count',
                    'count': count
                }))
                
            elif message_type == 'heartbeat':
                # Heartbeat - kullanıcının aktif olduğunu göster
                await self.update_last_seen()
                await self.send(text_data=json.dumps({
                    'type': 'heartbeat_ack',
                    'timestamp': datetime.now().isoformat()
                }))
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received from {self.user.username}")
        except Exception as e:
            logger.error(f"Error processing message from {self.user.username}: {e}")
    
    async def send_notification(self, event):
        """Bildirim gönder (group'dan tetiklenen)"""
        notification_data = event['notification']
        
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': notification_data
        }))
    
    async def send_live_activity(self, event):
        """Canlı aktivite gönder"""
        activity_data = event['activity']
        
        await self.send(text_data=json.dumps({
            'type': 'live_activity',
            'activity': activity_data
        }))
    
    async def user_status_update(self, event):
        """Kullanıcı online/offline durumu güncelleme"""
        status_data = event['status']
        
        await self.send(text_data=json.dumps({
            'type': 'user_status',
            'status': status_data
        }))
    
    @database_sync_to_async
    def set_user_online(self, is_online):
        """Kullanıcının online durumunu güncelle"""
        from .models import UserOnlineStatus
        
        status, created = UserOnlineStatus.objects.get_or_create(
            user=self.user,
            defaults={
                'is_online': is_online,
                'channel_name': self.channel_name,
                'user_agent': self.scope.get('headers', {}).get(b'user-agent', b'').decode(),
                'ip_address': self.get_client_ip()
            }
        )
        
        if not created:
            status.is_online = is_online
            status.channel_name = self.channel_name if is_online else ''
            status.last_seen = timezone.now()
            status.save()
        
        return status
    
    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Bildirimi okundu olarak işaretle"""
        from .models import Notification
        
        try:
            notification = Notification.objects.get(
                id=notification_id,
                recipient=self.user
            )
            notification.mark_as_read()
            return True
        except Notification.DoesNotExist:
            return False
    
    @database_sync_to_async
    def get_unread_notifications_count(self):
        """Okunmamış bildirim sayısını getir"""
        from .models import Notification
        
        return Notification.objects.filter(
            recipient=self.user,
            is_read=False
        ).count()
    
    @database_sync_to_async
    def send_pending_notifications(self):
        """Bekleyen bildirimleri gönder"""
        from .models import Notification
        
        # Son 24 saatin okunmamış bildirimlerini al
        pending_notifications = Notification.objects.filter(
            recipient=self.user,
            is_read=False,
            created_at__gte=timezone.now() - timezone.timedelta(hours=24)
        )[:10]  # Son 10 bildirimi gönder
        
        for notification in pending_notifications:
            notification_data = {
                'id': notification.id,
                'type': notification.notification_type,
                'title': notification.title,
                'message': notification.message,
                'created_at': notification.created_at.isoformat(),
                'action_url': notification.action_url,
                'extra_data': notification.extra_data,
                'sender': notification.sender.username if notification.sender else None
            }
            
            # Async olarak gönder
            self.send(text_data=json.dumps({
                'type': 'notification',
                'notification': notification_data
            }))
    
    @database_sync_to_async
    def update_last_seen(self):
        """Son görülme zamanını güncelle"""
        from .models import UserOnlineStatus
        
        try:
            status = UserOnlineStatus.objects.get(user=self.user)
            status.last_seen = timezone.now()
            status.save()
        except UserOnlineStatus.DoesNotExist:
            pass
    
    def get_client_ip(self):
        """Client IP adresini al"""
        headers = dict(self.scope['headers'])
        x_forwarded_for = headers.get(b'x-forwarded-for')
        
        if x_forwarded_for:
            ip = x_forwarded_for.decode().split(',')[0]
        else:
            ip = self.scope['client'][0]
        
        return ip


class ChatConsumer(AsyncWebsocketConsumer):
    """Gerçek zamanlı chat sistemi"""
    
    async def connect(self):
        """Chat WebSocket bağlantısı"""
        self.user = self.scope["user"]
        self.trade_id = self.scope['url_route']['kwargs']['trade_id']
        self.room_group_name = f"chat_trade_{self.trade_id}"
        
        if self.user.is_authenticated:
            # Trade'e erişim kontrolü
            has_access = await self.check_trade_access()
            
            if has_access:
                # Group'a katıl
                await self.channel_layer.group_add(
                    self.room_group_name,
                    self.channel_name
                )
                
                await self.accept()
                
                # Kullanıcının chat'e katıldığını bildır
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'user_joined',
                        'user': self.user.username,
                        'timestamp': datetime.now().isoformat()
                    }
                )
                
                logger.info(f"User {self.user.username} joined chat for trade {self.trade_id}")
            else:
                await self.close()
        else:
            await self.close()
    
    async def disconnect(self, close_code):
        """Chat bağlantısı kapandığında"""
        if hasattr(self, 'room_group_name'):
            # Kullanıcının chat'den ayrıldığını bildır
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_left',
                    'user': self.user.username,
                    'timestamp': datetime.now().isoformat()
                }
            )
            
            # Group'dan ayrıl
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            
            logger.info(f"User {self.user.username} left chat for trade {self.trade_id}")
    
    async def receive(self, text_data):
        """Chat mesajı alındığında"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'chat_message':
                content = data.get('content', '').strip()
                
                if content:
                    # Mesajı veritabanına kaydet
                    message = await self.save_message(content)
                    
                    if message:
                        # Mesajı group'a gönder
                        await self.channel_layer.group_send(
                            self.room_group_name,
                            {
                                'type': 'chat_message',
                                'message': {
                                    'id': message.id,
                                    'content': message.content,
                                    'sender': message.sender.username,
                                    'created_at': message.created_at.isoformat()
                                }
                            }
                        )
                        
                        # Karşı tarafa bildirim gönder
                        await self.send_message_notification(message)
            
            elif message_type == 'typing_start':
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'typing_indicator',
                        'user': self.user.username,
                        'is_typing': True
                    }
                )
            
            elif message_type == 'typing_stop':
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'typing_indicator',
                        'user': self.user.username,
                        'is_typing': False
                    }
                )
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in chat from {self.user.username}")
        except Exception as e:
            logger.error(f"Chat error from {self.user.username}: {e}")
    
    async def chat_message(self, event):
        """Chat mesajını WebSocket'e gönder"""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message']
        }))
    
    async def user_joined(self, event):
        """Kullanıcı katıldı bildirimi"""
        if event['user'] != self.user.username:  # Kendine gönderme
            await self.send(text_data=json.dumps({
                'type': 'user_joined',
                'user': event['user'],
                'timestamp': event['timestamp']
            }))
    
    async def user_left(self, event):
        """Kullanıcı ayrıldı bildirimi"""
        if event['user'] != self.user.username:  # Kendine gönderme
            await self.send(text_data=json.dumps({
                'type': 'user_left',
                'user': event['user'],
                'timestamp': event['timestamp']
            }))
    
    async def typing_indicator(self, event):
        """Yazıyor göstergesi"""
        if event['user'] != self.user.username:  # Kendine gönderme
            await self.send(text_data=json.dumps({
                'type': 'typing_indicator',
                'user': event['user'],
                'is_typing': event['is_typing']
            }))
    
    @database_sync_to_async
    def check_trade_access(self):
        """Kullanıcının trade'e erişimi var mı kontrol et"""
        from .models import Trade
        
        try:
            trade = Trade.objects.get(id=self.trade_id)
            return trade.requester == self.user or trade.responder == self.user
        except Trade.DoesNotExist:
            return False
    
    @database_sync_to_async
    def save_message(self, content):
        """Mesajı veritabanına kaydet"""
        from .models import Message, Trade
        
        try:
            trade = Trade.objects.get(id=self.trade_id)
            message = Message.objects.create(
                trade=trade,
                sender=self.user,
                content=content
            )
            return message
        except Trade.DoesNotExist:
            return None
    
    @database_sync_to_async
    def send_message_notification(self, message):
        """Karşı tarafa mesaj bildirimi gönder"""
        from .utils.notifications import NotificationService
        
        # Karşı tarafı belirle
        trade = message.trade
        recipient = trade.responder if trade.requester == self.user else trade.requester
        
        # Bildirim gönder
        NotificationService.send_message_notification(message, recipient)


class LiveActivityConsumer(AsyncWebsocketConsumer):
    """Canlı aktivite feed consumer"""
    
    async def connect(self):
        """Canlı aktivite feed bağlantısı"""
        self.user = self.scope["user"]
        
        if self.user.is_authenticated:
            # Global aktivite feed'i
            self.activity_group_name = "live_activities"
            
            # Group'a katıl
            await self.channel_layer.group_add(
                self.activity_group_name,
                self.channel_name
            )
            
            await self.accept()
            
            # Son aktiviteleri gönder
            await self.send_recent_activities()
            
            logger.info(f"User {self.user.username} connected to live activities")
        else:
            await self.close()
    
    async def disconnect(self, close_code):
        """Aktivite feed bağlantısı kapandığında"""
        if hasattr(self, 'activity_group_name'):
            await self.channel_layer.group_discard(
                self.activity_group_name,
                self.channel_name
            )
            
            logger.info(f"User {self.user.username} disconnected from live activities")
    
    async def live_activity(self, event):
        """Canlı aktiviteyi WebSocket'e gönder"""
        await self.send(text_data=json.dumps({
            'type': 'live_activity',
            'activity': event['activity']
        }))
    
    @database_sync_to_async
    def send_recent_activities(self):
        """Son aktiviteleri gönder"""
        from .models import LiveActivity
        
        # Son 50 public aktiviteyi al
        recent_activities = LiveActivity.objects.filter(
            is_public=True
        )[:50]
        
        for activity in recent_activities:
            activity_data = {
                'id': activity.id,
                'user': activity.user.username,
                'activity_type': activity.activity_type,
                'description': activity.description,
                'created_at': activity.created_at.isoformat(),
                'extra_data': activity.extra_data
            }
            
            # Async olarak gönder
            self.send(text_data=json.dumps({
                'type': 'live_activity',
                'activity': activity_data
            }))
