"""
⚡ Performance Monitoring Middleware
Real-time performance tracking and optimization
"""

import time
from django.utils.deprecation import MiddlewareMixin
from django.db import connection
from ..utils.performance import performance_monitor, query_optimizer
from ..utils.monitoring import performance_analyzer, error_tracker
import logging

logger = logging.getLogger(__name__)


class PerformanceMiddleware(MiddlewareMixin):
    """Performance monitoring and optimization middleware"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)

    def process_request(self, request):
        """Request başlangıcı - timing başlat"""
        request._performance_start_time = time.time()
        request._performance_initial_queries = len(connection.queries)
        return None

    def process_response(self, request, response):
        """Response sonunda - performance ölç"""
        
        if not hasattr(request, '_performance_start_time'):
            return response
        
        # Calculate metrics
        response_time = time.time() - request._performance_start_time
        query_count = len(connection.queries) - request._performance_initial_queries
        
        # Calculate database time
        db_time = 0
        if query_count > 0:
            recent_queries = connection.queries[-query_count:]
            db_time = sum(float(query['time']) for query in recent_queries)
        
        # Collect request data
        request_data = {
            'path': request.path,
            'method': request.method,
            'response_time': response_time,
            'db_time': db_time,
            'query_count': query_count,
            'status_code': response.status_code,
            'user': str(request.user) if request.user.is_authenticated else 'anonymous',
            'timestamp': time.time()
        }
        
        # Track performance
        performance_analyzer.analyze_request_performance(request_data)
        
        # Log slow requests
        if response_time > 1.0:  # 1 second threshold
            logger.warning(
                f"Slow request: {request.method} {request.path} "
                f"took {response_time:.3f}s with {query_count} queries"
            )
        
        # Add performance headers
        response['X-Response-Time'] = f"{response_time:.3f}s"
        response['X-DB-Queries'] = str(query_count)
        response['X-DB-Time'] = f"{db_time:.3f}s"
        
        return response

    def process_exception(self, request, exception):
        """Exception durumunda error tracking"""
        error_tracker.track_error(
            error_type=type(exception).__name__,
            error_message=str(exception),
            context={
                'path': request.path,
                'method': request.method,
                'user': str(request.user) if request.user.is_authenticated else 'anonymous'
            }
        )
        return None


class DatabaseOptimizationMiddleware(MiddlewareMixin):
    """Database query optimization middleware"""
    
    def process_response(self, request, response):
        """Database query'lerini analiz et ve optimize et"""
        
        # Analyze queries for optimization opportunities
        if hasattr(connection, 'queries') and connection.queries:
            slow_queries = []
            duplicate_queries = {}
            
            for query in connection.queries:
                query_time = float(query['time'])
                query_sql = query['sql']
                
                # Track slow queries
                if query_time > 0.1:  # 100ms threshold
                    slow_queries.append({
                        'sql': query_sql,
                        'time': query_time
                    })
                
                # Track duplicate queries
                if query_sql in duplicate_queries:
                    duplicate_queries[query_sql] += 1
                else:
                    duplicate_queries[query_sql] = 1
            
            # Log optimization opportunities
            if slow_queries:
                logger.warning(f"Found {len(slow_queries)} slow queries on {request.path}")
            
            duplicates = {sql: count for sql, count in duplicate_queries.items() if count > 1}
            if duplicates:
                logger.warning(f"Found {len(duplicates)} duplicate queries on {request.path}")
        
        return response


class CacheMiddleware(MiddlewareMixin):
    """Intelligent caching middleware"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.cacheable_paths = [
            '/api/',
            '/search/',
            '/recommendations/'
        ]
        self.cache_timeout = 300  # 5 minutes
        super().__init__(get_response)

    def process_request(self, request):
        """Check if response is cached"""
        
        # Only cache GET requests
        if request.method != 'GET':
            return None
        
        # Only cache specific paths
        if not any(request.path.startswith(path) for path in self.cacheable_paths):
            return None
        
        # Skip authenticated users for now (could be enhanced)
        if request.user.is_authenticated:
            return None
        
        cache_key = self._generate_cache_key(request)
        
        # Try to get from cache
        from django.core.cache import cache
        cached_response = cache.get(cache_key)
        
        if cached_response:
            logger.debug(f"Cache hit for {request.path}")
            return cached_response
        
        return None

    def process_response(self, request, response):
        """Cache response if appropriate"""
        
        # Only cache successful GET responses
        if (request.method == 'GET' and 
            response.status_code == 200 and
            any(request.path.startswith(path) for path in self.cacheable_paths)):
            
            cache_key = self._generate_cache_key(request)
            
            from django.core.cache import cache
            cache.set(cache_key, response, self.cache_timeout)
            
            response['X-Cache-Status'] = 'MISS'
            logger.debug(f"Cached response for {request.path}")
        
        return response

    def _generate_cache_key(self, request):
        """Generate cache key for request"""
        import hashlib
        
        key_parts = [
            request.path,
            request.GET.urlencode(),
            str(request.user.id) if request.user.is_authenticated else 'anonymous'
        ]
        
        key_string = '|'.join(key_parts)
        return f"cache_middleware:{hashlib.md5(key_string.encode()).hexdigest()}"


class CompressionMiddleware(MiddlewareMixin):
    """Response compression middleware"""
    
    def process_response(self, request, response):
        """Compress response if appropriate"""
        
        # Check if compression is supported
        accept_encoding = request.META.get('HTTP_ACCEPT_ENCODING', '')
        if 'gzip' not in accept_encoding.lower():
            return response
        
        # Only compress large responses
        if not hasattr(response, 'content') or len(response.content) < 1024:
            return response
        
        # Only compress specific content types
        content_type = response.get('Content-Type', '').lower()
        compressible_types = [
            'text/html',
            'text/css',
            'text/javascript',
            'application/javascript',
            'application/json',
            'text/plain'
        ]
        
        if not any(ct in content_type for ct in compressible_types):
            return response
        
        try:
            import gzip
            import io
            
            # Compress content
            buffer = io.BytesIO()
            with gzip.GzipFile(fileobj=buffer, mode='wb') as f:
                f.write(response.content)
            
            compressed_content = buffer.getvalue()
            
            # Only use compression if it actually reduces size
            if len(compressed_content) < len(response.content):
                response.content = compressed_content
                response['Content-Encoding'] = 'gzip'
                response['Content-Length'] = str(len(compressed_content))
                
                # Calculate compression ratio
                original_size = len(response.content)
                compressed_size = len(compressed_content)
                compression_ratio = (1 - compressed_size / original_size) * 100
                
                response['X-Compression-Ratio'] = f"{compression_ratio:.1f}%"
        
        except Exception as e:
            # Don't fail the request if compression fails
            logger.warning(f"Compression failed: {str(e)}")
        
        return response
