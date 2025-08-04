"""
Tests for System Settings Helper

These tests ensure the SystemSettingsHelper works correctly and safely
handles various edge cases without breaking the application.
"""
import json
from decimal import Decimal
from django.test import TestCase
from django.core.cache import cache
from unittest.mock import patch, MagicMock
from .system_settings import SystemSettingsHelper


class SystemSettingsHelperTest(TestCase):
    """Test the SystemSettingsHelper utility class."""
    
    def setUp(self):
        """Clear cache before each test."""
        cache.clear()
    
    def tearDown(self):
        """Clear cache after each test."""
        cache.clear()
    
    @patch('utils.system_settings.SystemSetting')
    def test_get_setting_text_type(self, mock_system_setting):
        """Test getting a text setting."""
        # Mock the SystemSetting model
        mock_setting = MagicMock()
        mock_setting.value = "test_value"
        mock_system_setting.objects.get.return_value = mock_setting
        
        result = SystemSettingsHelper.get_setting('test_key', 'default', 'text')
        
        self.assertEqual(result, "test_value")
        mock_system_setting.objects.get.assert_called_once_with(key='test_key')
    
    @patch('utils.system_settings.SystemSetting')
    def test_get_setting_number_type(self, mock_system_setting):
        """Test getting a number setting."""
        mock_setting = MagicMock()
        mock_setting.value = "42"
        mock_system_setting.objects.get.return_value = mock_setting
        
        result = SystemSettingsHelper.get_setting('test_key', 0, 'number')
        
        self.assertEqual(result, 42)
        
    @patch('utils.system_settings.SystemSetting')
    def test_get_setting_decimal_type(self, mock_system_setting):
        """Test getting a decimal setting."""
        mock_setting = MagicMock()
        mock_setting.value = "3.14"
        mock_system_setting.objects.get.return_value = mock_setting
        
        result = SystemSettingsHelper.get_setting('test_key', Decimal('0'), 'decimal')
        
        self.assertEqual(result, Decimal('3.14'))
    
    @patch('utils.system_settings.SystemSetting')
    def test_get_setting_boolean_type_true(self, mock_system_setting):
        """Test getting a boolean setting (true values)."""
        mock_setting = MagicMock()
        
        for true_value in ['true', 'True', '1', 'yes', 'on']:
            mock_setting.value = true_value
            mock_system_setting.objects.get.return_value = mock_setting
            
            result = SystemSettingsHelper.get_setting('test_key', False, 'boolean')
            self.assertTrue(result, f"Failed for value: {true_value}")
    
    @patch('utils.system_settings.SystemSetting')
    def test_get_setting_boolean_type_false(self, mock_system_setting):
        """Test getting a boolean setting (false values)."""
        mock_setting = MagicMock()
        
        for false_value in ['false', 'False', '0', 'no', 'off', 'anything_else']:
            mock_setting.value = false_value
            mock_system_setting.objects.get.return_value = mock_setting
            
            result = SystemSettingsHelper.get_setting('test_key', True, 'boolean')
            self.assertFalse(result, f"Failed for value: {false_value}")
    
    @patch('utils.system_settings.SystemSetting')
    def test_get_setting_json_type(self, mock_system_setting):
        """Test getting a JSON setting."""
        mock_setting = MagicMock()
        test_data = {"key": "value", "number": 42}
        mock_setting.value = json.dumps(test_data)
        mock_system_setting.objects.get.return_value = mock_setting
        
        result = SystemSettingsHelper.get_setting('test_key', {}, 'json')
        
        self.assertEqual(result, test_data)
    
    @patch('utils.system_settings.SystemSetting')
    def test_get_setting_not_found_returns_default(self, mock_system_setting):
        """Test that default is returned when setting doesn't exist."""
        mock_system_setting.objects.get.side_effect = mock_system_setting.DoesNotExist()
        
        result = SystemSettingsHelper.get_setting('nonexistent_key', 'default_value')
        
        self.assertEqual(result, 'default_value')
    
    @patch('utils.system_settings.SystemSetting')
    def test_get_setting_database_error_returns_default(self, mock_system_setting):
        """Test that default is returned when database error occurs."""
        mock_system_setting.objects.get.side_effect = Exception("Database error")
        
        result = SystemSettingsHelper.get_setting('test_key', 'default_value')
        
        self.assertEqual(result, 'default_value')
    
    @patch('utils.system_settings.SystemSetting')
    def test_get_setting_invalid_number_returns_default(self, mock_system_setting):
        """Test that default is returned for invalid number conversion."""
        mock_setting = MagicMock()
        mock_setting.value = "not_a_number"
        mock_system_setting.objects.get.return_value = mock_setting
        
        result = SystemSettingsHelper.get_setting('test_key', 999, 'number')
        
        self.assertEqual(result, 999)
    
    @patch('utils.system_settings.SystemSetting')
    def test_get_setting_invalid_json_returns_default(self, mock_system_setting):
        """Test that default is returned for invalid JSON."""
        mock_setting = MagicMock()
        mock_setting.value = "not valid json {"
        mock_system_setting.objects.get.return_value = mock_setting
        
        result = SystemSettingsHelper.get_setting('test_key', {'default': True}, 'json')
        
        self.assertEqual(result, {'default': True})
    
    @patch('utils.system_settings.SystemSetting')
    def test_caching_works(self, mock_system_setting):
        """Test that settings are cached properly."""
        mock_setting = MagicMock()
        mock_setting.value = "cached_value"
        mock_system_setting.objects.get.return_value = mock_setting
        
        # First call should hit database
        result1 = SystemSettingsHelper.get_setting('cache_test', 'default')
        self.assertEqual(result1, "cached_value")
        
        # Second call should use cache (mock should not be called again)
        mock_system_setting.objects.get.reset_mock()
        result2 = SystemSettingsHelper.get_setting('cache_test', 'default')
        self.assertEqual(result2, "cached_value")
        
        # Verify database was not called second time
        mock_system_setting.objects.get.assert_not_called()
    
    def test_convenience_methods(self):
        """Test the convenience methods with defaults."""
        # These should all return defaults when no settings exist
        self.assertEqual(SystemSettingsHelper.get_max_books_per_user(10), 10)
        self.assertEqual(SystemSettingsHelper.get_max_borrowing_days(7), 7)
        self.assertEqual(SystemSettingsHelper.get_fine_per_day(Decimal('1.50')), Decimal('1.50'))
        self.assertEqual(SystemSettingsHelper.get_reservation_timeout_hours(48), 48)
        self.assertEqual(SystemSettingsHelper.get_session_timeout_minutes(30), 30)
        self.assertEqual(SystemSettingsHelper.get_pickup_code_expiry_days(5), 5)
    
    def test_cache_invalidation(self):
        """Test cache invalidation functionality."""
        # Set a cached value
        cache.set(f"{SystemSettingsHelper.CACHE_PREFIX}test_key", "cached_value", 300)
        
        # Verify it's cached
        cached = cache.get(f"{SystemSettingsHelper.CACHE_PREFIX}test_key")
        self.assertEqual(cached, "cached_value")
        
        # Invalidate specific key
        SystemSettingsHelper.invalidate_cache('test_key')
        
        # Verify it's gone
        cached = cache.get(f"{SystemSettingsHelper.CACHE_PREFIX}test_key")
        self.assertIsNone(cached)
    
    @patch('utils.system_settings.SystemSetting')
    def test_float_number_conversion(self, mock_system_setting):
        """Test that float strings are properly converted to integers."""
        mock_setting = MagicMock()
        mock_setting.value = "42.7"  # Float string
        mock_system_setting.objects.get.return_value = mock_setting
        
        result = SystemSettingsHelper.get_setting('test_key', 0, 'number')
        
        self.assertEqual(result, 42)  # Should convert to int
    
    def test_convert_value_edge_cases(self):
        """Test edge cases in value conversion."""
        # Test empty string
        result = SystemSettingsHelper._convert_value('', 'number', 999)
        self.assertEqual(result, 999)
        
        # Test None (shouldn't happen but let's be safe)
        result = SystemSettingsHelper._convert_value(None, 'text', 'default')
        self.assertEqual(result, 'default')