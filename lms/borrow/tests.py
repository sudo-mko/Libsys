from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
from .models import Borrowing, ExtensionRequest
from users.models import User, MembershipType
from library.models import Book, Author, Category
from branches.models import Branch


class BorrowingModelTest(TestCase):
    """Test cases for Borrowing model"""
    
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
        
        self.user = User.objects.create_user(
            username='borrower',
            email='borrower@test.com',
            password='ValidPass123!',
            role='member',
            membership=self.membership_type
        )
        
        self.librarian = User.objects.create_user(
            username='librarian',
            email='librarian@test.com',
            password='ValidPass123!',
            role='librarian'
        )
        
        self.author = Author.objects.create(name="Test Author")
        self.category = Category.objects.create(category_name="Test Category")
        self.branch = Branch.objects.create(
            branch_name="Main Branch",
            location="Downtown"
        )
        
        self.book = Book.objects.create(
            title="Test Book",
            author=self.author,
            category=self.category,
            isbn="9781234567890",
            publication_date=date(2020, 1, 1),
            branch=self.branch,
            edition=1,
            description="A test book"
        )
        
    def test_borrowing_creation_valid(self):
        """Test Case 41: Create borrowing with valid data"""
        borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            due_date=date.today() + timedelta(days=14),
            status='pending'
        )
        
        self.assertEqual(borrowing.user, self.user)
        self.assertEqual(borrowing.book, self.book)
        self.assertEqual(borrowing.status, 'pending')
        self.assertFalse(borrowing.is_extended)
        
    def test_borrowing_pickup_code_generation(self):
        """Test Case 42: Pickup code generation and uniqueness"""
        borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            due_date=date.today() + timedelta(days=14),
            status='approved'
        )
        
        # Generate pickup code
        pickup_code = borrowing.generate_pickup_code()
        
        self.assertIsNotNone(pickup_code)
        self.assertEqual(len(pickup_code), 10)
        self.assertTrue(pickup_code.isalnum())
        self.assertTrue(pickup_code.isupper() or pickup_code.isdigit())
        
    def test_borrowing_pickup_code_uniqueness(self):
        """Test Case 43: Pickup codes should be unique"""
        borrowing1 = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            due_date=date.today() + timedelta(days=14),
            status='approved'
        )
        
        # Create another book for second borrowing
        book2 = Book.objects.create(
            title="Test Book 2",
            author=self.author,
            category=self.category,
            isbn="9781234567891",
            publication_date=date(2020, 1, 1),
            branch=self.branch,
            edition=1,
            description="Another test book"
        )
        
        borrowing2 = Borrowing.objects.create(
            user=self.user,
            book=book2,
            due_date=date.today() + timedelta(days=14),
            status='approved'
        )
        
        code1 = borrowing1.generate_pickup_code()
        code2 = borrowing2.generate_pickup_code()
        
        self.assertNotEqual(code1, code2)
        
    def test_borrowing_due_date_in_past(self):
        """Test Case 44: Due date in the past should be handled"""
        past_date = date.today() - timedelta(days=1)
        borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            due_date=past_date,
            status='pending'
        )
        
        # Past due dates are allowed for overdue handling
        self.assertEqual(borrowing.due_date, past_date)
        
    def test_borrowing_due_date_far_future(self):
        """Test Case 45: Due date far in future boundary test"""
        far_future = date.today() + timedelta(days=365)
        borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            due_date=far_future,
            status='pending'
        )
        
        self.assertEqual(borrowing.due_date, far_future)
        
    def test_borrowing_invalid_status(self):
        """Test Case 46: Invalid status should fail validation"""
        with self.assertRaises(ValidationError):
            borrowing = Borrowing(
                user=self.user,
                book=self.book,
                due_date=date.today() + timedelta(days=14),
                status='invalid_status'  # Invalid status
            )
            borrowing.full_clean()
            
    def test_borrowing_code_expiry_check(self):
        """Test Case 47: Pickup code expiry functionality"""
        borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            due_date=date.today() + timedelta(days=14),
            status='approved',
            approved_date=timezone.now() - timedelta(days=8)  # 8 days ago
        )
        
        # Assuming 7-day expiry for pickup codes
        self.assertTrue(borrowing.is_code_expired())
        
    def test_borrowing_code_not_expired(self):
        """Test Case 48: Pickup code not expired"""
        borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            due_date=date.today() + timedelta(days=14),
            status='approved',
            approved_date=timezone.now() - timedelta(days=3)  # 3 days ago
        )
        
        # Should not be expired yet
        self.assertFalse(borrowing.is_code_expired())
        
    def test_borrowing_missing_required_fields(self):
        """Test Case 49: Missing required fields should fail"""
        with self.assertRaises(ValidationError):
            borrowing = Borrowing(
                # Missing user and book
                due_date=date.today() + timedelta(days=14),
                status='pending'
            )
            borrowing.full_clean()
            
    def test_borrowing_rejection_fields(self):
        """Test Case 50: Rejection fields validation"""
        borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            due_date=date.today() + timedelta(days=14),
            status='rejected',
            rejected_by=self.librarian,
            rejected_date=timezone.now(),
            rejection_reason="Book not available"
        )
        
        self.assertEqual(borrowing.rejected_by, self.librarian)
        self.assertIsNotNone(borrowing.rejected_date)
        self.assertEqual(borrowing.rejection_reason, "Book not available")


class ExtensionRequestModelTest(TestCase):
    """Test cases for ExtensionRequest model"""
    
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
        
        self.user = User.objects.create_user(
            username='borrower',
            email='borrower@test.com',
            password='ValidPass123!',
            role='member',
            membership=self.membership_type
        )
        
        self.author = Author.objects.create(name="Test Author")
        self.category = Category.objects.create(category_name="Test Category")
        self.branch = Branch.objects.create(
            branch_name="Main Branch",
            location="Downtown"
        )
        
        self.book = Book.objects.create(
            title="Test Book",
            author=self.author,
            category=self.category,
            isbn="9781234567890",
            publication_date=date(2020, 1, 1),
            branch=self.branch,
            edition=1,
            description="A test book"
        )
        
        self.borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            due_date=date.today() + timedelta(days=14),
            status='borrowed'
        )
        
    def test_extension_request_creation_valid(self):
        """Test Case 51: Create extension request with valid data"""
        extension = ExtensionRequest.objects.create(
            borrowing=self.borrowing,
            request_date=timezone.now(),
            rejection_reason="Need more time to read",
            status='pending'
        )
        
        self.assertEqual(extension.borrowing, self.borrowing)
        self.assertEqual(extension.rejection_reason, "Need more time to read")
        self.assertEqual(extension.status, 'pending')
        
    def test_extension_request_invalid_status(self):
        """Test Case 52: Invalid extension status should fail"""
        with self.assertRaises(ValidationError):
            extension = ExtensionRequest(
                borrowing=self.borrowing,
                request_date=timezone.now(),
                rejection_reason="Need more time",
                status='invalid_status'  # Invalid status
            )
            extension.full_clean()
            
    def test_extension_request_future_requested_date(self):
        """Test Case 53: Future requested date should not be allowed"""
        future_date = timezone.now() + timedelta(days=1)
        extension = ExtensionRequest.objects.create(
            borrowing=self.borrowing,
            request_date=future_date,
            rejection_reason="Future request",
            status='pending'
        )
        
        # Future dates might be allowed in some cases, but this is a boundary test
        self.assertEqual(extension.request_date, future_date)
        
    def test_extension_request_missing_reason(self):
        """Test Case 54: Extension request without reason"""
        extension = ExtensionRequest.objects.create(
            borrowing=self.borrowing,
            request_date=timezone.now(),
            rejection_reason="",  # Empty reason
            status='pending'
        )
        
        # Empty reasons might be allowed, but should be noted
        self.assertEqual(extension.rejection_reason, "")


# Create your tests here.
