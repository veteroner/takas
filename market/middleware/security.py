"""
🛡️ Security Middleware
Real-time güvenlik kontrolleri ve koruma katmanları
"""

import time
import json
from django.http import HttpResponse, JsonResponse
from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from ..utils.security import security_manager
import logging

logger = logging.getLogger(__name__)


class SecurityMiddleware(MiddlewareMixin):
    """Ana güvenlik middleware'i"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)

    def process_request(self, request):
        """Her request'te güvenlik kontrolleri"""
        
        # 1. IP Block Check
        client_ip = security_manager._get_client_ip(request)
        is_blocked, block_data = security_manager.is_ip_blocked(client_ip)
        
        if is_blocked:
            logger.warning(f"Blocked IP attempted access: {client_ip}")
            return JsonResponse({
                'error': 'Access denied',
                'reason': block_data.get('reason', 'Security violation'),
                'blocked_until': block_data.get('blocked_at')
            }, status=403)
        
        # 2. Rate Limiting
        action = self._determine_action(request)
        if action:
            allowed, rate_info = security_manager.check_rate_limit(request, action)
            
            if not allowed:
                security_manager.log_security_event(
                    'rate_limit_exceeded',
                    request,
                    {'action': action, 'rate_info': rate_info}
                )
                
                return JsonResponse({
                    'error': 'Rate limit exceeded',
                    'retry_after': rate_info.get('retry_after', 0),
                    'limit': rate_info.get('limit', 0)
                }, status=429)
        
        # 3. Suspicious Activity Detection
        is_suspicious, flags = security_manager.detect_suspicious_activity(request)
        
        if is_suspicious:
            security_manager.log_security_event(
                'suspicious_activity',
                request,
                {'flags': flags}
            )
            
            # Block IP after multiple suspicious activities
            suspicious_count = self._get_suspicious_count(client_ip)
            if suspicious_count > 3:
                security_manager.block_ip(
                    client_ip,
                    duration=3600,  # 1 hour
                    reason='Multiple suspicious activities'
                )
                
                return JsonResponse({
                    'error': 'Access denied',
                    'reason': 'Suspicious activity detected'
                }, status=403)
        
        # 4. Store request metadata for monitoring
        self._store_request_metadata(request)
        
        return None

    def process_response(self, request, response):
        """Response işleme - güvenlik header'ları ekle"""
        
        # Security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Content-Security-Policy'] = self._get_csp_header()
        
        # Custom security headers
        response['X-Security-Level'] = 'high'
        response['X-Powered-By'] = ''  # Hide server info
        
        return response

    def _determine_action(self, request):
        """Request'ten action tipini belirle"""
        path = request.path.lower()
        
        if '/login' in path or '/signin' in path:
            return 'login'
        elif '/signup' in path or '/register' in path:
            return 'signup'
        elif '/api/' in path:
            return 'api'
        elif '/search' in path:
            return 'search'
        elif '/upload' in path or request.method == 'POST' and request.FILES:
            return 'upload'
        elif '/message' in path or '/chat' in path:
            return 'message'
        
        return None

    def _get_suspicious_count(self, ip):
        """IP için şüpheli aktivite sayısını al"""
        cache_key = f"suspicious_count:{ip}"
        count = cache.get(cache_key, 0)
        cache.set(cache_key, count + 1, 3600)  # 1 hour window
        return count + 1

    def _store_request_metadata(self, request):
        """Request metadata'sını monitoring için sakla"""
        metadata = {
            'timestamp': time.time(),
            'ip': security_manager._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'path': request.path,
            'method': request.method,
            'user': str(request.user) if request.user.is_authenticated else 'anonymous'
        }
        
        # Store in cache for real-time monitoring
        cache_key = f"request_metadata:{metadata['ip']}"
        recent_requests = cache.get(cache_key, [])
        recent_requests.append(metadata)
        
        # Keep only last 50 requests
        recent_requests = recent_requests[-50:]
        cache.set(cache_key, recent_requests, 3600)

    def _get_csp_header(self):
        """Content Security Policy header oluştur"""
        return (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' ws: wss:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )


class DDoSProtectionMiddleware(MiddlewareMixin):
    """DDoS koruma middleware'i"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.request_threshold = 100  # requests per minute
        self.window_size = 60  # seconds
        super().__init__(get_response)

    def process_request(self, request):
        """DDoS saldırılarını tespit et ve engelle"""
        
        client_ip = security_manager._get_client_ip(request)
        cache_key = f"ddos_protection:{client_ip}"
        
        # Get current request count
        current_requests = cache.get(cache_key, [])
        now = time.time()
        
        # Remove old requests outside the window
        current_requests = [req_time for req_time in current_requests 
                          if now - req_time < self.window_size]
        
        # Check if threshold exceeded
        if len(current_requests) >= self.request_threshold:
            logger.error(f"DDoS attack detected from IP: {client_ip}")
            
            # Block IP for 1 hour
            security_manager.block_ip(
                client_ip,
                duration=3600,
                reason='DDoS attack detected'
            )
            
            security_manager.log_security_event(
                'ddos_attack',
                request,
                {'requests_per_minute': len(current_requests)}
            )
            
            return JsonResponse({
                'error': 'Too many requests',
                'message': 'DDoS protection activated'
            }, status=429)
        
        # Add current request
        current_requests.append(now)
        cache.set(cache_key, current_requests, self.window_size)
        
        return None


class FileUploadSecurityMiddleware(MiddlewareMixin):
    """Dosya yükleme güvenlik middleware'i"""
    
    def process_request(self, request):
        """Dosya yüklemelerini güvenlik açısından kontrol et"""
        
        if request.method == 'POST' and request.FILES:
            for field_name, uploaded_file in request.FILES.items():
                
                # Security validation
                is_valid, errors = security_manager.validate_file_upload(uploaded_file)
                
                if not is_valid:
                    security_manager.log_security_event(
                        'malicious_file_upload',
                        request,
                        {'errors': errors, 'filename': uploaded_file.name}
                    )
                    
                    return JsonResponse({
                        'error': 'File upload rejected',
                        'reasons': errors
                    }, status=400)
        
        return None


class APISecurityMiddleware(MiddlewareMixin):
    """API güvenlik middleware'i"""
    
    def process_request(self, request):
        """API endpoint'leri için özel güvenlik kontrolleri"""
        
        if not request.path.startswith('/api/'):
            return None
        
        # Check API key if required
        if self._requires_api_key(request.path):
            api_key = request.META.get('HTTP_X_API_KEY')
            if not self._validate_api_key(api_key):
                return JsonResponse({
                    'error': 'Invalid or missing API key'
                }, status=401)
        
        # Validate JSON payload
        if request.content_type == 'application/json':
            try:
                if hasattr(request, 'body') and request.body:
                    json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({
                    'error': 'Invalid JSON payload'
                }, status=400)
        
        # Check request size
        if hasattr(request, 'content_length') and request.content_length:
            max_size = 10 * 1024 * 1024  # 10MB
            if request.content_length > max_size:
                return JsonResponse({
                    'error': 'Request too large'
                }, status=413)
        
        return None

    def _requires_api_key(self, path):
        """API key gerektiren endpoint'leri kontrol et"""
        # For now, no endpoints require API key
        # In production, you might require API keys for certain endpoints
        return False

    def _validate_api_key(self, api_key):
        """API key'i doğrula"""
        if not api_key:
            return False
        
        # Simple validation - in production use proper API key management
        valid_keys = getattr(settings, 'API_KEYS', [])
        return api_key in valid_keys


class SessionSecurityMiddleware(MiddlewareMixin):
    """Session güvenlik middleware'i"""
    
    def process_request(self, request):
        """Session güvenliği kontrolleri"""
        
        if request.user.is_authenticated:
            
            # Check session timeout
            last_activity = request.session.get('last_activity')
            if last_activity:
                inactive_time = time.time() - last_activity
                max_inactive_time = getattr(settings, 'SESSION_TIMEOUT', 3600)  # 1 hour
                
                if inactive_time > max_inactive_time:
                    request.session.flush()
                    return JsonResponse({
                        'error': 'Session expired',
                        'redirect': '/accounts/login/'
                    }, status=401)
            
            # Update last activity
            request.session['last_activity'] = time.time()
            
            # Check for session hijacking
            stored_ip = request.session.get('ip_address')
            current_ip = security_manager._get_client_ip(request)
            
            if stored_ip and stored_ip != current_ip:
                # Potential session hijacking
                security_manager.log_security_event(
                    'session_hijacking_attempt',
                    request,
                    {'stored_ip': stored_ip, 'current_ip': current_ip}
                )
                
                request.session.flush()
                return JsonResponse({
                    'error': 'Session security violation',
                    'redirect': '/accounts/login/'
                }, status=401)
            
            # Store current IP for future checks
            request.session['ip_address'] = current_ip
        
        return None
