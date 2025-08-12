"""
📊 Advanced Monitoring & Logging System
Real-time system monitoring, error tracking, and performance analytics
"""

import os
import json
import time
import platform
try:
    import psutil
except ImportError:
    psutil = None
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from django.db import connection
from django.core.management.color import no_style
import logging

logger = logging.getLogger(__name__)


class SystemMonitor:
    """System resource monitoring"""
    
    def __init__(self):
        self.start_time = time.time()
        self.last_check = time.time()

    def get_system_stats(self) -> Dict[str, Any]:
        """Detaylı sistem istatistikleri"""
        try:
            if psutil is None:
                return {
                    'error': 'psutil not available',
                    'message': 'Install psutil for system monitoring: pip install psutil'
                }
            
            # CPU Information
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # Memory Information
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Disk Information
            disk = psutil.disk_usage('/')
            
            # Network Information
            network = psutil.net_io_counters()
            
            # Process Information
            process = psutil.Process()
            process_memory = process.memory_info()
            
            return {
                'timestamp': timezone.now().isoformat(),
                'uptime': time.time() - self.start_time,
                'system': {
                    'platform': platform.platform(),
                    'python_version': platform.python_version(),
                    'architecture': platform.architecture()[0]
                },
                'cpu': {
                    'percent': cpu_percent,
                    'count': cpu_count,
                    'frequency': cpu_freq.current if cpu_freq else None
                },
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent,
                    'used': memory.used,
                    'free': memory.free
                },
                'swap': {
                    'total': swap.total,
                    'used': swap.used,
                    'percent': swap.percent
                },
                'disk': {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': (disk.used / disk.total) * 100
                },
                'network': {
                    'bytes_sent': network.bytes_sent,
                    'bytes_recv': network.bytes_recv,
                    'packets_sent': network.packets_sent,
                    'packets_recv': network.packets_recv
                },
                'process': {
                    'memory_rss': process_memory.rss,
                    'memory_vms': process_memory.vms,
                    'cpu_percent': process.cpu_percent(),
                    'num_threads': process.num_threads()
                }
            }
        except Exception as e:
            logger.error(f"System monitoring error: {str(e)}")
            return {'error': str(e)}

    def get_database_stats(self) -> Dict[str, Any]:
        """Database istatistikleri"""
        try:
            cursor = connection.cursor()
            
            # Query count and timing
            query_count = len(connection.queries)
            total_time = sum(float(q['time']) for q in connection.queries)
            
            # Database size (SQLite specific)
            db_size = 0
            if settings.DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':
                db_path = settings.DATABASES['default']['NAME']
                if os.path.exists(db_path):
                    db_size = os.path.getsize(db_path)
            
            # Connection info
            connection_info = {
                'vendor': connection.vendor,
                'version': None,
                'encoding': getattr(connection, 'encoding', None)
            }
            
            try:
                if connection.vendor == 'sqlite':
                    cursor.execute("SELECT sqlite_version()")
                    connection_info['version'] = cursor.fetchone()[0]
            except:
                pass
            
            return {
                'query_count': query_count,
                'total_query_time': total_time,
                'avg_query_time': total_time / query_count if query_count > 0 else 0,
                'database_size': db_size,
                'connection': connection_info
            }
            
        except Exception as e:
            logger.error(f"Database monitoring error: {str(e)}")
            return {'error': str(e)}

    def get_django_stats(self) -> Dict[str, Any]:
        """Django aplikasyon istatistikleri"""
        try:
            from django.apps import apps
            
            # Model counts
            model_counts = {}
            for model in apps.get_models():
                try:
                    count = model.objects.count()
                    model_counts[f"{model._meta.app_label}.{model._meta.model_name}"] = count
                except:
                    pass
            
            # Cache stats
            cache_stats = {}
            try:
                # Try to get cache stats (Redis specific)
                if hasattr(cache, '_cache') and hasattr(cache._cache, 'get_stats'):
                    cache_stats = cache._cache.get_stats()
            except:
                pass
            
            # Settings info
            settings_info = {
                'debug': settings.DEBUG,
                'time_zone': settings.TIME_ZONE,
                'language_code': settings.LANGUAGE_CODE,
                'installed_apps_count': len(settings.INSTALLED_APPS),
                'middleware_count': len(settings.MIDDLEWARE)
            }
            
            return {
                'model_counts': model_counts,
                'cache_stats': cache_stats,
                'settings': settings_info
            }
            
        except Exception as e:
            logger.error(f"Django monitoring error: {str(e)}")
            return {'error': str(e)}

    def store_metrics(self, metrics: Dict[str, Any]):
        """Metrikleri cache'de sakla"""
        timestamp = int(time.time())
        cache_key = f"system_metrics:{timestamp}"
        
        # Store current metrics
        cache.set(cache_key, metrics, 3600)  # 1 hour
        
        # Maintain metrics history
        history_key = "system_metrics_history"
        history = cache.get(history_key, [])
        history.append(timestamp)
        
        # Keep only last 24 hours of metrics
        cutoff = timestamp - 86400
        history = [ts for ts in history if ts > cutoff]
        
        cache.set(history_key, history, 86400)

    def get_metrics_history(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Metrik geçmişini al"""
        history_key = "system_metrics_history"
        timestamps = cache.get(history_key, [])
        
        # Filter by time range
        cutoff = int(time.time()) - (hours * 3600)
        relevant_timestamps = [ts for ts in timestamps if ts > cutoff]
        
        metrics_history = []
        for timestamp in relevant_timestamps[-100:]:  # Last 100 records
            cache_key = f"system_metrics:{timestamp}"
            metrics = cache.get(cache_key)
            if metrics:
                metrics_history.append(metrics)
        
        return metrics_history


class ErrorTracker:
    """Error tracking and analysis"""
    
    def __init__(self):
        self.error_counts = {}
        self.recent_errors = []

    def track_error(self, error_type: str, error_message: str, context: Dict[str, Any] = None):
        """Hata takibi"""
        error_info = {
            'type': error_type,
            'message': error_message,
            'context': context or {},
            'timestamp': timezone.now().isoformat(),
            'count': 1
        }
        
        # Update error counts
        error_key = f"{error_type}:{error_message}"
        if error_key in self.error_counts:
            self.error_counts[error_key]['count'] += 1
            self.error_counts[error_key]['last_seen'] = error_info['timestamp']
        else:
            self.error_counts[error_key] = {
                'type': error_type,
                'message': error_message,
                'count': 1,
                'first_seen': error_info['timestamp'],
                'last_seen': error_info['timestamp']
            }
        
        # Add to recent errors
        self.recent_errors.append(error_info)
        
        # Keep only last 100 errors
        if len(self.recent_errors) > 100:
            self.recent_errors.pop(0)
        
        # Store in cache
        cache.set('error_tracker_counts', self.error_counts, 86400)
        cache.set('error_tracker_recent', self.recent_errors, 3600)
        
        logger.error(f"Error tracked: {error_type} - {error_message}", extra=context)

    def get_error_summary(self) -> Dict[str, Any]:
        """Hata özeti"""
        # Load from cache
        self.error_counts = cache.get('error_tracker_counts', {})
        self.recent_errors = cache.get('error_tracker_recent', [])
        
        # Calculate error statistics
        total_errors = sum(error['count'] for error in self.error_counts.values())
        unique_errors = len(self.error_counts)
        
        # Most frequent errors
        frequent_errors = sorted(
            self.error_counts.values(),
            key=lambda x: x['count'],
            reverse=True
        )[:10]
        
        # Recent error trends
        now = timezone.now()
        last_hour_errors = [
            error for error in self.recent_errors
            if (now - datetime.fromisoformat(error['timestamp'].replace('Z', '+00:00'))).total_seconds() < 3600
        ]
        
        return {
            'total_errors': total_errors,
            'unique_errors': unique_errors,
            'errors_last_hour': len(last_hour_errors),
            'most_frequent': frequent_errors,
            'recent_errors': self.recent_errors[-10:]  # Last 10 errors
        }


class PerformanceAnalyzer:
    """Performance analysis and recommendations"""
    
    def __init__(self):
        self.performance_data = []

    def analyze_request_performance(self, request_data: Dict[str, Any]):
        """Request performans analizi"""
        self.performance_data.append(request_data)
        
        # Keep only last 1000 requests
        if len(self.performance_data) > 1000:
            self.performance_data.pop(0)
        
        # Store in cache
        cache.set('performance_data', self.performance_data, 3600)

    def get_performance_insights(self) -> Dict[str, Any]:
        """Performans öngörüleri"""
        # Load from cache
        self.performance_data = cache.get('performance_data', [])
        
        if not self.performance_data:
            return {'message': 'No performance data available'}
        
        # Calculate metrics
        response_times = [req.get('response_time', 0) for req in self.performance_data]
        db_query_times = [req.get('db_time', 0) for req in self.performance_data]
        query_counts = [req.get('query_count', 0) for req in self.performance_data]
        
        avg_response_time = sum(response_times) / len(response_times)
        avg_db_time = sum(db_query_times) / len(db_query_times)
        avg_query_count = sum(query_counts) / len(query_counts)
        
        # Identify slow requests
        slow_threshold = 1.0  # 1 second
        slow_requests = [req for req in self.performance_data if req.get('response_time', 0) > slow_threshold]
        
        # Generate recommendations
        recommendations = []
        
        if avg_response_time > 0.5:
            recommendations.append("Response times are high. Consider caching frequently accessed data.")
        
        if avg_db_time > 0.2:
            recommendations.append("Database queries are slow. Consider query optimization and indexing.")
        
        if avg_query_count > 10:
            recommendations.append("Too many database queries per request. Consider using select_related and prefetch_related.")
        
        if len(slow_requests) > len(self.performance_data) * 0.1:
            recommendations.append("More than 10% of requests are slow. Review bottlenecks.")
        
        return {
            'metrics': {
                'avg_response_time': round(avg_response_time, 3),
                'avg_db_time': round(avg_db_time, 3),
                'avg_query_count': round(avg_query_count, 1),
                'slow_requests_count': len(slow_requests),
                'total_requests': len(self.performance_data)
            },
            'recommendations': recommendations,
            'slowest_requests': sorted(
                self.performance_data,
                key=lambda x: x.get('response_time', 0),
                reverse=True
            )[:5]
        }


class HealthChecker:
    """System health checker"""
    
    def __init__(self):
        self.health_checks = {
            'database': self._check_database,
            'cache': self._check_cache,
            'disk_space': self._check_disk_space,
            'memory': self._check_memory,
            'dependencies': self._check_dependencies
        }

    def run_health_checks(self) -> Dict[str, Any]:
        """Tüm health check'leri çalıştır"""
        results = {}
        overall_status = 'healthy'
        
        for check_name, check_func in self.health_checks.items():
            try:
                result = check_func()
                results[check_name] = result
                
                if result['status'] == 'critical':
                    overall_status = 'critical'
                elif result['status'] == 'warning' and overall_status == 'healthy':
                    overall_status = 'warning'
                    
            except Exception as e:
                results[check_name] = {
                    'status': 'critical',
                    'message': f"Health check failed: {str(e)}"
                }
                overall_status = 'critical'
        
        return {
            'overall_status': overall_status,
            'timestamp': timezone.now().isoformat(),
            'checks': results
        }

    def _check_database(self) -> Dict[str, Any]:
        """Database bağlantısını kontrol et"""
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            
            return {
                'status': 'healthy',
                'message': 'Database connection is working'
            }
        except Exception as e:
            return {
                'status': 'critical',
                'message': f"Database connection failed: {str(e)}"
            }

    def _check_cache(self) -> Dict[str, Any]:
        """Cache sistemini kontrol et"""
        try:
            test_key = 'health_check_test'
            test_value = 'test_value'
            
            cache.set(test_key, test_value, 30)
            retrieved_value = cache.get(test_key)
            
            if retrieved_value == test_value:
                cache.delete(test_key)
                return {
                    'status': 'healthy',
                    'message': 'Cache is working properly'
                }
            else:
                return {
                    'status': 'warning',
                    'message': 'Cache set/get mismatch'
                }
        except Exception as e:
            return {
                'status': 'critical',
                'message': f"Cache system failed: {str(e)}"
            }

    def _check_disk_space(self) -> Dict[str, Any]:
        """Disk alanını kontrol et"""
        try:
            disk = psutil.disk_usage('/')
            usage_percent = (disk.used / disk.total) * 100
            
            if usage_percent > 90:
                status = 'critical'
                message = f"Disk usage is critical: {usage_percent:.1f}%"
            elif usage_percent > 80:
                status = 'warning'
                message = f"Disk usage is high: {usage_percent:.1f}%"
            else:
                status = 'healthy'
                message = f"Disk usage is normal: {usage_percent:.1f}%"
            
            return {
                'status': status,
                'message': message,
                'usage_percent': usage_percent
            }
        except Exception as e:
            return {
                'status': 'critical',
                'message': f"Disk check failed: {str(e)}"
            }

    def _check_memory(self) -> Dict[str, Any]:
        """Memory kullanımını kontrol et"""
        try:
            memory = psutil.virtual_memory()
            usage_percent = memory.percent
            
            if usage_percent > 90:
                status = 'critical'
                message = f"Memory usage is critical: {usage_percent:.1f}%"
            elif usage_percent > 80:
                status = 'warning'
                message = f"Memory usage is high: {usage_percent:.1f}%"
            else:
                status = 'healthy'
                message = f"Memory usage is normal: {usage_percent:.1f}%"
            
            return {
                'status': status,
                'message': message,
                'usage_percent': usage_percent
            }
        except Exception as e:
            return {
                'status': 'critical',
                'message': f"Memory check failed: {str(e)}"
            }

    def _check_dependencies(self) -> Dict[str, Any]:
        """Critical dependencies kontrol et"""
        try:
            import django
            import PIL
            
            missing_deps = []
            
            # Check optional dependencies
            try:
                import psutil
            except ImportError:
                missing_deps.append('psutil')
            
            if missing_deps:
                return {
                    'status': 'warning',
                    'message': f"Optional dependencies missing: {', '.join(missing_deps)}"
                }
            else:
                return {
                    'status': 'healthy',
                    'message': 'All dependencies are available'
                }
        except Exception as e:
            return {
                'status': 'critical',
                'message': f"Dependency check failed: {str(e)}"
            }


# Global instances
system_monitor = SystemMonitor()
error_tracker = ErrorTracker()
performance_analyzer = PerformanceAnalyzer()
health_checker = HealthChecker()
