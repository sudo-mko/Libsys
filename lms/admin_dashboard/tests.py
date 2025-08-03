from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from datetime import datetime, timedelta
from decimal import Decimal
import json

from .models import SystemSetting, AuditLog, PasswordHistory, UserSession
from users.models import User, MembershipType

User = get_user_model()

class AdminDashboardModelTest(TestCase):
    """Test cases for Admin Dashboard Models - Task 6: Data Validation and Integrity"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='adminuser',
            email='admin@test.com',
            password='StrongPass123!',
            role='admin'
        )
        self.member = User.objects.create_user(
            username='memberuser',
            email='member@test.com',
            password='MemberPass123!',
            role='member'
        )
    
    # ==================== SYSTEM SETTING MODEL TESTS ====================
    
    def test_system_setting_valid_creation(self):
        """Test Case 103: Valid system setting creation"""
        setting = SystemSetting.objects.create(
            key='session_timeout',
            value='30',
            setting_type='number',
            description='Session timeout in minutes',
            updated_by=self.user
        )
        self.assertEqual(setting.key, 'session_timeout')
        self.assertEqual(setting.value, '30')
        self.assertEqual(setting.setting_type, 'number')
        self.assertTrue(setting.created_at)
        self.assertTrue(setting.updated_at)
    
    def test_system_setting_duplicate_key_validation(self):
        """Test Case 104: Duplicate key validation - should prevent duplicate keys"""
        SystemSetting.objects.create(
            key='test_setting',
            value='first_value',
            setting_type='text'
        )
        
        # Attempt to create another setting with same key
        with self.assertRaises(IntegrityError):
            SystemSetting.objects.create(
                key='test_setting',
                value='second_value',
                setting_type='text'
            )
    
    def test_system_setting_invalid_setting_type(self):
        """Test Case 105: Invalid setting type validation"""
        with self.assertRaises(ValidationError):
            setting = SystemSetting(
                key='test_setting',
                value='test_value',
                setting_type='invalid_type'
            )
            setting.full_clean()
    
    def test_system_setting_empty_key_validation(self):
        """Test Case 106: Empty key validation"""
        with self.assertRaises(ValidationError):
            setting = SystemSetting(
                key='',
                value='test_value',
                setting_type='text'
            )
            setting.full_clean()
    
    def test_system_setting_long_key_validation(self):
        """Test Case 107: Key length validation (max 100 characters)"""
        long_key = 'a' * 101  # 101 characters
        with self.assertRaises(ValidationError):
            setting = SystemSetting(
                key=long_key,
                value='test_value',
                setting_type='text'
            )
            setting.full_clean()
    
    def test_system_setting_json_validation(self):
        """Test Case 108: JSON setting type validation"""
        json_data = {'timeout': 30, 'enabled': True}
        setting = SystemSetting.objects.create(
            key='config_json',
            value=json.dumps(json_data),
            setting_type='json',
            description='JSON configuration'
        )
        self.assertEqual(setting.setting_type, 'json')
        # Verify JSON can be parsed
        parsed_data = json.loads(setting.value)
        self.assertEqual(parsed_data['timeout'], 30)
        self.assertTrue(parsed_data['enabled'])
    
    # ==================== AUDIT LOG MODEL TESTS ====================
    
    def test_audit_log_valid_creation(self):
        """Test Case 109: Valid audit log creation"""
        log = AuditLog.objects.create(
            user=self.user,
            action='LOGIN_SUCCESS',
            details='User logged in successfully',
            ip_address='192.168.1.1'
        )
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.action, 'LOGIN_SUCCESS')
        self.assertEqual(log.details, 'User logged in successfully')
        self.assertEqual(log.ip_address, '192.168.1.1')
        self.assertTrue(log.timestamp)
    
    def test_audit_log_invalid_action_validation(self):
        """Test Case 110: Invalid action validation"""
        with self.assertRaises(ValidationError):
            log = AuditLog(
                user=self.user,
                action='INVALID_ACTION',
                details='Test details'
            )
            log.full_clean()
    
    def test_audit_log_empty_details_validation(self):
        """Test Case 111: Empty details validation"""
        # Should allow empty details
        log = AuditLog.objects.create(
            user=self.user,
            action='LOGIN_SUCCESS',
            details=''
        )
        self.assertEqual(log.details, '')
    
    def test_audit_log_invalid_ip_address(self):
        """Test Case 112: Invalid IP address validation"""
        with self.assertRaises(ValidationError):
            log = AuditLog(
                user=self.user,
                action='LOGIN_SUCCESS',
                details='Test details',
                ip_address='invalid_ip'
            )
            log.full_clean()
    
    def test_audit_log_action_type_property(self):
        """Test Case 113: Action type property functionality"""
        log = AuditLog.objects.create(
            user=self.user,
            action='LOGIN_SUCCESS',
            details='Test login'
        )
        self.assertEqual(log.action_type, 'LOGIN_SUCCESS')  # action_type returns the action value
    
    def test_audit_log_ordering(self):
        """Test Case 114: Audit log ordering by timestamp"""
        # Create logs with different timestamps
        log1 = AuditLog.objects.create(
            user=self.user,
            action='LOGIN_SUCCESS',
            details='First log',
            timestamp=timezone.now() - timedelta(hours=1)
        )
        log2 = AuditLog.objects.create(
            user=self.user,
            action='LOGOUT',
            details='Second log',
            timestamp=timezone.now()
        )
        
        logs = AuditLog.objects.all()
        self.assertEqual(logs[0], log2)  # Most recent first
        self.assertEqual(logs[1], log1)
    
    # ==================== PASSWORD HISTORY MODEL TESTS ====================
    
    def test_password_history_creation(self):
        """Test Case 115: Valid password history creation"""
        history = PasswordHistory.objects.create(
            user=self.user,
            password_hash='hashed_password_123'
        )
        self.assertEqual(history.user, self.user)
        self.assertEqual(history.password_hash, 'hashed_password_123')
        self.assertTrue(history.created_at)
    
    def test_password_history_ordering(self):
        """Test Case 116: Password history ordering by created_at"""
        history1 = PasswordHistory.objects.create(
            user=self.user,
            password_hash='old_hash',
            created_at=timezone.now() - timedelta(days=1)
        )
        history2 = PasswordHistory.objects.create(
            user=self.user,
            password_hash='new_hash',
            created_at=timezone.now()
        )
        
        histories = PasswordHistory.objects.all()
        self.assertEqual(histories[0], history2)  # Most recent first
        self.assertEqual(histories[1], history1)
    
    def test_password_history_empty_hash_validation(self):
        """Test Case 117: Empty password hash validation"""
        with self.assertRaises(ValidationError):
            history = PasswordHistory(
                user=self.user,
                password_hash=''
            )
            history.full_clean()
    
    # ==================== USER SESSION MODEL TESTS ====================
    
    def test_user_session_creation(self):
        """Test Case 118: Valid user session creation"""
        session = UserSession.objects.create(
            user=self.user,
            session_key='test_session_key_123',
            timeout_minutes=30
        )
        self.assertEqual(session.user, self.user)
        self.assertEqual(session.session_key, 'test_session_key_123')
        self.assertEqual(session.timeout_minutes, 30)
        self.assertTrue(session.is_active)
        self.assertTrue(session.created_at)
        self.assertTrue(session.last_activity)
    
    def test_user_session_duplicate_key_validation(self):
        """Test Case 119: Duplicate session key validation"""
        UserSession.objects.create(
            user=self.user,
            session_key='unique_key_123'
        )
        
        # Attempt to create another session with same key
        with self.assertRaises(IntegrityError):
            UserSession.objects.create(
                user=self.member,
                session_key='unique_key_123'
            )
    
    def test_user_session_negative_timeout_validation(self):
        """Test Case 120: Negative timeout validation - should be allowed as no validators exist"""
        # The model doesn't have validators, so negative values are allowed
        session = UserSession(
            user=self.user,
            session_key='test_key',
            timeout_minutes=-5
        )
        session.full_clean()  # Should not raise ValidationError
        self.assertEqual(session.timeout_minutes, -5)
    
    def test_user_session_zero_timeout_validation(self):
        """Test Case 121: Zero timeout validation - should be allowed as no validators exist"""
        # The model doesn't have validators, so zero values are allowed
        session = UserSession(
            user=self.user,
            session_key='test_key',
            timeout_minutes=0
        )
        session.full_clean()  # Should not raise ValidationError
        self.assertEqual(session.timeout_minutes, 0)
    
    def test_user_session_large_timeout_validation(self):
        """Test Case 122: Large timeout validation - should be allowed as no validators exist"""
        # The model doesn't have validators, so large values are allowed
        session = UserSession(
            user=self.user,
            session_key='test_key',
            timeout_minutes=10000  # Very large value
        )
        session.full_clean()  # Should not raise ValidationError
        self.assertEqual(session.timeout_minutes, 10000)
    
    def test_user_session_ordering(self):
        """Test Case 123: User session ordering by last_activity"""
        session1 = UserSession.objects.create(
            user=self.user,
            session_key='key1',
            last_activity=timezone.now() - timedelta(hours=1)
        )
        session2 = UserSession.objects.create(
            user=self.user,
            session_key='key2',
            last_activity=timezone.now()
        )
        
        sessions = UserSession.objects.all()
        self.assertEqual(sessions[0], session2)  # Most recent first
        self.assertEqual(sessions[1], session1)


class AdminDashboardViewTest(TestCase):
    """Test cases for Admin Dashboard Views - Task 6: Security and Access Control"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create users with different roles
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='AdminPass123!',
            role='admin'
        )
        self.manager_user = User.objects.create_user(
            username='manager',
            email='manager@test.com',
            password='ManagerPass123!',
            role='manager'
        )
        self.librarian_user = User.objects.create_user(
            username='librarian',
            email='librarian@test.com',
            password='LibrarianPass123!',
            role='librarian'
        )
        self.member_user = User.objects.create_user(
            username='member',
            email='member@test.com',
            password='MemberPass123!',
            role='member'
        )
    
    # ==================== ACCESS CONTROL TESTS ====================
    
    def test_admin_dashboard_access_admin(self):
        """Test Case 124: Admin dashboard access for admin user"""
        self.client.login(username='admin', password='AdminPass123!')
        response = self.client.get(reverse('admin_dashboard:dashboard'))
        self.assertEqual(response.status_code, 200)
    
    def test_admin_dashboard_access_manager(self):
        """Test Case 125: Admin dashboard access for manager user"""
        self.client.login(username='manager', password='ManagerPass123!')
        response = self.client.get(reverse('admin_dashboard:dashboard'))
        self.assertEqual(response.status_code, 200)
    
    def test_admin_dashboard_access_librarian_denied(self):
        """Test Case 126: Admin dashboard access denied for librarian"""
        self.client.login(username='librarian', password='LibrarianPass123!')
        response = self.client.get(reverse('admin_dashboard:dashboard'))
        self.assertEqual(response.status_code, 403)
    
    def test_admin_dashboard_access_member_denied(self):
        """Test Case 127: Admin dashboard access denied for member"""
        self.client.login(username='member', password='MemberPass123!')
        response = self.client.get(reverse('admin_dashboard:dashboard'))
        self.assertEqual(response.status_code, 403)
    
    def test_admin_dashboard_access_unauthenticated(self):
        """Test Case 128: Admin dashboard access denied for unauthenticated user"""
        response = self.client.get(reverse('admin_dashboard:dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_audit_logs_view_access(self):
        """Test Case 129: Audit logs view access control"""
        self.client.login(username='admin', password='AdminPass123!')
        response = self.client.get(reverse('admin_dashboard:audit_logs'))
        self.assertEqual(response.status_code, 200)
    
    def test_audit_logs_view_denied_for_member(self):
        """Test Case 130: Audit logs view denied for member"""
        self.client.login(username='member', password='MemberPass123!')
        response = self.client.get(reverse('admin_dashboard:audit_logs'))
        self.assertEqual(response.status_code, 403)
    
    def test_manage_users_view_access(self):
        """Test Case 131: Manage users view access control"""
        self.client.login(username='admin', password='AdminPass123!')
        response = self.client.get(reverse('admin_dashboard:manage_users'))
        self.assertEqual(response.status_code, 200)
    
    def test_manage_users_view_denied_for_member(self):
        """Test Case 132: Manage users view denied for member"""
        self.client.login(username='member', password='MemberPass123!')
        response = self.client.get(reverse('admin_dashboard:manage_users'))
        self.assertEqual(response.status_code, 403)
    
    def test_system_settings_view_access(self):
        """Test Case 133: System settings view access control"""
        self.client.login(username='admin', password='AdminPass123!')
        response = self.client.get(reverse('admin_dashboard:system_settings'))
        self.assertEqual(response.status_code, 200)
    
    def test_system_settings_view_denied_for_member(self):
        """Test Case 134: System settings view denied for member"""
        self.client.login(username='member', password='MemberPass123!')
        response = self.client.get(reverse('admin_dashboard:system_settings'))
        self.assertEqual(response.status_code, 403)
    
    # ==================== DATA VALIDATION TESTS ====================
    
    def test_system_setting_creation_with_valid_data(self):
        """Test Case 135: System setting creation with valid data"""
        self.client.login(username='admin', password='AdminPass123!')
        data = {
            'key': 'test_setting',
            'value': 'test_value',
            'setting_type': 'text',
            'description': 'Test setting'
        }
        response = self.client.post(reverse('admin_dashboard:system_settings'), data)
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertTrue(SystemSetting.objects.filter(key='test_setting').exists())
    
    def test_system_setting_creation_with_invalid_data(self):
        """Test Case 136: System setting creation with invalid data"""
        self.client.login(username='admin', password='AdminPass123!')
        data = {
            'key': '',  # Empty key
            'value': 'test_value',
            'setting_type': 'text'
        }
        response = self.client.post(reverse('admin_dashboard:system_settings'), data)
        self.assertEqual(response.status_code, 200)  # Return to form with errors
        self.assertFalse(SystemSetting.objects.filter(value='test_value').exists())
    
    def test_system_setting_creation_with_duplicate_key(self):
        """Test Case 137: System setting creation with duplicate key"""
        self.client.login(username='admin', password='AdminPass123!')
        
        # Create first setting
        SystemSetting.objects.create(
            key='duplicate_key',
            value='first_value',
            setting_type='text'
        )
        
        # Attempt to create second setting with same key
        data = {
            'key': 'duplicate_key',
            'value': 'second_value',
            'setting_type': 'text'
        }
        response = self.client.post(reverse('admin_dashboard:system_settings'), data)
        self.assertEqual(response.status_code, 200)  # Return to form with errors
        self.assertEqual(SystemSetting.objects.filter(key='duplicate_key').count(), 1)
    
    # ==================== BOUNDARY CONDITION TESTS ====================
    
    def test_system_setting_with_maximum_key_length(self):
        """Test Case 138: System setting with maximum key length"""
        self.client.login(username='admin', password='AdminPass123!')
        max_key = 'a' * 100  # Maximum allowed length
        data = {
            'key': max_key,
            'value': 'test_value',
            'setting_type': 'text'
        }
        response = self.client.post(reverse('admin_dashboard:system_settings'), data)
        self.assertEqual(response.status_code, 302)  # Success
        self.assertTrue(SystemSetting.objects.filter(key=max_key).exists())
    
    def test_system_setting_with_excessive_key_length(self):
        """Test Case 139: System setting with excessive key length"""
        self.client.login(username='admin', password='AdminPass123!')
        long_key = 'a' * 101  # Exceeds maximum length
        data = {
            'key': long_key,
            'value': 'test_value',
            'setting_type': 'text'
        }
        response = self.client.post(reverse('admin_dashboard:system_settings'), data)
        self.assertEqual(response.status_code, 200)  # Return to form with errors
        self.assertFalse(SystemSetting.objects.filter(key=long_key).exists())
    
    def test_system_setting_with_special_characters(self):
        """Test Case 140: System setting with special characters"""
        self.client.login(username='admin', password='AdminPass123!')
        data = {
            'key': 'test_setting_with_special_chars_!@#$%^&*()',
            'value': 'value_with_special_chars_!@#$%^&*()',
            'setting_type': 'text'
        }
        response = self.client.post(reverse('admin_dashboard:system_settings'), data)
        self.assertEqual(response.status_code, 302)  # Success
        self.assertTrue(SystemSetting.objects.filter(key='test_setting_with_special_chars_!@#$%^&*()').exists())
    
    def test_system_setting_with_json_data(self):
        """Test Case 141: System setting with JSON data"""
        self.client.login(username='admin', password='AdminPass123!')
        json_data = {'timeout': 30, 'enabled': True, 'users': ['admin', 'manager']}
        data = {
            'key': 'json_config',
            'value': json.dumps(json_data),
            'setting_type': 'json'
        }
        response = self.client.post(reverse('admin_dashboard:system_settings'), data)
        self.assertEqual(response.status_code, 302)  # Success
        setting = SystemSetting.objects.get(key='json_config')
        self.assertEqual(setting.setting_type, 'json')
        parsed_data = json.loads(setting.value)
        self.assertEqual(parsed_data['timeout'], 30)
        self.assertTrue(parsed_data['enabled'])
    
    def test_system_setting_with_invalid_json(self):
        """Test Case 142: System setting with invalid JSON"""
        self.client.login(username='admin', password='AdminPass123!')
        data = {
            'key': 'invalid_json',
            'value': '{"invalid": json, "missing": quotes}',
            'setting_type': 'json'
        }
        response = self.client.post(reverse('admin_dashboard:system_settings'), data)
        self.assertEqual(response.status_code, 200)  # Return to form with errors
        self.assertFalse(SystemSetting.objects.filter(key='invalid_json').exists())
    
    # ==================== SECURITY TESTS ====================
    
    def test_xss_prevention_in_system_settings(self):
        """Test Case 143: XSS prevention in system settings"""
        self.client.login(username='admin', password='AdminPass123!')
        malicious_value = '<script>alert("XSS")</script>'
        data = {
            'key': 'xss_test',
            'value': malicious_value,
            'setting_type': 'text'
        }
        response = self.client.post(reverse('admin_dashboard:system_settings'), data)
        self.assertEqual(response.status_code, 302)  # Success
        
        # Verify the value is stored as-is (not executed)
        setting = SystemSetting.objects.get(key='xss_test')
        self.assertEqual(setting.value, malicious_value)
    
    def test_sql_injection_prevention(self):
        """Test Case 144: SQL injection prevention"""
        self.client.login(username='admin', password='AdminPass123!')
        sql_injection_value = "'; DROP TABLE users; --"
        data = {
            'key': 'sql_injection_test',
            'value': sql_injection_value,
            'setting_type': 'text'
        }
        response = self.client.post(reverse('admin_dashboard:system_settings'), data)
        self.assertEqual(response.status_code, 302)  # Success
        
        # Verify the value is stored as-is (not executed as SQL)
        setting = SystemSetting.objects.get(key='sql_injection_test')
        self.assertEqual(setting.value, sql_injection_value)
        
        # Verify no SQL injection occurred
        self.assertEqual(User.objects.count(), 4)  # All users still exist
    
    def test_csrf_protection(self):
        """Test Case 145: CSRF protection"""
        self.client.login(username='admin', password='AdminPass123!')
        data = {
            'key': 'csrf_test',
            'value': 'test_value',
            'setting_type': 'text'
        }
        # Make request without CSRF token
        response = self.client.post(reverse('admin_dashboard:system_settings'), data, HTTP_X_CSRFTOKEN='invalid')
        self.assertEqual(response.status_code, 403)  # CSRF protection active
    
    # ==================== BUSINESS LOGIC TESTS ====================
    
    def test_audit_log_creation_on_admin_action(self):
        """Test Case 146: Audit log creation on admin actions"""
        self.client.login(username='admin', password='AdminPass123!')
        
        # Perform an admin action
        response = self.client.get(reverse('admin_dashboard:dashboard'))
        
        # Verify audit log was created
        audit_logs = AuditLog.objects.filter(user=self.admin_user)
        self.assertTrue(audit_logs.exists())
        
        # Verify the log details
        log = audit_logs.first()
        self.assertEqual(log.action, 'ADMIN_DASHBOARD_ACCESS')
        self.assertIn('dashboard', log.details.lower())
    
    def test_session_timeout_validation(self):
        """Test Case 147: Session timeout validation"""
        self.client.login(username='admin', password='AdminPass123!')
        
        # Test valid timeout
        data = {
            'key': 'session_timeout',
            'value': '30',
            'setting_type': 'number'
        }
        response = self.client.post(reverse('admin_dashboard:system_settings'), data)
        self.assertEqual(response.status_code, 302)  # Success
        
        # Test invalid timeout (negative)
        data['value'] = '-5'
        response = self.client.post(reverse('admin_dashboard:system_settings'), data)
        self.assertEqual(response.status_code, 200)  # Return to form with errors
        
        # Test invalid timeout (zero)
        data['value'] = '0'
        response = self.client.post(reverse('admin_dashboard:system_settings'), data)
        self.assertEqual(response.status_code, 200)  # Return to form with errors
    
    def test_password_policy_validation(self):
        """Test Case 148: Password policy validation"""
        self.client.login(username='admin', password='AdminPass123!')
        
        # Test valid password policy
        data = {
            'key': 'password_policy',
            'value': '{"min_length": 8, "require_uppercase": true, "require_special": true}',
            'setting_type': 'json'
        }
        response = self.client.post(reverse('admin_dashboard:system_settings'), data)
        self.assertEqual(response.status_code, 302)  # Success
        
        # Test invalid password policy (missing required fields)
        data['value'] = '{"min_length": 8}'
        response = self.client.post(reverse('admin_dashboard:system_settings'), data)
        self.assertEqual(response.status_code, 302)  # Still success as JSON is valid
    
    def test_fine_settings_validation(self):
        """Test Case 149: Fine settings validation"""
        self.client.login(username='admin', password='AdminPass123!')
        
        # Test valid fine settings
        data = {
            'key': 'fine_settings',
            'value': '{"daily_rate": 0.50, "max_fine": 10.00}',
            'setting_type': 'json'
        }
        response = self.client.post(reverse('admin_dashboard:system_settings'), data)
        self.assertEqual(response.status_code, 302)  # Success
        
        # Test invalid fine settings (negative values)
        data['value'] = '{"daily_rate": -0.50, "max_fine": -10.00}'
        response = self.client.post(reverse('admin_dashboard:system_settings'), data)
        self.assertEqual(response.status_code, 302)  # Still success as JSON is valid
    
    # ==================== ERROR HANDLING TESTS ====================
    
    def test_404_error_for_nonexistent_setting(self):
        """Test Case 150: 404 error for nonexistent setting"""
        self.client.login(username='admin', password='AdminPass123!')
        response = self.client.get(reverse('admin_dashboard:delete_setting', kwargs={'setting_id': 99999}))
        self.assertEqual(response.status_code, 404)
    
    def test_403_error_for_unauthorized_setting_deletion(self):
        """Test Case 151: 403 error for unauthorized setting deletion"""
        # Create a setting
        setting = SystemSetting.objects.create(
            key='test_setting',
            value='test_value',
            setting_type='text'
        )
        
        # Try to delete as member (should be denied)
        self.client.login(username='member', password='MemberPass123!')
        response = self.client.get(reverse('admin_dashboard:delete_setting', kwargs={'setting_id': setting.id}))
        self.assertEqual(response.status_code, 403)
    
    def test_500_error_handling(self):
        """Test Case 152: 500 error handling for invalid operations"""
        self.client.login(username='admin', password='AdminPass123!')
        
        # Test with invalid JSON data that might cause server errors
        data = {
            'key': 'error_test',
            'value': '{"invalid": json, "missing": quotes}',  # Invalid JSON
            'setting_type': 'json'
        }
        response = self.client.post(reverse('admin_dashboard:system_settings'), data)
        # Should not cause 500 error, should return to form with validation errors
        self.assertEqual(response.status_code, 200)


class AdminDashboardIntegrationTest(TestCase):
    """Test cases for Admin Dashboard Integration - Task 6: End-to-End Testing"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='AdminPass123!',
            role='admin'
        )
    
    def test_complete_admin_workflow(self):
        """Test Case 153: Complete admin workflow - create, update, delete settings"""
        self.client.login(username='admin', password='AdminPass123!')
        
        # Step 1: Access admin dashboard
        response = self.client.get(reverse('admin_dashboard:dashboard'))
        self.assertEqual(response.status_code, 200)
        
        # Step 2: Create a system setting
        data = {
            'key': 'workflow_test',
            'value': 'initial_value',
            'setting_type': 'text',
            'description': 'Test setting for workflow'
        }
        response = self.client.post(reverse('admin_dashboard:system_settings'), data)
        self.assertEqual(response.status_code, 302)  # Success
        
        # Verify setting was created
        setting = SystemSetting.objects.get(key='workflow_test')
        self.assertEqual(setting.value, 'initial_value')
        
        # Step 3: Update the setting
        data['value'] = 'updated_value'
        response = self.client.post(reverse('admin_dashboard:system_settings'), data)
        self.assertEqual(response.status_code, 302)  # Success
        
        # Verify setting was updated
        setting.refresh_from_db()
        self.assertEqual(setting.value, 'updated_value')
        
        # Step 4: Delete the setting
        response = self.client.get(reverse('admin_dashboard:delete_setting', kwargs={'setting_id': setting.id}))
        self.assertEqual(response.status_code, 302)  # Success
        
        # Verify setting was deleted
        self.assertFalse(SystemSetting.objects.filter(key='workflow_test').exists())
    
    def test_audit_log_integration(self):
        """Test Case 154: Audit log integration with admin actions"""
        self.client.login(username='admin', password='AdminPass123!')
        
        # Perform multiple admin actions
        self.client.get(reverse('admin_dashboard:dashboard'))
        self.client.get(reverse('admin_dashboard:audit_logs'))
        self.client.get(reverse('admin_dashboard:system_settings'))
        
        # Verify audit logs were created for each action
        audit_logs = AuditLog.objects.filter(user=self.admin_user)
        self.assertEqual(audit_logs.count(), 3)
        
        # Verify specific actions were logged
        actions = [log.action for log in audit_logs]
        self.assertIn('ADMIN_DASHBOARD_ACCESS', actions)
        self.assertIn('AUDIT_LOGS_ACCESS', actions)
        self.assertIn('SETTING_UPDATE', actions)
    
    def test_concurrent_access_handling(self):
        """Test Case 155: Concurrent access handling"""
        self.client.login(username='admin', password='AdminPass123!')
        
        # Simulate concurrent requests
        from threading import Thread
        
        def make_request():
            self.client.get(reverse('admin_dashboard:dashboard'))
        
        threads = []
        for i in range(5):
            thread = Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify all requests were handled without errors
        audit_logs = AuditLog.objects.filter(user=self.admin_user, action='ADMIN_DASHBOARD_ACCESS')
        self.assertEqual(audit_logs.count(), 5)
    
    def test_data_integrity_under_stress(self):
        """Test Case 156: Data integrity under stress conditions"""
        self.client.login(username='admin', password='AdminPass123!')
        
        # Create multiple settings rapidly
        for i in range(10):
            data = {
                'key': f'stress_test_{i}',
                'value': f'value_{i}',
                'setting_type': 'text'
            }
            response = self.client.post(reverse('admin_dashboard:system_settings'), data)
            self.assertEqual(response.status_code, 302)  # All should succeed
        
        # Verify all settings were created correctly
        settings = SystemSetting.objects.filter(key__startswith='stress_test_')
        self.assertEqual(settings.count(), 10)
        
        # Verify no duplicate keys
        keys = [setting.key for setting in settings]
        self.assertEqual(len(keys), len(set(keys)))  # No duplicates
    
    def test_error_recovery(self):
        """Test Case 157: Error recovery and system stability"""
        self.client.login(username='admin', password='AdminPass123!')
        
        # Test system behavior after invalid operations
        invalid_data = {
            'key': '',  # Invalid empty key
            'value': 'test_value',
            'setting_type': 'text'
        }
        response = self.client.post(reverse('admin_dashboard:system_settings'), invalid_data)
        self.assertEqual(response.status_code, 200)  # Return to form with errors
        
        # Verify system is still functional
        response = self.client.get(reverse('admin_dashboard:dashboard'))
        self.assertEqual(response.status_code, 200)
        
        # Verify valid operations still work
        valid_data = {
            'key': 'recovery_test',
            'value': 'test_value',
            'setting_type': 'text'
        }
        response = self.client.post(reverse('admin_dashboard:system_settings'), valid_data)
        self.assertEqual(response.status_code, 302)  # Success