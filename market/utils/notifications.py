"""
📡 Real-time Notification Service
Bu modül gerçek zamanlı bildirim yönetimi için gerekli servisleri sağlar.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)


class NotificationService:
    """Gerçek zamanlı bildirim servisi"""
    
    @staticmethod
    def create_notification(
        recipient: User,
        notification_type: str,
        title: str,
        message: str,
        sender: Optional[User] = None,
        content_object: Optional[Any] = None,
        action_url: str = "",
        extra_data: Dict = None,
        send_realtime: bool = True
    ) -> 'Notification':
        """
        Yeni bildirim oluştur ve gönder
        
        Args:
            recipient: Bildirimi alacak kullanıcı
            notification_type: Bildirim türü
            title: Bildirim başlığı
            message: Bildirim mesajı
            sender: Bildirimi gönderen kullanıcı (opsiyonel)
            content_object: İlgili Django modeli (opsiyonel)
            action_url: Tıklandığında gidilecek URL
            extra_data: Ek JSON data
            send_realtime: Gerçek zamanlı gönderilsin mi?
        
        Returns:
            Oluşturulan Notification objesi
        """
        from ..models import Notification
        
        if extra_data is None:
            extra_data = {}
        
        # Content type ve object ID belirle
        content_type = None
        object_id = None
        if content_object:
            content_type = ContentType.objects.get_for_model(content_object)
            object_id = content_object.pk
        
        # Bildirimi oluştur
        notification = Notification.objects.create(
            recipient=recipient,
            sender=sender,
            notification_type=notification_type,
            title=title,
            message=message,
            content_type=content_type,
            object_id=object_id,
            action_url=action_url,
            extra_data=extra_data
        )
        
        logger.info(f"Created notification {notification.id} for {recipient.username}")
        
        # Gerçek zamanlı gönder
        if send_realtime:
            NotificationService.send_realtime_notification(notification)
        
        return notification
    
    @staticmethod
    def send_realtime_notification(notification: 'Notification'):
        """Bildirimi WebSocket ile gerçek zamanlı gönder"""
        channel_layer = get_channel_layer()
        
        if channel_layer:
            notification_data = {
                'id': notification.id,
                'type': notification.notification_type,
                'title': notification.title,
                'message': notification.message,
                'created_at': notification.created_at.isoformat(),
                'action_url': notification.action_url,
                'extra_data': notification.extra_data,
                'sender': notification.sender.username if notification.sender else None,
                'time_since': notification.time_since_created
            }
            
            # Kullanıcıya özel group'a gönder
            group_name = f"notifications_{notification.recipient.id}"
            
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    'type': 'send_notification',
                    'notification': notification_data
                }
            )
            
            # Bildirim gönderildi olarak işaretle
            notification.is_sent = True
            notification.save()
            
            logger.info(f"Sent realtime notification {notification.id} to {notification.recipient.username}")
        else:
            logger.warning("Channel layer not available for realtime notifications")
    
    @staticmethod
    def send_trade_request_notification(trade: 'Trade'):
        """Takas teklifi bildirimi"""
        NotificationService.create_notification(
            recipient=trade.responder,
            notification_type='trade_request',
            title=f"🔄 Yeni Takas Teklifi",
            message=f"{trade.requester.first_name or trade.requester.username} sizden {trade.requested_item.title} için {trade.offered_item.title} takası istiyor.",
            sender=trade.requester,
            content_object=trade,
            action_url=f"/trade/{trade.id}/",
            extra_data={
                'trade_id': trade.id,
                'offered_item': trade.offered_item.title,
                'requested_item': trade.requested_item.title
            }
        )
    
    @staticmethod
    def send_trade_response_notification(trade: 'Trade', accepted: bool):
        """Takas yanıt bildirimi"""
        action = "kabul etti" if accepted else "reddetti"
        emoji = "✅" if accepted else "❌"
        
        NotificationService.create_notification(
            recipient=trade.requester,
            notification_type='trade_accepted' if accepted else 'trade_rejected',
            title=f"{emoji} Takas {action.title()}",
            message=f"{trade.responder.first_name or trade.responder.username} takas teklifinizi {action}.",
            sender=trade.responder,
            content_object=trade,
            action_url=f"/trade/{trade.id}/",
            extra_data={
                'trade_id': trade.id,
                'accepted': accepted,
                'offered_item': trade.offered_item.title,
                'requested_item': trade.requested_item.title
            }
        )
    
    @staticmethod
    def send_message_notification(message: 'Message', recipient: User):
        """Yeni mesaj bildirimi"""
        NotificationService.create_notification(
            recipient=recipient,
            notification_type='new_message',
            title=f"💬 Yeni Mesaj",
            message=f"{message.sender.first_name or message.sender.username}: {message.content[:50]}{'...' if len(message.content) > 50 else ''}",
            sender=message.sender,
            content_object=message.trade,
            action_url=f"/trade/{message.trade.id}/",
            extra_data={
                'trade_id': message.trade.id,
                'message_id': message.id,
                'message_preview': message.content[:100]
            }
        )
    
    @staticmethod
    def send_item_liked_notification(item: 'Item', liker: User):
        """Ürün beğenildi bildirimi"""
        NotificationService.create_notification(
            recipient=item.owner,
            notification_type='item_liked',
            title=f"❤️ Ürününüz Beğenildi",
            message=f"{liker.first_name or liker.username} '{item.title}' ürününüzü beğendi.",
            sender=liker,
            content_object=item,
            action_url=f"/items/{item.id}/",
            extra_data={
                'item_id': item.id,
                'item_title': item.title,
                'liker_username': liker.username
            }
        )
    
    @staticmethod
    def send_recommendation_notification(recommendation: 'MatchRecommendation'):
        """Yeni öneri bildirimi"""
        NotificationService.create_notification(
            recipient=recommendation.user,
            notification_type='new_recommendation',
            title=f"🎯 Size Özel Öneri",
            message=f"'{recommendation.recommended_item.title}' sizin için mükemmel bir eşleşme! Eşleşme: {recommendation.match_score:.0f}%",
            content_object=recommendation.recommended_item,
            action_url=f"/items/{recommendation.recommended_item.id}/",
            extra_data={
                'recommendation_id': recommendation.id,
                'item_id': recommendation.recommended_item.id,
                'match_score': recommendation.match_score,
                'recommendation_type': recommendation.recommendation_type
            }
        )
    
    @staticmethod
    def get_unread_count(user: User) -> int:
        """Kullanıcının okunmamış bildirim sayısı"""
        from ..models import Notification
        
        return Notification.objects.filter(
            recipient=user,
            is_read=False
        ).count()
    
    @staticmethod
    def mark_all_read(user: User) -> int:
        """Kullanıcının tüm bildirimlerini okundu olarak işaretle"""
        from ..models import Notification
        
        return Notification.objects.filter(
            recipient=user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
    
    @staticmethod
    def cleanup_old_notifications(days: int = 30):
        """Eski bildirimleri temizle"""
        from ..models import Notification
        
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        deleted_count = Notification.objects.filter(
            created_at__lt=cutoff_date,
            is_read=True
        ).delete()[0]
        
        logger.info(f"Cleaned up {deleted_count} old notifications")
        return deleted_count


class LiveActivityService:
    """Canlı aktivite feed servisi"""
    
    @staticmethod
    def create_activity(
        user: User,
        activity_type: str,
        description: str,
        content_object: Optional[Any] = None,
        extra_data: Dict = None,
        is_public: bool = True,
        broadcast: bool = True
    ) -> 'LiveActivity':
        """
        Yeni aktivite oluştur ve broadcast et
        
        Args:
            user: Aktiviteyi yapan kullanıcı
            activity_type: Aktivite türü
            description: Aktivite açıklaması
            content_object: İlgili Django modeli
            extra_data: Ek JSON data
            is_public: Herkese gösterilsin mi?
            broadcast: Gerçek zamanlı broadcast edilsin mi?
        
        Returns:
            Oluşturulan LiveActivity objesi
        """
        from ..models import LiveActivity
        
        if extra_data is None:
            extra_data = {}
        
        # Content type ve object ID belirle
        content_type = None
        object_id = None
        if content_object:
            content_type = ContentType.objects.get_for_model(content_object)
            object_id = content_object.pk
        
        # Aktiviteyi oluştur
        activity = LiveActivity.objects.create(
            user=user,
            activity_type=activity_type,
            description=description,
            content_type=content_type,
            object_id=object_id,
            extra_data=extra_data,
            is_public=is_public
        )
        
        logger.info(f"Created activity {activity.id} for {user.username}")
        
        # Gerçek zamanlı broadcast
        if broadcast and is_public:
            LiveActivityService.broadcast_activity(activity)
        
        return activity
    
    @staticmethod
    def broadcast_activity(activity: 'LiveActivity'):
        """Aktiviteyi WebSocket ile broadcast et"""
        channel_layer = get_channel_layer()
        
        if channel_layer:
            activity_data = {
                'id': activity.id,
                'user': activity.user.username,
                'user_display': activity.user.first_name or activity.user.username,
                'activity_type': activity.activity_type,
                'description': activity.description,
                'created_at': activity.created_at.isoformat(),
                'extra_data': activity.extra_data
            }
            
            # Global aktivite feed'ine gönder
            async_to_sync(channel_layer.group_send)(
                "live_activities",
                {
                    'type': 'live_activity',
                    'activity': activity_data
                }
            )
            
            logger.info(f"Broadcasted activity {activity.id}")
        else:
            logger.warning("Channel layer not available for activity broadcast")
    
    @staticmethod
    def track_item_created(item: 'Item'):
        """Yeni ürün oluşturma aktivitesi"""
        LiveActivityService.create_activity(
            user=item.owner,
            activity_type='item_created',
            description=f"{item.owner.first_name or item.owner.username} yeni bir ürün ekledi: {item.title}",
            content_object=item,
            extra_data={
                'item_id': item.id,
                'item_title': item.title,
                'item_category': item.get_category_display()
            }
        )
    
    @staticmethod
    def track_trade_created(trade: 'Trade'):
        """Yeni takas aktivitesi"""
        LiveActivityService.create_activity(
            user=trade.requester,
            activity_type='trade_created',
            description=f"{trade.requester.first_name or trade.requester.username} takas teklifi yaptı",
            content_object=trade,
            extra_data={
                'trade_id': trade.id,
                'offered_item': trade.offered_item.title,
                'requested_item': trade.requested_item.title
            }
        )
    
    @staticmethod
    def track_trade_completed(trade: 'Trade'):
        """Takas tamamlandı aktivitesi"""
        LiveActivityService.create_activity(
            user=trade.requester,
            activity_type='trade_completed',
            description=f"Başarılı takas: {trade.offered_item.title} ↔ {trade.requested_item.title}",
            content_object=trade,
            extra_data={
                'trade_id': trade.id,
                'offered_item': trade.offered_item.title,
                'requested_item': trade.requested_item.title,
                'requester': trade.requester.username,
                'responder': trade.responder.username
            }
        )
    
    @staticmethod
    def track_user_joined(user: User):
        """Yeni üye aktivitesi"""
        LiveActivityService.create_activity(
            user=user,
            activity_type='user_joined',
            description=f"{user.first_name or user.username} Swapzy'ye katıldı! 👋",
            extra_data={
                'user_id': user.id,
                'username': user.username,
                'join_date': user.date_joined.isoformat()
            }
        )


class OnlineStatusService:
    """Kullanıcı online durumu servisi"""
    
    @staticmethod
    def get_online_users() -> List[User]:
        """Online kullanıcıları getir"""
        from ..models import UserOnlineStatus
        
        online_statuses = UserOnlineStatus.objects.filter(is_online=True)
        return [status.user for status in online_statuses]
    
    @staticmethod
    def get_online_count() -> int:
        """Online kullanıcı sayısı"""
        from ..models import UserOnlineStatus
        
        return UserOnlineStatus.objects.filter(is_online=True).count()
    
    @staticmethod
    def is_user_online(user: User) -> bool:
        """Kullanıcı online mı?"""
        from ..models import UserOnlineStatus
        
        try:
            status = UserOnlineStatus.objects.get(user=user)
            return status.is_online
        except UserOnlineStatus.DoesNotExist:
            return False
    
    @staticmethod
    def broadcast_status_change(user: User, is_online: bool):
        """Durum değişikliğini broadcast et"""
        channel_layer = get_channel_layer()
        
        if channel_layer:
            status_data = {
                'user': user.username,
                'user_display': user.first_name or user.username,
                'is_online': is_online,
                'timestamp': timezone.now().isoformat()
            }
            
            # Tüm notification consumer'lara gönder
            async_to_sync(channel_layer.group_send)(
                "notifications_broadcast",
                {
                    'type': 'user_status_update',
                    'status': status_data
                }
            )
            
            logger.info(f"Broadcasted status change for {user.username}: {'online' if is_online else 'offline'}")
