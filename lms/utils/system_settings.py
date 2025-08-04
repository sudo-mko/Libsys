"""
System Settings Helper Utility

This utility provides safe access to system settings with fallbacks to prevent
breaking existing functionality.
"""
from decimal import Decimal
from django.core.cache import cache
from typing import Union, Any, Optional
import logging

logger = logging.getLogger(__name__)


class SystemSettingsHelper:
    """
    Helper class for accessing system settings with safe fallbacks.
    
    This class ensures that if system settings are not configured or fail to load,
    the application falls back to sensible defaults without breaking.
    """
    
    # Cache timeout for settings (5 minutes)
    CACHE_TIMEOUT = 300
    CACHE_PREFIX = 'system_setting_'
    
    @classmethod
    def get_setting(cls, key: str, default: Any = None, setting_type: str = 'text') -> Any:
        """
        Get a system setting value with type conversion and caching.
        
        Args:
            key: The setting key to retrieve
            default: Default value if setting doesn't exist
            setting_type: Type of setting ('text', 'number', 'boolean', 'json', 'decimal')
            
        Returns:
            The setting value converted to the appropriate type, or default if not found
        """
        cache_key = f"{cls.CACHE_PREFIX}{key}"
        
        # Try to get from cache first
        cached_value = cache.get(cache_key)
        if cached_value is not None:
            return cls._convert_value(cached_value, setting_type, default)
        
        try:
            # Import here to avoid circular imports
            from admin_dashboard.models import SystemSetting
            
            setting = SystemSetting.objects.get(key=key)
            value = setting.value
            
            # Cache the raw value
            cache.set(cache_key, value, cls.CACHE_TIMEOUT)
            
            return cls._convert_value(value, setting_type, default)
            
        except Exception as e:
            logger.warning(f"Failed to get system setting '{key}': {e}")
            return default
    
    @classmethod
    def _convert_value(cls, value: str, setting_type: str, default: Any) -> Any:
        """
        Convert string value to appropriate type.
        
        Args:
            value: String value from database
            setting_type: Target type
            default: Default value to return on conversion error
            
        Returns:
            Converted value or default if conversion fails
        """
        try:
            if setting_type == 'number':
                return int(value) if value.isdigit() else int(float(value))
            elif setting_type == 'decimal':
                return Decimal(str(value))
            elif setting_type == 'boolean':
                return str(value).lower() in ['true', '1', 'yes', 'on']
            elif setting_type == 'json':
                import json
                return json.loads(value)
            else:  # text
                return str(value)
        except (ValueError, TypeError, Exception) as e:
            logger.warning(f"Failed to convert setting value '{value}' to {setting_type}: {e}")
            return default
    
    @classmethod
    def invalidate_cache(cls, key: Optional[str] = None):
        """
        Invalidate cached settings.
        
        Args:
            key: Specific key to invalidate, or None to clear all setting caches
        """
        if key:
            cache_key = f"{cls.CACHE_PREFIX}{key}"
            cache.delete(cache_key)
        else:
            # Clear all setting caches - this is a simple approach
            # In production, you might want a more sophisticated cache invalidation
            try:
                from admin_dashboard.models import SystemSetting
                for setting in SystemSetting.objects.all():
                    cache_key = f"{cls.CACHE_PREFIX}{setting.key}"
                    cache.delete(cache_key)
            except Exception:
                pass
    
    # Convenience methods for common settings with built-in defaults
    
    @classmethod
    def get_max_books_per_user(cls, membership_default: int = 5) -> int:
        """Get maximum books per user setting with membership fallback."""
        return cls.get_setting('max_books_per_user', membership_default, 'number')
    
    @classmethod
    def get_max_borrowing_days(cls, membership_default: int = 14) -> int:
        """Get maximum borrowing days with membership fallback."""
        return cls.get_setting('max_borrowing_days', membership_default, 'number')
    
    @classmethod
    def get_fine_per_day(cls, default: Decimal = Decimal('2.00')) -> Decimal:
        """Get fine per day amount."""
        return cls.get_setting('fine_per_day', default, 'decimal')
    
    @classmethod
    def get_reservation_timeout_hours(cls, default: int = 24) -> int:
        """Get reservation timeout in hours."""
        return cls.get_setting('reservation_timeout_hours', default, 'number')
    
    @classmethod
    def get_session_timeout_minutes(cls, default: int = 15) -> int:
        """Get session timeout in minutes."""
        return cls.get_setting('session_timeout_minutes', default, 'number')
    
    @classmethod
    def get_pickup_code_expiry_days(cls, default: int = 3) -> int:
        """Get pickup code expiry in days."""
        return cls.get_setting('pickup_code_expiry_days', default, 'number')


# Signal handler to invalidate cache when settings change
def invalidate_setting_cache(sender, instance, **kwargs):
    """Signal handler to invalidate cache when a SystemSetting is saved."""
    SystemSettingsHelper.invalidate_cache(instance.key)


# Connect the signal when this module is imported
def connect_signals():
    """Connect post_save signal for SystemSetting model."""
    try:
        from django.db.models.signals import post_save, post_delete
        from admin_dashboard.models import SystemSetting
        
        post_save.connect(invalidate_setting_cache, sender=SystemSetting)
        post_delete.connect(invalidate_setting_cache, sender=SystemSetting)
    except Exception:
        # If models aren't ready yet, signals will be connected later
        pass


# Try to connect signals on import
connect_signals()