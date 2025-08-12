"""
⚡ Performance Optimization System
Database optimization, caching strategies, and performance monitoring
"""

import time
import functools
import hashlib
from typing import Any, Dict, List, Optional, Callable
from django.core.cache import cache
from django.db import models, connection
from django.conf import settings
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import QuerySet
import logging

logger = logging.getLogger(__name__)


class QueryOptimizer:
    """Database query optimization manager"""
    
    def __init__(self):
        self.slow_query_threshold = 0.1  # 100ms
        self.query_stats = {}

    def optimize_queryset(self, queryset: QuerySet, relations: List[str] = None) -> QuerySet:
        """QuerySet optimizasyonu"""
        if relations:
            # Use select_related for ForeignKey and OneToOne
            foreign_relations = [rel for rel in relations if '__' not in rel]
            if foreign_relations:
                queryset = queryset.select_related(*foreign_relations)
            
            # Use prefetch_related for ManyToMany and reverse ForeignKey
            many_relations = [rel for rel in relations if '__' in rel or rel.endswith('_set')]
            if many_relations:
                queryset = queryset.prefetch_related(*many_relations)
        
        return queryset

    def bulk_create_optimized(self, model_class, objects: List[Dict], batch_size: int = 1000):
        """Optimized bulk create"""
        model_objects = [model_class(**obj) for obj in objects]
        
        # Use bulk_create with batch_size for better performance
        created_objects = []
        for i in range(0, len(model_objects), batch_size):
            batch = model_objects[i:i + batch_size]
            created_objects.extend(
                model_class.objects.bulk_create(batch, ignore_conflicts=True)
            )
        
        return created_objects

    def bulk_update_optimized(self, objects: List[models.Model], fields: List[str], batch_size: int = 1000):
        """Optimized bulk update"""
        for i in range(0, len(objects), batch_size):
            batch = objects[i:i + batch_size]
            objects[0].__class__.objects.bulk_update(batch, fields)

    def track_query_performance(self, query_name: str, execution_time: float):
        """Query performansını takip et"""
        if query_name not in self.query_stats:
            self.query_stats[query_name] = {
                'total_time': 0,
                'count': 0,
                'slow_queries': 0,
                'avg_time': 0
            }
        
        stats = self.query_stats[query_name]
        stats['total_time'] += execution_time
        stats['count'] += 1
        stats['avg_time'] = stats['total_time'] / stats['count']
        
        if execution_time > self.slow_query_threshold:
            stats['slow_queries'] += 1
            logger.warning(f"Slow query detected: {query_name} took {execution_time:.3f}s")

    def get_query_stats(self) -> Dict[str, Dict]:
        """Query istatistiklerini al"""
        return self.query_stats

    def reset_query_stats(self):
        """Query istatistiklerini sıfırla"""
        self.query_stats = {}


class CacheManager:
    """Intelligent caching system"""
    
    def __init__(self):
        self.default_timeout = 3600  # 1 hour
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }

    def get_or_set(self, key: str, callable_func: Callable, timeout: int = None) -> Any:
        """Get from cache or set with callable"""
        if timeout is None:
            timeout = self.default_timeout
        
        # Try to get from cache
        result = cache.get(key)
        if result is not None:
            self.cache_stats['hits'] += 1
            return result
        
        # Cache miss - compute and set
        self.cache_stats['misses'] += 1
        result = callable_func()
        self.set(key, result, timeout)
        
        return result

    def set(self, key: str, value: Any, timeout: int = None):
        """Set cache with stats tracking"""
        if timeout is None:
            timeout = self.default_timeout
        
        cache.set(key, value, timeout)
        self.cache_stats['sets'] += 1

    def delete(self, key: str):
        """Delete from cache with stats tracking"""
        cache.delete(key)
        self.cache_stats['deletes'] += 1

    def delete_pattern(self, pattern: str):
        """Delete cache keys matching pattern"""
        # Note: This requires Redis backend for pattern support
        try:
            from django.core.cache.backends.redis import RedisCache
            if isinstance(cache._cache, RedisCache):
                keys = cache._cache.get_client().keys(pattern)
                if keys:
                    cache._cache.get_client().delete(*keys)
                    self.cache_stats['deletes'] += len(keys)
        except ImportError:
            # Fallback for non-Redis backends
            logger.warning("Pattern deletion not supported with current cache backend")

    def get_cache_stats(self) -> Dict[str, int]:
        """Cache istatistiklerini al"""
        total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
        hit_rate = (self.cache_stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            **self.cache_stats,
            'hit_rate': round(hit_rate, 2),
            'total_requests': total_requests
        }

    def clear_all_stats(self):
        """Tüm cache istatistiklerini temizle"""
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }


class PerformanceMonitor:
    """Performance monitoring and profiling"""
    
    def __init__(self):
        self.request_times = []
        self.db_query_times = []
        self.cache_operations = []

    def time_function(self, func_name: str = None):
        """Decorator for timing functions"""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                function_name = func_name or f"{func.__module__}.{func.__name__}"
                self.record_execution_time(function_name, execution_time)
                
                return result
            return wrapper
        return decorator

    def time_database_queries(self):
        """Context manager for timing database queries"""
        class DatabaseTimer:
            def __init__(self, monitor):
                self.monitor = monitor
                self.initial_queries = 0
                
            def __enter__(self):
                self.initial_queries = len(connection.queries)
                return self
                
            def __exit__(self, exc_type, exc_val, exc_tb):
                final_queries = len(connection.queries)
                new_queries = connection.queries[self.initial_queries:final_queries]
                
                total_time = sum(float(query['time']) for query in new_queries)
                self.monitor.record_db_query_time(total_time, len(new_queries))
        
        return DatabaseTimer(self)

    def record_execution_time(self, function_name: str, execution_time: float):
        """Function execution time kaydı"""
        record = {
            'function': function_name,
            'time': execution_time,
            'timestamp': timezone.now()
        }
        
        # Keep only last 1000 records
        if len(self.request_times) >= 1000:
            self.request_times.pop(0)
        
        self.request_times.append(record)
        
        # Log slow functions
        if execution_time > 1.0:  # 1 second threshold
            logger.warning(f"Slow function: {function_name} took {execution_time:.3f}s")

    def record_db_query_time(self, total_time: float, query_count: int):
        """Database query time kaydı"""
        record = {
            'total_time': total_time,
            'query_count': query_count,
            'timestamp': timezone.now()
        }
        
        # Keep only last 1000 records
        if len(self.db_query_times) >= 1000:
            self.db_query_times.pop(0)
        
        self.db_query_times.append(record)

    def get_performance_report(self) -> Dict[str, Any]:
        """Performans raporu oluştur"""
        if not self.request_times:
            return {'error': 'No performance data available'}
        
        # Function performance analysis
        function_stats = {}
        for record in self.request_times:
            func_name = record['function']
            if func_name not in function_stats:
                function_stats[func_name] = {
                    'total_time': 0,
                    'count': 0,
                    'max_time': 0,
                    'min_time': float('inf')
                }
            
            stats = function_stats[func_name]
            stats['total_time'] += record['time']
            stats['count'] += 1
            stats['max_time'] = max(stats['max_time'], record['time'])
            stats['min_time'] = min(stats['min_time'], record['time'])
            stats['avg_time'] = stats['total_time'] / stats['count']
        
        # Database query analysis
        db_stats = {
            'total_queries': sum(r['query_count'] for r in self.db_query_times),
            'total_db_time': sum(r['total_time'] for r in self.db_query_times),
            'avg_queries_per_request': 0,
            'avg_db_time_per_request': 0
        }
        
        if self.db_query_times:
            db_stats['avg_queries_per_request'] = db_stats['total_queries'] / len(self.db_query_times)
            db_stats['avg_db_time_per_request'] = db_stats['total_db_time'] / len(self.db_query_times)
        
        # Overall performance
        total_execution_time = sum(r['time'] for r in self.request_times)
        avg_execution_time = total_execution_time / len(self.request_times)
        
        return {
            'summary': {
                'total_requests': len(self.request_times),
                'avg_execution_time': round(avg_execution_time, 3),
                'total_execution_time': round(total_execution_time, 3)
            },
            'functions': {
                name: {
                    **stats,
                    'avg_time': round(stats['avg_time'], 3),
                    'total_time': round(stats['total_time'], 3)
                }
                for name, stats in sorted(
                    function_stats.items(),
                    key=lambda x: x[1]['total_time'],
                    reverse=True
                )[:10]  # Top 10 slowest functions
            },
            'database': db_stats
        }


class ImageOptimizer:
    """Image optimization and processing"""
    
    def __init__(self):
        self.max_width = 1920
        self.max_height = 1080
        self.quality = 85
        self.thumbnail_size = (300, 300)

    def optimize_image(self, image_file, max_size: tuple = None, quality: int = None):
        """Resim optimizasyonu"""
        try:
            from PIL import Image, ImageOps
            import io
            
            if max_size is None:
                max_size = (self.max_width, self.max_height)
            if quality is None:
                quality = self.quality
            
            # Open image
            image = Image.open(image_file)
            
            # Auto-rotate based on EXIF data
            image = ImageOps.exif_transpose(image)
            
            # Convert to RGB if necessary
            if image.mode in ('RGBA', 'P'):
                image = image.convert('RGB')
            
            # Resize if too large
            original_size = image.size
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Save optimized image
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=quality, optimize=True)
            output.seek(0)
            
            # Calculate compression ratio
            original_size_mb = image_file.size / (1024 * 1024)
            optimized_size_mb = len(output.getvalue()) / (1024 * 1024)
            compression_ratio = (1 - optimized_size_mb / original_size_mb) * 100
            
            logger.info(f"Image optimized: {compression_ratio:.1f}% compression")
            
            return output, {
                'original_size': original_size,
                'new_size': image.size,
                'compression_ratio': compression_ratio,
                'original_size_mb': original_size_mb,
                'optimized_size_mb': optimized_size_mb
            }
            
        except Exception as e:
            logger.error(f"Image optimization failed: {str(e)}")
            return image_file, {'error': str(e)}

    def create_thumbnail(self, image_file, size: tuple = None):
        """Thumbnail oluştur"""
        try:
            from PIL import Image, ImageOps
            import io
            
            if size is None:
                size = self.thumbnail_size
            
            image = Image.open(image_file)
            image = ImageOps.exif_transpose(image)
            
            # Create thumbnail
            image.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Convert to RGB if necessary
            if image.mode in ('RGBA', 'P'):
                image = image.convert('RGB')
            
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=self.quality)
            output.seek(0)
            
            return output
            
        except Exception as e:
            logger.error(f"Thumbnail creation failed: {str(e)}")
            return None


class PaginationOptimizer:
    """Optimized pagination for large datasets"""
    
    def __init__(self):
        self.default_per_page = 20
        self.max_per_page = 100

    def paginate_queryset(self, queryset: QuerySet, page: int, per_page: int = None) -> Dict[str, Any]:
        """Optimized pagination"""
        if per_page is None:
            per_page = self.default_per_page
        
        # Limit per_page to prevent abuse
        per_page = min(per_page, self.max_per_page)
        
        # Use database-level pagination
        paginator = Paginator(queryset, per_page)
        
        try:
            page_obj = paginator.page(page)
        except:
            page_obj = paginator.page(1)
        
        return {
            'items': list(page_obj.object_list),
            'pagination': {
                'page': page_obj.number,
                'per_page': per_page,
                'total_pages': paginator.num_pages,
                'total_items': paginator.count,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
                'next_page': page_obj.next_page_number() if page_obj.has_next() else None,
                'previous_page': page_obj.previous_page_number() if page_obj.has_previous() else None
            }
        }

    def cursor_paginate(self, queryset: QuerySet, cursor: str = None, per_page: int = None) -> Dict[str, Any]:
        """Cursor-based pagination for better performance on large datasets"""
        if per_page is None:
            per_page = self.default_per_page
        
        per_page = min(per_page, self.max_per_page)
        
        # Apply cursor filter
        if cursor:
            try:
                cursor_id = int(cursor)
                queryset = queryset.filter(id__lt=cursor_id)
            except (ValueError, TypeError):
                pass
        
        # Get items plus one extra to check if there's a next page
        items = list(queryset[:per_page + 1])
        
        has_next = len(items) > per_page
        if has_next:
            items = items[:per_page]
        
        next_cursor = str(items[-1].id) if items and has_next else None
        
        return {
            'items': items,
            'pagination': {
                'cursor': cursor,
                'per_page': per_page,
                'has_next': has_next,
                'next_cursor': next_cursor
            }
        }


# Global instances
query_optimizer = QueryOptimizer()
cache_manager = CacheManager()
performance_monitor = PerformanceMonitor()
image_optimizer = ImageOptimizer()
pagination_optimizer = PaginationOptimizer()


# Decorators for easy use
def cache_result(timeout: int = 3600, key_prefix: str = ''):
    """Cache function result decorator"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            key_parts = [key_prefix, func.__name__, str(hash(str(args) + str(kwargs)))]
            cache_key = ':'.join(filter(None, key_parts))
            
            return cache_manager.get_or_set(
                cache_key,
                lambda: func(*args, **kwargs),
                timeout
            )
        return wrapper
    return decorator


def monitor_performance(func_name: str = None):
    """Performance monitoring decorator"""
    return performance_monitor.time_function(func_name)


def optimize_queries(relations: List[str]):
    """Query optimization decorator"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # If result is a QuerySet, optimize it
            if isinstance(result, QuerySet):
                result = query_optimizer.optimize_queryset(result, relations)
            
            return result
        return wrapper
    return decorator
