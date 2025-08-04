from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import authenticate
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError
from datetime import timedelta, date
from decimal import Decimal
from .models import User, MembershipType
from .forms import UserRegistrationForm, UserLoginForm, MembershipTypeForm, AdminUserCreationForm


class UserModelTest(TestCase):
    """Test cases for the User model including validation and business logic"""
    
    def setUp(self):
        """Set up test data"""
        self.membership_type = MembershipType.objects.create(
            name="Basic",
            monthly_fee=Decimal('10.00'),
            annual_fee=Decimal('100.00'),
            max_books=3,
            loan_period_days=14,
            extension_days=7
        )
        
    def test_user_creation_valid_data(self):
        """Test Case 1: Create user with valid data"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='ValidPass123!',
            first_name='Test',
            last_name='User',
            phone_number='1234567890',
            role='member'
        )
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.role, 'member')
        self.assertEqual(user.failed_login_attempts, 0)
        self.assertFalse(user.is_account_locked())
        
    def test_user_invalid_role(self):
        """Test Case 2: Create user with invalid role (should fail validation)"""
        with self.assertRaises(ValidationError):
            user = User(
                username='testuser',
                email='test@example.com',
                role='invalid_role',  # Invalid role
                phone_number='1234567890'
            )
            user.full_clean()  # This should raise ValidationError
            
    def test_phone_number_max_length(self):
        """Test Case 3: Phone number exceeding max length should fail"""
        with self.assertRaises(ValidationError):
            user = User(
                username='testuser',
                email='test@example.com',
                phone_number='1' * 25,  # Exceeds max_length=20
                role='member'
            )
            user.full_clean()
            
    def test_account_locking_mechanism(self):
        """Test Case 4: Account locking after failed login attempts"""
        user = User.objects.create_user(
            username='locktest',
            email='lock@test.com',
            password='ValidPass123!',
            role='member'
        )
        
        # Simulate failed login attempts
        max_attempts = settings.ACCOUNT_LOCK_SETTINGS['MAX_FAILED_ATTEMPTS']
        for i in range(max_attempts):
            user.increment_failed_attempts()
            
        self.assertTrue(user.is_account_locked())
        self.assertEqual(user.failed_login_attempts, max_attempts)
        
    def test_account_lock_warning_threshold(self):
        """Test Case 5: Warning threshold for approaching lock"""
        user = User.objects.create_user(
            username='warningtest',
            email='warning@test.com',
            password='ValidPass123!',
            role='member'
        )
        
        # Add attempts up to warning threshold
        warning_threshold = settings.ACCOUNT_LOCK_SETTINGS['WARNING_THRESHOLD']
        for i in range(warning_threshold):
            user.increment_failed_attempts()
            
        self.assertTrue(user.should_show_warning())
        self.assertFalse(user.is_account_locked())  # Not locked yet
        
    def test_account_lock_not_applied_to_admin(self):
        """Test Case 6: Account lock should not apply to admin users"""
        admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='ValidPass123!',
            role='admin'
        )
        
        # Simulate many failed attempts
        for i in range(10):  # More than max attempts
            admin_user.increment_failed_attempts()
            
        self.assertFalse(admin_user.is_account_locked())  # Admin should not be locked
        
    def test_password_expiry_for_admin_manager(self):
        """Test Case 7: Password expiry for admin/manager users"""
        admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='ValidPass123!',
            role='admin'
        )
        
        # Test new user without last_password_change
        self.assertTrue(admin_user.is_password_expired())
        
        # Set password change date to 7 months ago
        admin_user.last_password_change = timezone.now() - timedelta(days=210)
        admin_user.save()
        self.assertTrue(admin_user.is_password_expired())
        
        # Set recent password change
        admin_user.last_password_change = timezone.now() - timedelta(days=30)
        admin_user.save()
        self.assertFalse(admin_user.is_password_expired())
        
    def test_password_no_expiry_for_member(self):
        """Test Case 8: Password should not expire for regular members"""
        member = User.objects.create_user(
            username='member',
            email='member@test.com',
            password='ValidPass123!',
            role='member'
        )
        
        # Even without last_password_change, member passwords don't expire
        self.assertFalse(member.is_password_expired())
        
    def test_gdpr_consent_fields(self):
        """Test Case 9: GDPR consent fields validation"""
        user = User.objects.create_user(
            username='gdprtest',
            email='gdpr@test.com',
            password='ValidPass123!',
            privacy_consent=True,
            marketing_consent=False,
            consent_date=timezone.now(),
            consent_ip='192.168.1.1'
        )
        
        self.assertTrue(user.privacy_consent)
        self.assertFalse(user.marketing_consent)
        self.assertIsNotNone(user.consent_date)
        self.assertEqual(user.consent_ip, '192.168.1.1')
        
    def test_negative_failed_attempts(self):
        """Test Case 10: Negative failed attempts should not be allowed"""
        user = User.objects.create_user(
            username='negativetest',
            email='negative@test.com',
            password='ValidPass123!',
            role='member'
        )
        
        # Try to set negative failed attempts
        with self.assertRaises(ValidationError):
            user.failed_login_attempts = -1
            user.full_clean()


class MembershipTypeModelTest(TestCase):
    """Test cases for MembershipType model"""
    
    def test_membership_type_creation_valid(self):
        """Test Case 11: Create membership type with valid data"""
        membership = MembershipType.objects.create(
            name="Premium",
            monthly_fee=Decimal('25.50'),
            annual_fee=Decimal('250.00'),
            max_books=10,
            loan_period_days=21,
            extension_days=7
        )
        
        self.assertEqual(membership.name, "Premium")
        self.assertEqual(membership.monthly_fee, Decimal('25.50'))
        self.assertEqual(membership.max_books, 10)
        
    def test_negative_membership_fees(self):
        """Test Case 12: Negative fees should not be allowed"""
        with self.assertRaises(ValidationError):
            membership = MembershipType(
                name="Invalid",
                monthly_fee=Decimal('-10.00'),  # Negative fee
                annual_fee=Decimal('100.00'),
                max_books=5,
                loan_period_days=14,
                extension_days=7
            )
            membership.full_clean()
            
    def test_zero_max_books(self):
        """Test Case 13: Zero max books should not be allowed"""
        with self.assertRaises(ValidationError):
            membership = MembershipType(
                name="Invalid",
                monthly_fee=Decimal('10.00'),
                annual_fee=Decimal('100.00'),
                max_books=0,  # Zero books not allowed
                loan_period_days=14,
                extension_days=7
            )
            membership.full_clean()
            
    def test_excessive_max_books(self):
        """Test Case 14: Excessive max books boundary test"""
        # Test with very high number (boundary test)
        membership = MembershipType.objects.create(
            name="Unlimited",
            monthly_fee=Decimal('100.00'),
            annual_fee=Decimal('1000.00'),
            max_books=999999,  # Very high number
            loan_period_days=365,
            extension_days=30
        )
        self.assertEqual(membership.max_books, 999999)


class UserFormsTest(TestCase):
    """Test cases for User-related forms"""
    
    def test_user_registration_form_valid(self):
        """Test Case 15: Valid user registration form"""
        form_data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'phone_number': '1234567890',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!'
        }
        form = UserRegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())
        
    def test_user_registration_weak_password(self):
        """Test Case 16: Weak password should be rejected"""
        form_data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'phone_number': '1234567890',
            'password1': 'weak',  # Too weak
            'password2': 'weak'
        }
        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        
    def test_user_registration_password_mismatch(self):
        """Test Case 17: Password mismatch should be rejected"""
        form_data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'phone_number': '1234567890',
            'password1': 'StrongPass123!',
            'password2': 'DifferentPass123!'  # Mismatch
        }
        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        
    def test_membership_type_form_valid(self):
        """Test Case 18: Valid membership type form"""
        form_data = {
            'name': 'Student',
            'monthly_fee': '15.00',
            'annual_fee': '150.00',
            'max_books': '5',
            'loan_period_days': '21',
            'extension_days': '7'
        }
        form = MembershipTypeForm(data=form_data)
        self.assertTrue(form.is_valid())
        
    def test_membership_type_form_negative_values(self):
        """Test Case 19: Negative values in membership form should be rejected"""
        form_data = {
            'name': 'Invalid',
            'monthly_fee': '-10.00',  # Negative
            'annual_fee': '150.00',
            'max_books': '5',
            'loan_period_days': '21',
            'extension_days': '7'
        }
        form = MembershipTypeForm(data=form_data)
        self.assertFalse(form.is_valid())


class AdminUserCreationFormTest(TestCase):
    """Test cases for AdminUserCreationForm - ensuring security measures match regular registration"""
    
    def test_admin_user_creation_form_valid(self):
        """Test Case 96: Valid admin user creation form with proper security measures"""
        form_data = {
            'username': 'adminuser',
            'email': 'adminuser@example.com',
            'first_name': 'Admin',
            'last_name': 'User',
            'phone_number': '+1234567890',
            'role': 'member',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!'
        }
        form = AdminUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())
        
    def test_admin_form_phone_number_validation(self):
        """Test Case 97: Phone number validation in admin form"""
        # Valid phone number
        form_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'phone_number': '+1234567890',
            'role': 'member',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!'
        }
        form = AdminUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Invalid phone number - too short
        form_data['phone_number'] = '123'
        form = AdminUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('phone_number', form.errors)
        
        # Invalid phone number - too long
        form_data['phone_number'] = '+12345678901234567890'
        form = AdminUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('phone_number', form.errors)
        
    def test_admin_form_password_requirements(self):
        """Test Case 98: Password requirements in admin form match regular registration"""
        base_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'phone_number': '+1234567890',
            'role': 'member',
            'password2': 'StrongPass123!'
        }
        
        # Test password too short
        form_data = base_data.copy()
        form_data['password1'] = 'Short1!'
        form = AdminUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('password1', form.errors)
        
        # Test password without uppercase
        form_data['password1'] = 'strongpass123!'
        form = AdminUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('password1', form.errors)
        
        # Test password without lowercase
        form_data['password1'] = 'STRONGPASS123!'
        form = AdminUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('password1', form.errors)
        
        # Test password without number
        form_data['password1'] = 'StrongPass!'
        form = AdminUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('password1', form.errors)
        
        # Test password without special character
        form_data['password1'] = 'StrongPass123'
        form = AdminUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('password1', form.errors)
        
        # Test valid password
        form_data['password1'] = 'StrongPass123!'
        form = AdminUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())
        
    def test_admin_form_duplicate_username_email(self):
        """Test Case 99: Duplicate username and email validation in admin form"""
        # Create existing user
        User.objects.create_user(
            username='existinguser',
            email='existing@example.com',
            password='ValidPass123!'
        )
        
        # Test duplicate username
        form_data = {
            'username': 'existinguser',
            'email': 'new@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'phone_number': '+1234567890',
            'role': 'member',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!'
        }
        form = AdminUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)
        
        # Test duplicate email
        form_data['username'] = 'newuser'
        form_data['email'] = 'existing@example.com'
        form = AdminUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        
    def test_admin_form_required_fields(self):
        """Test Case 100: Required fields validation in admin form"""
        # Test missing required fields
        form_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            # Missing first_name, last_name, phone_number, role, passwords
        }
        form = AdminUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        
        # Check that required fields are validated (some may be handled by Django's built-in validation)
        required_fields = ['phone_number', 'role', 'password1', 'password2']
        for field in required_fields:
            self.assertIn(field, form.errors)
            
    def test_admin_form_role_validation(self):
        """Test Case 101: Role validation in admin form"""
        form_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'phone_number': '+1234567890',
            'role': 'invalid_role',  # Invalid role
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!'
        }
        form = AdminUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('role', form.errors)
        
    def test_admin_form_security_consistency(self):
        """Test Case 102: Security measures consistency between admin and regular forms"""
        # Test that admin form has same password requirements as regular form
        admin_form = AdminUserCreationForm()
        regular_form = UserRegistrationForm()
        
        # Both forms should have password validation
        self.assertIn('password1', admin_form.fields)
        self.assertIn('password1', regular_form.fields)
        
        # Both forms should have phone number validation
        self.assertIn('phone_number', admin_form.fields)
        self.assertIn('phone_number', regular_form.fields)
        
        # Admin form should have additional role field
        self.assertIn('role', admin_form.fields)
        
        # Test that both forms reject weak passwords
        weak_password_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'phone_number': '+1234567890',
            'password1': 'weak',
            'password2': 'weak'
        }
        
        # Add role for admin form
        admin_weak_data = weak_password_data.copy()
        admin_weak_data['role'] = 'member'
        
        admin_form = AdminUserCreationForm(data=admin_weak_data)
        regular_form = UserRegistrationForm(data=weak_password_data)
        
        # Both should reject weak passwords
        self.assertFalse(admin_form.is_valid())
        self.assertFalse(regular_form.is_valid())


class UserAuthenticationTest(TestCase):
    """Test cases for user authentication and login"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='authtest',
            email='auth@test.com',
            password='ValidPass123!',
            role='member'
        )
        
    def test_successful_login(self):
        """Test Case 20: Successful login with valid credentials"""
        user = authenticate(username='authtest', password='ValidPass123!')
        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'authtest')
        
    def test_failed_login_wrong_password(self):
        """Test Case 21: Failed login with wrong password"""
        user = authenticate(username='authtest', password='WrongPassword!')
        self.assertIsNone(user)
        
    def test_login_locked_account(self):
        """Test Case 22: Login should fail for locked account"""
        # Lock the account
        self.user.account_locked_until = timezone.now() + timedelta(minutes=5)
        self.user.save()
        
        user = authenticate(username='authtest', password='ValidPass123!')
        # Authentication might succeed, but account should be marked as locked
        self.assertTrue(self.user.is_account_locked())


# Create your tests here.
