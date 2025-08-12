"""
🛡️ Advanced Security System
Enterprise-level güvenlik kontrolleri ve koruma mekanizmaları
"""

import hashlib
import secrets
import time
import ipaddress
import re
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from django.core.cache import cache
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.http import HttpRequest
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)


class SecurityManager:
    """Merkezi güvenlik yöneticisi"""
    
    def __init__(self):
        self.rate_limits = {
            'login': {'count': 5, 'window': 300},  # 5 attempts in 5 minutes
            'signup': {'count': 3, 'window': 3600},  # 3 signups per hour
            'api': {'count': 100, 'window': 3600},  # 100 API calls per hour
            'search': {'count': 50, 'window': 300},  # 50 searches in 5 minutes
            'upload': {'count': 10, 'window': 3600},  # 10 uploads per hour
            'message': {'count': 30, 'window': 300},  # 30 messages in 5 minutes
        }
        
        self.suspicious_patterns = [
            r'<script.*?>.*?</script>',  # XSS attempts
            r'union.*select.*from',  # SQL injection
            r'javascript:',  # JavaScript injection
            r'data:.*base64',  # Data URI attacks
            r'vbscript:',  # VBScript injection
            r'expression\(',  # CSS expression attacks
        ]
        
        self.blocked_user_agents = [
            'scanner', 'bot', 'crawler', 'spider', 'scraper',
            'hack', 'exploit', 'vulnerability', 'sqlmap'
        ]

    def check_rate_limit(self, request: HttpRequest, action: str) -> Tuple[bool, Dict]:
        """Rate limiting kontrolü"""
        if action not in self.rate_limits:
            return True, {}
        
        limit_config = self.rate_limits[action]
        identifier = self._get_request_identifier(request)
        cache_key = f"rate_limit:{action}:{identifier}"
        
        # Current attempts
        attempts = cache.get(cache_key, [])
        now = time.time()
        
        # Remove old attempts
        attempts = [attempt for attempt in attempts 
                   if now - attempt < limit_config['window']]
        
        # Check limit
        if len(attempts) >= limit_config['count']:
            return False, {
                'error': f'Rate limit exceeded for {action}',
                'retry_after': limit_config['window'] - (now - attempts[0]) if attempts else 0,
                'attempts': len(attempts),
                'limit': limit_config['count']
            }
        
        # Add current attempt
        attempts.append(now)
        cache.set(cache_key, attempts, limit_config['window'])
        
        return True, {
            'attempts': len(attempts),
            'limit': limit_config['count'],
            'window': limit_config['window']
        }

    def detect_suspicious_activity(self, request: HttpRequest) -> Tuple[bool, List[str]]:
        """Şüpheli aktivite tespiti"""
        suspicious_flags = []
        
        # Check request content for suspicious patterns
        content = self._extract_request_content(request)
        for pattern in self.suspicious_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                suspicious_flags.append(f"Suspicious pattern detected: {pattern}")
        
        # Check User-Agent
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        for blocked_agent in self.blocked_user_agents:
            if blocked_agent in user_agent:
                suspicious_flags.append(f"Blocked user agent: {blocked_agent}")
        
        # Check for rapid requests from same IP
        ip = self._get_client_ip(request)
        rapid_requests = self._check_rapid_requests(ip)
        if rapid_requests:
            suspicious_flags.append("Rapid requests detected")
        
        # Check for unusual request headers
        unusual_headers = self._check_unusual_headers(request)
        suspicious_flags.extend(unusual_headers)
        
        return len(suspicious_flags) > 0, suspicious_flags

    def validate_file_upload(self, uploaded_file) -> Tuple[bool, List[str]]:
        """Dosya yükleme güvenlik kontrolü"""
        errors = []
        
        # File size check
        max_size = 10 * 1024 * 1024  # 10MB
        if uploaded_file.size > max_size:
            errors.append(f"File too large: {uploaded_file.size} bytes (max: {max_size})")
        
        # File type check
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if uploaded_file.content_type not in allowed_types:
            errors.append(f"Invalid file type: {uploaded_file.content_type}")
        
        # File extension check
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        file_extension = uploaded_file.name.lower().split('.')[-1] if '.' in uploaded_file.name else ''
        if f'.{file_extension}' not in allowed_extensions:
            errors.append(f"Invalid file extension: {file_extension}")
        
        # Check for executable files disguised as images
        if self._is_executable_file(uploaded_file):
            errors.append("File appears to be executable")
        
        # Scan file content for malicious patterns
        malicious_content = self._scan_file_content(uploaded_file)
        if malicious_content:
            errors.extend(malicious_content)
        
        return len(errors) == 0, errors

    def encrypt_sensitive_data(self, data: str, key: Optional[str] = None) -> str:
        """Hassas veri şifreleme"""
        if not key:
            key = getattr(settings, 'ENCRYPTION_KEY', settings.SECRET_KEY[:32])
        
        # Simple XOR encryption (for demo - use proper encryption in production)
        encrypted = ''
        for i, char in enumerate(data):
            encrypted += chr(ord(char) ^ ord(key[i % len(key)]))
        
        return encrypted.encode('base64') if hasattr(encrypted, 'encode') else encrypted

    def decrypt_sensitive_data(self, encrypted_data: str, key: Optional[str] = None) -> str:
        """Şifrelenmiş veri çözme"""
        if not key:
            key = getattr(settings, 'ENCRYPTION_KEY', settings.SECRET_KEY[:32])
        
        # Reverse the XOR encryption
        try:
            decoded = encrypted_data.decode('base64') if hasattr(encrypted_data, 'decode') else encrypted_data
            decrypted = ''
            for i, char in enumerate(decoded):
                decrypted += chr(ord(char) ^ ord(key[i % len(key)]))
            return decrypted
        except Exception:
            return encrypted_data

    def log_security_event(self, event_type: str, request: HttpRequest, details: Dict):
        """Güvenlik olayını kaydet"""
        log_data = {
            'timestamp': timezone.now().isoformat(),
            'event_type': event_type,
            'ip_address': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'user': str(request.user) if hasattr(request, 'user') and hasattr(request.user, 'is_authenticated') and request.user.is_authenticated else 'Anonymous',
            'path': request.path,
            'method': request.method,
            'details': details
        }
        
        logger.warning(f"Security Event: {event_type}", extra=log_data)
        
        # Store in cache for real-time monitoring
        cache_key = f"security_events:{timezone.now().strftime('%Y%m%d')}"
        events = cache.get(cache_key, [])
        events.append(log_data)
        cache.set(cache_key, events[-100:], 86400)  # Keep last 100 events for 24h

    def block_ip(self, ip_address: str, duration: int = 3600, reason: str = "Security violation"):
        """IP adresini engelle"""
        cache_key = f"blocked_ip:{ip_address}"
        block_data = {
            'blocked_at': timezone.now().isoformat(),
            'duration': duration,
            'reason': reason
        }
        cache.set(cache_key, block_data, duration)
        
        logger.error(f"IP blocked: {ip_address} for {duration}s - {reason}")

    def is_ip_blocked(self, ip_address: str) -> Tuple[bool, Optional[Dict]]:
        """IP adresinin engellenip engellenmediğini kontrol et"""
        cache_key = f"blocked_ip:{ip_address}"
        block_data = cache.get(cache_key)
        
        if block_data:
            return True, block_data
        return False, None

    def _get_request_identifier(self, request: HttpRequest) -> str:
        """Request için benzersiz tanımlayıcı oluştur"""
        ip = self._get_client_ip(request)
        user_id = str(request.user.id) if request.user.is_authenticated else 'anonymous'
        return f"{ip}:{user_id}"

    def _get_client_ip(self, request: HttpRequest) -> str:
        """Gerçek client IP adresini al"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        
        # Validate IP address
        try:
            ipaddress.ip_address(ip)
            return ip
        except ValueError:
            return '127.0.0.1'

    def _extract_request_content(self, request: HttpRequest) -> str:
        """Request içeriğini çıkar"""
        content = ""
        
        # GET parameters
        content += str(request.GET)
        
        # POST data (if available)
        if hasattr(request, 'POST'):
            content += str(request.POST)
        
        # Path and query string
        content += request.get_full_path()
        
        return content.lower()

    def _check_rapid_requests(self, ip: str) -> bool:
        """Hızlı ardışık istekleri kontrol et"""
        cache_key = f"rapid_requests:{ip}"
        requests = cache.get(cache_key, [])
        now = time.time()
        
        # Remove old requests (last 60 seconds)
        requests = [req for req in requests if now - req < 60]
        
        # Check if more than 30 requests in last minute
        if len(requests) > 30:
            return True
        
        # Add current request
        requests.append(now)
        cache.set(cache_key, requests, 60)
        
        return False

    def _check_unusual_headers(self, request: HttpRequest) -> List[str]:
        """Olağandışı header'ları kontrol et"""
        unusual = []
        
        # Check for missing common headers
        if not request.META.get('HTTP_USER_AGENT'):
            unusual.append("Missing User-Agent header")
        
        if not request.META.get('HTTP_ACCEPT'):
            unusual.append("Missing Accept header")
        
        # Check for suspicious headers
        suspicious_headers = ['X-Forwarded-For', 'X-Real-IP', 'X-Originating-IP']
        for header in suspicious_headers:
            if f'HTTP_{header.replace("-", "_").upper()}' in request.META:
                value = request.META[f'HTTP_{header.replace("-", "_").upper()}']
                if ',' in value:  # Multiple IPs might indicate proxy chaining
                    unusual.append(f"Multiple IPs in {header}: {value}")
        
        return unusual

    def _is_executable_file(self, uploaded_file) -> bool:
        """Dosyanın çalıştırılabilir olup olmadığını kontrol et"""
        # Read first few bytes to check file signature
        try:
            uploaded_file.seek(0)
            header = uploaded_file.read(10)
            uploaded_file.seek(0)
            
            # Common executable signatures
            executable_signatures = [
                b'\x4d\x5a',  # PE (Windows executable)
                b'\x7f\x45\x4c\x46',  # ELF (Linux executable)
                b'\xfe\xed\xfa',  # Mach-O (macOS executable)
                b'\xcf\xfa\xed\xfe',  # Mach-O (32-bit)
            ]
            
            for signature in executable_signatures:
                if header.startswith(signature):
                    return True
                    
        except Exception:
            pass
        
        return False

    def _scan_file_content(self, uploaded_file) -> List[str]:
        """Dosya içeriğinde zararlı pattern'leri tara"""
        issues = []
        
        try:
            uploaded_file.seek(0)
            content = uploaded_file.read(1024)  # Read first 1KB
            uploaded_file.seek(0)
            
            # Convert to string if possible
            try:
                text_content = content.decode('utf-8', errors='ignore')
            except:
                text_content = str(content)
            
            # Check for script tags and other malicious content
            malicious_patterns = [
                '<script', '</script>', 'javascript:', 'vbscript:',
                'onload=', 'onerror=', 'onclick=', 'eval(',
                'document.cookie', 'window.location'
            ]
            
            for pattern in malicious_patterns:
                if pattern.lower() in text_content.lower():
                    issues.append(f"Malicious pattern detected: {pattern}")
                    
        except Exception as e:
            issues.append(f"File content scan error: {str(e)}")
        
        return issues


class UserSecurityManager:
    """Kullanıcı güvenliği yöneticisi"""
    
    def __init__(self):
        self.password_requirements = {
            'min_length': 8,
            'require_uppercase': True,
            'require_lowercase': True,
            'require_numbers': True,
            'require_special': True,
            'special_chars': '!@#$%^&*()_+-=[]{}|;:,.<>?'
        }

    def validate_password_strength(self, password: str) -> Tuple[bool, List[str]]:
        """Şifre gücünü doğrula"""
        errors = []
        req = self.password_requirements
        
        if len(password) < req['min_length']:
            errors.append(f"Password must be at least {req['min_length']} characters long")
        
        if req['require_uppercase'] and not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        if req['require_lowercase'] and not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        if req['require_numbers'] and not re.search(r'\d', password):
            errors.append("Password must contain at least one number")
        
        if req['require_special'] and not any(char in req['special_chars'] for char in password):
            errors.append(f"Password must contain at least one special character: {req['special_chars']}")
        
        # Check for common weak patterns
        weak_patterns = [
            (r'(.)\1{2,}', "Password cannot contain repeated characters"),
            (r'(012|123|234|345|456|567|678|789|890)', "Password cannot contain sequential numbers"),
            (r'(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)', "Password cannot contain sequential letters"),
        ]
        
        for pattern, error_msg in weak_patterns:
            if re.search(pattern, password, re.IGNORECASE):
                errors.append(error_msg)
        
        return len(errors) == 0, errors

    def generate_secure_token(self, length: int = 32) -> str:
        """Güvenli token oluştur"""
        return secrets.token_urlsafe(length)

    def hash_sensitive_data(self, data: str) -> str:
        """Hassas veriyi hash'le"""
        salt = secrets.token_hex(16)
        return hashlib.pbkdf2_hmac('sha256', data.encode(), salt.encode(), 100000).hex() + ':' + salt

    def verify_hashed_data(self, data: str, hashed_data: str) -> bool:
        """Hash'lenmiş veriyi doğrula"""
        try:
            hash_part, salt = hashed_data.split(':')
            return hashlib.pbkdf2_hmac('sha256', data.encode(), salt.encode(), 100000).hex() == hash_part
        except:
            return False

    def check_user_security_status(self, user) -> Dict[str, Any]:
        """Kullanıcının güvenlik durumunu kontrol et"""
        status = {
            'strong_password': False,
            'recent_login': False,
            'suspicious_activity': False,
            'security_score': 0,
            'recommendations': []
        }
        
        # Check login activity
        if hasattr(user, 'last_login') and user.last_login:
            days_since_login = (timezone.now() - user.last_login).days
            status['recent_login'] = days_since_login < 30
            
            if days_since_login > 90:
                status['recommendations'].append("Consider logging in more frequently")
        
        # Check for suspicious login patterns
        suspicious_logins = self._check_suspicious_logins(user)
        status['suspicious_activity'] = suspicious_logins
        
        if suspicious_logins:
            status['recommendations'].append("Review recent login activity")
        
        # Calculate security score
        score = 0
        if status['strong_password']:
            score += 30
        if status['recent_login']:
            score += 20
        if not status['suspicious_activity']:
            score += 25
        if user.is_active:
            score += 15
        if user.email:
            score += 10
        
        status['security_score'] = score
        
        # Add recommendations based on score
        if score < 50:
            status['recommendations'].append("Update your password to a stronger one")
        if score < 70:
            status['recommendations'].append("Enable additional security features")
        
        return status

    def _check_suspicious_logins(self, user) -> bool:
        """Şüpheli giriş pattern'lerini kontrol et"""
        # Check cache for user's recent login attempts
        cache_key = f"login_attempts:{user.id}"
        attempts = cache.get(cache_key, [])
        
        if len(attempts) > 10:  # Too many recent attempts
            return True
        
        # Check for logins from multiple IPs in short time
        if len(set(attempt.get('ip') for attempt in attempts[-5:])) > 3:
            return True
        
        return False


# Global instances
security_manager = SecurityManager()
user_security_manager = UserSecurityManager()
