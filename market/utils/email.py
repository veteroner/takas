from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.sites.models import Site
from django.urls import reverse
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class EmailService:
    """
    Profesyonel email gönderim servisi
    """
    
    @staticmethod
    def get_site_url():
        """Site URL'ini döndürür"""
        try:
            site = Site.objects.get_current()
            return f"http://{site.domain}"
        except:
            return "http://localhost:8000"
    
    @staticmethod
    def send_template_email(template_name, context, subject, recipient_list, 
                          from_email=None, fail_silently=False):
        """
        Template bazlı email gönderimi
        
        Args:
            template_name (str): Email template adı (örn: 'new_trade_offer')
            context (dict): Template context
            subject (str): Email konusu
            recipient_list (list): Alıcı email listesi
            from_email (str): Gönderen email (opsiyonel)
            fail_silently (bool): Hata durumunda sessiz kalma
        
        Returns:
            bool: Başarı durumu
        """
        try:
            # Default values
            if from_email is None:
                from_email = settings.DEFAULT_FROM_EMAIL
            
            # Site URL'ini context'e ekle
            context.update({
                'site_url': EmailService.get_site_url(),
                'unsubscribe_url': f"{EmailService.get_site_url()}/unsubscribe/",
            })
            
            # HTML template render
            html_template = f"emails/{template_name}.html"
            html_content = render_to_string(html_template, context)
            
            # Plain text template (opsiyonel)
            try:
                text_template = f"emails/{template_name}.txt"
                text_content = render_to_string(text_template, context)
            except:
                # HTML'den text oluştur (basit strip)
                import re
                text_content = re.sub('<[^<]+?>', '', html_content)
                text_content = ' '.join(text_content.split())
            
            # Subject prefix ekle
            full_subject = f"{settings.EMAIL_SUBJECT_PREFIX}{subject}"
            
            # Email oluştur
            email = EmailMultiAlternatives(
                subject=full_subject,
                body=text_content,
                from_email=from_email,
                to=recipient_list
            )
            
            # HTML alternatif ekle
            email.attach_alternative(html_content, "text/html")
            
            # Gönder
            result = email.send(fail_silently=fail_silently)
            
            logger.info(f"Email sent successfully: {template_name} to {recipient_list}")
            return result > 0
            
        except Exception as e:
            logger.error(f"Email sending failed: {str(e)}")
            if not fail_silently:
                raise
            return False


class TradeEmailService(EmailService):
    """Takas ile ilgili email servisleri"""
    
    @staticmethod
    def send_new_trade_offer_email(trade):
        """Yeni takas teklifi emaili"""
        recipient = trade.responder
        
        if not recipient.email:
            logger.warning(f"User {recipient.username} has no email address")
            return False
        
        context = {
            'trade': trade,
            'recipient': recipient,
        }
        
        return EmailService.send_template_email(
            template_name='new_trade_offer',
            context=context,
            subject=f'Yeni Takas Teklifi: {trade.offered_item.title}',
            recipient_list=[recipient.email],
            fail_silently=True
        )
    
    @staticmethod
    def send_trade_status_update_email(trade):
        """Takas durumu güncelleme emaili"""
        recipient = trade.requester
        
        if not recipient.email:
            logger.warning(f"User {recipient.username} has no email address")
            return False
        
        # Status'a göre konu belirle
        status_subjects = {
            'accepted': f'Harika Haber! Takas Kabul Edildi: {trade.requested_item.title}',
            'rejected': f'Takas Reddedildi: {trade.requested_item.title}',
            'cancelled': f'Takas İptal Edildi: {trade.requested_item.title}',
        }
        
        subject = status_subjects.get(
            trade.status, 
            f'Takas Durumu Güncellendi: {trade.requested_item.title}'
        )
        
        context = {
            'trade': trade,
            'recipient': recipient,
        }
        
        return EmailService.send_template_email(
            template_name='trade_status_update',
            context=context,
            subject=subject,
            recipient_list=[recipient.email],
            fail_silently=True
        )


class MessageEmailService(EmailService):
    """Mesaj ile ilgili email servisleri"""
    
    @staticmethod
    def send_new_message_email(message):
        """Yeni mesaj bildirimi emaili"""
        # Alıcıyı belirle (mesaj gönderen olmayan kişi)
        if message.sender == message.trade.requester:
            recipient = message.trade.responder
        else:
            recipient = message.trade.requester
        
        if not recipient.email:
            logger.warning(f"User {recipient.username} has no email address")
            return False
        
        context = {
            'message': message,
            'recipient': recipient,
        }
        
        return EmailService.send_template_email(
            template_name='new_message',
            context=context,
            subject=f'Yeni Mesaj: {message.sender.first_name or message.sender.username}',
            recipient_list=[recipient.email],
            fail_silently=True
        )


class AuthEmailService(EmailService):
    """Kimlik doğrulama ile ilgili email servisleri"""
    
    @staticmethod
    def send_password_reset_email(user, reset_url, request_ip=None):
        """Şifre sıfırlama emaili"""
        if not user.email:
            logger.warning(f"User {user.username} has no email address")
            return False
        
        context = {
            'user': user,
            'reset_url': reset_url,
            'request_ip': request_ip,
            'timestamp': timezone.now(),
        }
        
        return EmailService.send_template_email(
            template_name='password_reset',
            context=context,
            subject='Şifre Sıfırlama İsteği',
            recipient_list=[user.email],
            fail_silently=True
        )
    
    @staticmethod
    def send_welcome_email(user):
        """Hoşgeldin emaili"""
        if not user.email:
            return False
        
        context = {
            'user': user,
        }
        
        return EmailService.send_template_email(
            template_name='welcome',
            context=context,
            subject='Swapzy\'ye Hoşgeldiniz! 🎉',
            recipient_list=[user.email],
            fail_silently=True
        )


# Convenience functions
def notify_new_trade_offer(trade):
    """Yeni takas teklifi bildirimi"""
    return TradeEmailService.send_new_trade_offer_email(trade)

def notify_trade_status_update(trade):
    """Takas durumu güncelleme bildirimi"""
    return TradeEmailService.send_trade_status_update_email(trade)

def notify_new_message(message):
    """Yeni mesaj bildirimi"""
    return MessageEmailService.send_new_message_email(message)

def send_password_reset_notification(user, reset_url, request_ip=None):
    """Şifre sıfırlama bildirimi"""
    return AuthEmailService.send_password_reset_email(user, reset_url, request_ip)
