"""
Cache Manager for Admin Dashboard
Comprehensive caching implementation using Django's cache framework
"""

from django.core.cache import cache
from django.conf import settings
from django.db.models import Count, Q
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta
from django.utils import timezone
import logging
import hashlib
import json

logger = logging.getLogger(__name__)

User = get_user_model()

class AdminDashboardCacheManager:
    """
    Centralized cache manager for admin dashboard performance optimization
    """
    
    # Cache timeouts (in seconds)
    CACHE_TIMEOUTS = {
        'DASHBOARD_STATS': 300,  # 5 minutes
        'USER_STATS': 180,  # 3 minutes
        'AUDIT_LOGS': 120,  # 2 minutes
        'SYSTEM_SETTINGS': 600,  # 10 minutes
        'SESSION_DATA': 60,  # 1 minute
        'REPORTS': 900,  # 15 minutes
        'SECURITY_STATS': 300,  # 5 minutes
        'ACTIVITY_STATS': 180,  # 3 minutes
    }
    
    # Cache key prefixes
    CACHE_PREFIXES = {
        'DASHBOARD': 'admin_dashboard',
        'USER': 'user_stats',
        'AUDIT': 'audit_logs',
        'SETTINGS': 'system_settings',
        'SESSION': 'session_data',
        'REPORTS': 'reports',
        'SECURITY': 'security_stats',
        'ACTIVITY': 'activity_stats',
    }
    
    @classmethod
    def get_cache_key(cls, prefix, identifier, **kwargs):
        """
        Generate consistent cache keys
        
        Args:
            prefix: Cache prefix from CACHE_PREFIXES
            identifier: Unique identifier for the cache entry
            **kwargs: Additional parameters for cache key generation
            
        Returns:
            Formatted cache key string
        """
        key_parts = [cls.CACHE_PREFIXES.get(prefix, prefix), str(identifier)]
        
        # Add additional parameters to make key unique
        for key, value in sorted(kwargs.items()):
            if value is not None:
                key_parts.append(f"{key}_{value}")
        
        # Create hash for long keys to keep them manageable
        cache_key = "_".join(key_parts)
        if len(cache_key) > 100:
            cache_key = hashlib.md5(cache_key.encode()).hexdigest()
        
        return cache_key
    
    @classmethod
    def get_dashboard_stats(cls, force_refresh=False):
        """
        Get cached dashboard statistics
        
        Args:
            force_refresh: Force refresh of cached data
            
        Returns:
            Dictionary of dashboard statistics
        """
        cache_key = cls.get_cache_key('DASHBOARD', 'stats')
        
        if not force_refresh:
            cached_stats = cache.get(cache_key)
            if cached_stats is not None:
                logger.debug(f"Cache hit for dashboard stats: {cache_key}")
                return cached_stats
        
        # Calculate fresh statistics
        logger.debug("Calculating fresh dashboard statistics")
        stats = cls._calculate_dashboard_stats()
        
        # Cache the results
        cache.set(cache_key, stats, cls.CACHE_TIMEOUTS['DASHBOARD_STATS'])
        logger.debug(f"Cached dashboard stats: {cache_key}")
        
        return stats
    
    @classmethod
    def _calculate_dashboard_stats(cls):
        """Calculate dashboard statistics"""
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)
        
        stats = {
            'total_users': User.objects.count(),
            'total_members': User.objects.filter(role='member').count(),
            'total_librarians': User.objects.filter(role='librarian').count(),
            'total_managers': User.objects.filter(role='manager').count(),
            'recent_users': User.objects.filter(created_at__gte=thirty_days_ago).count(),
            'locked_accounts': User.objects.filter(account_locked_until__isnull=False).count(),
            'active_accounts': User.objects.filter(is_active=True).count(),
        }
        
        # Add audit log statistics
        try:
            from .models import AuditLog
            stats['recent_audit_logs'] = AuditLog.objects.filter(
                timestamp__gte=thirty_days_ago
            ).count()
        except Exception as e:
            logger.warning(f"Failed to calculate audit log stats: {e}")
            stats['recent_audit_logs'] = 0
        
        return stats
    
    @classmethod
    def get_user_stats(cls, search_query='', role_filter='', status_filter='', force_refresh=False):
        """
        Get cached user statistics with filters
        
        Args:
            search_query: Search query for filtering
            role_filter: Role filter
            status_filter: Status filter
            force_refresh: Force refresh of cached data
            
        Returns:
            Dictionary of user statistics
        """
        cache_key = cls.get_cache_key('USER', 'stats', 
                                    search=search_query, 
                                    role=role_filter, 
                                    status=status_filter)
        
        if not force_refresh:
            cached_stats = cache.get(cache_key)
            if cached_stats is not None:
                logger.debug(f"Cache hit for user stats: {cache_key}")
                return cached_stats
        
        # Calculate fresh user statistics
        logger.debug("Calculating fresh user statistics")
        stats = cls._calculate_user_stats()
        
        # Cache the results
        cache.set(cache_key, stats, cls.CACHE_TIMEOUTS['USER_STATS'])
        logger.debug(f"Cached user stats: {cache_key}")
        
        return stats
    
    @classmethod
    def _calculate_user_stats(cls):
        """Calculate user statistics"""
        return {
            'total': User.objects.count(),
            'active': User.objects.filter(is_active=True).count(),
            'locked': User.objects.filter(account_locked_until__isnull=False).count(),
            'members': User.objects.filter(role='member').count(),
            'librarians': User.objects.filter(role='librarian').count(),
            'managers': User.objects.filter(role='manager').count(),
            'admins': User.objects.filter(role='admin').count(),
        }
    
    @classmethod
    def get_audit_logs(cls, action_filter='', user_filter='', date_from='', date_to='', 
                      security_filter='', page=1, force_refresh=False):
        """
        Get cached audit logs with filters
        
        Args:
            action_filter: Action type filter
            user_filter: User filter
            date_from: Start date filter
            date_to: End date filter
            security_filter: Security event filter
            page: Page number for pagination
            force_refresh: Force refresh of cached data
            
        Returns:
            Dictionary containing audit logs and metadata
        """
        cache_key = cls.get_cache_key('AUDIT', 'logs',
                                    action=action_filter,
                                    user=user_filter,
                                    date_from=date_from,
                                    date_to=date_to,
                                    security=security_filter,
                                    page=page)
        
        if not force_refresh:
            cached_logs = cache.get(cache_key)
            if cached_logs is not None:
                logger.debug(f"Cache hit for audit logs: {cache_key}")
                return cached_logs
        
        # Calculate fresh audit logs
        logger.debug("Calculating fresh audit logs")
        logs_data = cls._calculate_audit_logs(action_filter, user_filter, date_from, 
                                            date_to, security_filter, page)
        
        # Cache the results
        cache.set(cache_key, logs_data, cls.CACHE_TIMEOUTS['AUDIT_LOGS'])
        logger.debug(f"Cached audit logs: {cache_key}")
        
        return logs_data
    
    @classmethod
    def _calculate_audit_logs(cls, action_filter, user_filter, date_from, date_to, 
                             security_filter, page):
        """Calculate audit logs with filters"""
        try:
            from .models import AuditLog
            
            logs = AuditLog.objects.all().select_related('user')
            
            # Apply filters
            if action_filter:
                logs = logs.filter(action=action_filter)
            
            if user_filter:
                logs = logs.filter(
                    Q(user__username__icontains=user_filter) |
                    Q(user__first_name__icontains=user_filter) |
                    Q(user__last_name__icontains=user_filter)
                )
            
            if date_from:
                try:
                    from_date = datetime.strptime(date_from, '%Y-%m-%d')
                    from_date = timezone.make_aware(from_date)
                    logs = logs.filter(timestamp__gte=from_date)
                except ValueError:
                    pass
            
            if date_to:
                try:
                    to_date = datetime.strptime(date_to, '%Y-%m-%d')
                    to_date = timezone.make_aware(to_date)
                    logs = logs.filter(timestamp__lte=to_date)
                except ValueError:
                    pass
            
            if security_filter == 'security_events':
                security_actions = [
                    'LOGIN_FAILED', 'MULTIPLE_LOGIN_FAILURES', 'ACCOUNT_LOCKED',
                    'SUSPICIOUS_ACTIVITY', 'SESSION_TIMEOUT', 'FORCE_LOGOUT'
                ]
                logs = logs.filter(action__in=security_actions)
            
            # Pagination
            from django.core.paginator import Paginator
            paginator = Paginator(logs, 50)
            page_obj = paginator.get_page(page)
            
            return {
                'logs': list(page_obj),
                'page_obj': page_obj,
                'total_count': logs.count(),
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate audit logs: {e}")
            return {'logs': [], 'page_obj': None, 'total_count': 0}
    
    @classmethod
    def get_system_settings(cls, force_refresh=False):
        """
        Get cached system settings
        
        Args:
            force_refresh: Force refresh of cached data
            
        Returns:
            Dictionary of system settings by category
        """
        cache_key = cls.get_cache_key('SETTINGS', 'categories')
        
        if not force_refresh:
            cached_settings = cache.get(cache_key)
            if cached_settings is not None:
                logger.debug(f"Cache hit for system settings: {cache_key}")
                return cached_settings
        
        # Calculate fresh system settings
        logger.debug("Calculating fresh system settings")
        settings = cls._calculate_system_settings()
        
        # Cache the results
        cache.set(cache_key, settings, cls.CACHE_TIMEOUTS['SYSTEM_SETTINGS'])
        logger.debug(f"Cached system settings: {cache_key}")
        
        return settings
    
    @classmethod
    def _calculate_system_settings(cls):
        """Calculate system settings by category"""
        try:
            from .models import SystemSetting
            
            settings = SystemSetting.objects.all().order_by('key')
            existing_settings = {setting.key: setting for setting in settings}
            
            # Define setting categories (same structure as original)
            setting_categories = {
                'borrowing': {
                    'name': 'Borrowing & Loans',
                    'icon': 'fas fa-book',
                    'description': 'Settings that control book borrowing behavior',
                    'settings': [
                        {
                            'key': 'max_books_per_user',
                            'name': 'Max Books Per User',
                            'default': '5',
                            'type': 'number',
                            'description': 'Maximum number of books a user can borrow simultaneously',
                            'min': 1,
                            'max': 50
                        },
                        {
                            'key': 'max_borrowing_days',
                            'name': 'Default Loan Period',
                            'default': '14',
                            'type': 'number',
                            'description': 'Default number of days for book loans',
                            'min': 1,
                            'max': 365,
                            'unit': 'days'
                        },
                    ]
                },
                'fines': {
                    'name': 'Fines & Penalties',
                    'icon': 'fas fa-dollar-sign',
                    'description': 'Configure fine calculation rules and rates',
                    'settings': [
                        {
                            'key': 'fine_tier_1_rate',
                            'name': 'Tier 1 Rate',
                            'default': '2.00',
                            'type': 'decimal',
                            'description': 'Fine amount per day for tier 1 (early overdue)',
                            'min': 0.01,
                            'unit': 'MVR/day'
                        },
                    ]
                },
                'sessions': {
                    'name': 'Session Management',
                    'icon': 'fas fa-clock',
                    'description': 'Control user session timeouts by role',
                    'settings': [
                        {
                            'key': 'member_session_timeout_minutes',
                            'name': 'Member Session Timeout',
                            'default': '15',
                            'type': 'number',
                            'description': 'Session timeout for regular library members',
                            'min': 5,
                            'max': 480,
                            'unit': 'minutes'
                        },
                    ]
                },
            }
            
            # Add current values to setting definitions
            for category_key, category in setting_categories.items():
                for setting_def in category['settings']:
                    if setting_def['key'] in existing_settings:
                        setting_def['current_value'] = existing_settings[setting_def['key']].value
                        setting_def['is_configured'] = True
                        setting_def['setting_object'] = existing_settings[setting_def['key']]
                    else:
                        setting_def['current_value'] = setting_def['default']
                        setting_def['is_configured'] = False
                        setting_def['setting_object'] = None
            
            return setting_categories
            
        except Exception as e:
            logger.error(f"Failed to calculate system settings: {e}")
            return {}
    
    @classmethod
    def get_security_stats(cls, force_refresh=False):
        """
        Get cached security statistics
        
        Args:
            force_refresh: Force refresh of cached data
            
        Returns:
            Dictionary of security statistics
        """
        cache_key = cls.get_cache_key('SECURITY', 'stats')
        
        if not force_refresh:
            cached_stats = cache.get(cache_key)
            if cached_stats is not None:
                logger.debug(f"Cache hit for security stats: {cache_key}")
                return cached_stats
        
        # Calculate fresh security statistics
        logger.debug("Calculating fresh security statistics")
        stats = cls._calculate_security_stats()
        
        # Cache the results
        cache.set(cache_key, stats, cls.CACHE_TIMEOUTS['SECURITY_STATS'])
        logger.debug(f"Cached security stats: {cache_key}")
        
        return stats
    
    @classmethod
    def _calculate_security_stats(cls):
        """Calculate security statistics"""
        try:
            from .models import AuditLog
            
            now = timezone.now()
            today = now.date()
            week_ago = today - timedelta(days=7)
            
            stats = {
                'failed_logins_today': AuditLog.objects.filter(
                    action='LOGIN_FAILED',
                    timestamp__date=today
                ).count(),
                'locked_accounts_today': AuditLog.objects.filter(
                    action='ACCOUNT_LOCKED',
                    timestamp__date=today
                ).count(),
                'failed_logins_week': AuditLog.objects.filter(
                    action='LOGIN_FAILED',
                    timestamp__date__gte=week_ago
                ).count(),
                'suspicious_activities_week': AuditLog.objects.filter(
                    action__in=['SUSPICIOUS_ACTIVITY', 'MULTIPLE_LOGIN_FAILURES'],
                    timestamp__date__gte=week_ago
                ).count(),
            }
            
            # Get top failed login IPs
            failed_login_ips = AuditLog.objects.filter(
                action='LOGIN_FAILED',
                timestamp__date__gte=week_ago,
                ip_address__isnull=False
            ).values('ip_address').annotate(
                count=Count('ip_address')
            ).order_by('-count')[:10]
            
            stats['failed_login_ips'] = list(failed_login_ips)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to calculate security stats: {e}")
            return {
                'failed_logins_today': 0,
                'locked_accounts_today': 0,
                'failed_logins_week': 0,
                'suspicious_activities_week': 0,
                'failed_login_ips': [],
            }
    
    @classmethod
    def invalidate_cache(cls, cache_type=None, **kwargs):
        """
        Invalidate specific cache entries or all caches
        
        Args:
            cache_type: Type of cache to invalidate (DASHBOARD, USER, AUDIT, etc.)
            **kwargs: Additional parameters for specific cache invalidation
        """
        if cache_type is None:
            # Invalidate all admin dashboard caches
            cls._invalidate_all_caches()
        else:
            # Invalidate specific cache type
            cls._invalidate_cache_type(cache_type, **kwargs)
    
    @classmethod
    def _invalidate_all_caches(cls):
        """Invalidate all admin dashboard caches"""
        try:
            # Clear all cache keys with admin dashboard prefixes
            for prefix in cls.CACHE_PREFIXES.values():
                # This is a simplified approach - in production you might want
                # a more sophisticated cache invalidation strategy
                cache.delete_pattern(f"{prefix}_*")
            
            logger.info("Invalidated all admin dashboard caches")
        except Exception as e:
            logger.error(f"Failed to invalidate all caches: {e}")
    
    @classmethod
    def _invalidate_cache_type(cls, cache_type, **kwargs):
        """Invalidate specific cache type"""
        try:
            if cache_type == 'DASHBOARD':
                cache.delete(cls.get_cache_key('DASHBOARD', 'stats'))
            elif cache_type == 'USER':
                # Invalidate user stats with specific filters
                cache_key = cls.get_cache_key('USER', 'stats', **kwargs)
                cache.delete(cache_key)
            elif cache_type == 'AUDIT':
                # Invalidate audit logs with specific filters
                cache_key = cls.get_cache_key('AUDIT', 'logs', **kwargs)
                cache.delete(cache_key)
            elif cache_type == 'SETTINGS':
                cache.delete(cls.get_cache_key('SETTINGS', 'categories'))
            elif cache_type == 'SECURITY':
                cache.delete(cls.get_cache_key('SECURITY', 'stats'))
            
            logger.info(f"Invalidated {cache_type} cache")
        except Exception as e:
            logger.error(f"Failed to invalidate {cache_type} cache: {e}")
    
    @classmethod
    def get_cache_info(cls):
        """
        Get information about cache usage and performance
        
        Returns:
            Dictionary with cache statistics
        """
        cache_info = {
            'cache_backend': getattr(settings, 'CACHES', {}).get('default', {}).get('BACKEND', 'Unknown'),
            'cache_timeouts': cls.CACHE_TIMEOUTS,
            'cache_prefixes': cls.CACHE_PREFIXES,
        }
        
        # Try to get cache statistics if available
        try:
            if hasattr(cache, 'get_stats'):
                cache_info['cache_stats'] = cache.get_stats()
        except Exception:
            pass
        
        return cache_info


# Cache decorators for easy use
def cached_dashboard_stats(timeout=None):
    """
    Decorator to cache dashboard statistics
    
    Usage:
        @cached_dashboard_stats(timeout=300)
        def get_dashboard_data():
            return calculate_stats()
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            cache_key = f"dashboard_stats_{func.__name__}"
            cached_result = cache.get(cache_key)
            
            if cached_result is not None:
                return cached_result
            
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout or AdminDashboardCacheManager.CACHE_TIMEOUTS['DASHBOARD_STATS'])
            return result
        return wrapper
    return decorator


def cached_user_stats(timeout=None):
    """
    Decorator to cache user statistics
    
    Usage:
        @cached_user_stats(timeout=180)
        def get_user_data():
            return calculate_user_stats()
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Create cache key based on function arguments
            cache_key = f"user_stats_{func.__name__}_{hash(str(args) + str(sorted(kwargs.items())))}"
            cached_result = cache.get(cache_key)
            
            if cached_result is not None:
                return cached_result
            
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout or AdminDashboardCacheManager.CACHE_TIMEOUTS['USER_STATS'])
            return result
        return wrapper
    return decorator 