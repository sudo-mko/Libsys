from django.test import TestCase, Client
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.urls import reverse
from datetime import date, timedelta
from decimal import Decimal
from .models import Fine
from users.models import User, MembershipType
from library.models import Book, Author, Category
from branches.models import Branch
from borrow.models import Borrowing


class FineModelTest(TestCase):
    """Test cases for Fine model including validation and business logic"""
    
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
            due_date=date.today() - timedelta(days=5),  # Overdue
            status='borrowed'
        )
        
    def test_fine_creation_valid(self):
        """Test Case 158: Create fine with valid data"""
        fine = Fine.objects.create(
            borrowing=self.borrowing,
            amount=Decimal('5.00'),
            days_overdue=5,
            fine_type='overdue'
        )
        
        self.assertEqual(fine.borrowing, self.borrowing)
        self.assertEqual(fine.amount, Decimal('5.00'))
        self.assertEqual(fine.days_overdue, 5)
        self.assertEqual(fine.fine_type, 'overdue')
        self.assertFalse(fine.paid)
        
    def test_fine_negative_amount(self):
        """Test Case 159: Negative fine amount should fail validation"""
        with self.assertRaises(ValidationError):
            fine = Fine(
                borrowing=self.borrowing,
                amount=Decimal('-5.00'),  # Negative amount
                days_overdue=5,
                fine_type='overdue'
            )
            fine.full_clean()
            
    def test_fine_zero_amount(self):
        """Test Case 160: Zero fine amount should be allowed for zero days overdue"""
        fine = Fine.objects.create(
            borrowing=self.borrowing,
            amount=Decimal('0.00'),  # Zero amount
            days_overdue=0,
            fine_type='overdue'
        )
        
        self.assertEqual(fine.amount, Decimal('0.00'))
        self.assertEqual(fine.days_overdue, 0)
        
    def test_fine_excessive_amount(self):
        """Test Case 161: Very large fine amount boundary test"""
        fine = Fine.objects.create(
            borrowing=self.borrowing,
            amount=Decimal('9999.99'),  # Very large amount
            days_overdue=100,
            fine_type='overdue'
        )
        
        self.assertEqual(fine.amount, Decimal('9999.99'))
        
    def test_fine_invalid_type(self):
        """Test Case 162: Invalid fine type should fail validation"""
        with self.assertRaises(ValidationError):
            fine = Fine(
                borrowing=self.borrowing,
                amount=Decimal('5.00'),
                days_overdue=5,
                fine_type='invalid_type'  # Invalid type
            )
            fine.full_clean()
            
    def test_fine_negative_days_overdue(self):
        """Test Case 163: Negative days overdue should fail validation"""
        with self.assertRaises(ValidationError):
            fine = Fine(
                borrowing=self.borrowing,
                amount=Decimal('5.00'),
                days_overdue=-1,  # Negative days
                fine_type='overdue'
            )
            fine.full_clean()
            
    def test_fine_large_days_overdue(self):
        """Test Case 164: Very large days overdue boundary test"""
        fine = Fine.objects.create(
            borrowing=self.borrowing,
            amount=Decimal('100.00'),
            days_overdue=999999,  # Very large number
            fine_type='overdue'
        )
        
        self.assertEqual(fine.days_overdue, 999999)
        
    def test_fine_payment_status(self):
        """Test Case 165: Fine payment status functionality"""
        fine = Fine.objects.create(
            borrowing=self.borrowing,
            amount=Decimal('5.00'),
            days_overdue=5,
            fine_type='overdue'
        )
        
        # Initially unpaid
        self.assertFalse(fine.paid)
        self.assertIsNone(fine.paid_at)
        
        # Mark as paid
        fine.paid = True
        fine.paid_at = timezone.now()
        fine.save()
        
        self.assertTrue(fine.paid)
        self.assertIsNotNone(fine.paid_at)
        
    def test_fine_created_at_auto_set(self):
        """Test Case 166: Fine created_at should be auto-set"""
        fine = Fine.objects.create(
            borrowing=self.borrowing,
            amount=Decimal('5.00'),
            days_overdue=5,
            fine_type='overdue'
        )
        
        self.assertIsNotNone(fine.created_at)
        self.assertIsInstance(fine.created_at, timezone.datetime)
        
    def test_fine_missing_required_fields(self):
        """Test Case 167: Missing required fields should fail"""
        with self.assertRaises(ValidationError):
            fine = Fine(
                # Missing borrowing, amount, days_overdue, fine_type
            )
            fine.full_clean()
            
    def test_fine_different_types(self):
        """Test Case 168: Test all fine types"""
        fine_types = ['overdue', 'damaged']
        
        for fine_type in fine_types:
            fine = Fine.objects.create(
                borrowing=self.borrowing,
                amount=Decimal('5.00'),
                days_overdue=5,
                fine_type=fine_type
            )
            
            self.assertEqual(fine.fine_type, fine_type)
            
    def test_fine_decimal_precision(self):
        """Test Case 169: Fine amount decimal precision"""
        fine = Fine.objects.create(
            borrowing=self.borrowing,
            amount=Decimal('5.55'),  # Decimal with cents
            days_overdue=5,
            fine_type='overdue'
        )
        
        self.assertEqual(fine.amount, Decimal('5.55'))
        
    def test_fine_string_representation(self):
        """Test Case 170: Fine string representation"""
        fine = Fine.objects.create(
            borrowing=self.borrowing,
            amount=Decimal('5.00'),
            days_overdue=5,
            fine_type='overdue'
        )
        
        expected_str = f"Fine for {str(self.borrowing)} - Overdue Fine: 5.00 MVR"
        self.assertEqual(str(fine), expected_str)


class FineCalculationTest(TestCase):
    """Test cases for Fine calculation methods"""
    
    def test_calculate_overdue_fine_zero_days(self):
        """Test Case 171: Calculate overdue fine for zero days"""
        fine_amount = Fine.calculate_overdue_fine(0)
        self.assertEqual(fine_amount, Decimal('0.00'))
        
    def test_calculate_overdue_fine_negative_days(self):
        """Test Case 172: Calculate overdue fine for negative days"""
        fine_amount = Fine.calculate_overdue_fine(-5)
        self.assertEqual(fine_amount, Decimal('0.00'))
        
    def test_calculate_overdue_fine_1_day(self):
        """Test Case 173: Calculate overdue fine for 1 day"""
        fine_amount = Fine.calculate_overdue_fine(1)
        self.assertEqual(fine_amount, Decimal('2.00'))
        
    def test_calculate_overdue_fine_3_days(self):
        """Test Case 174: Calculate overdue fine for 3 days"""
        fine_amount = Fine.calculate_overdue_fine(3)
        self.assertEqual(fine_amount, Decimal('6.00'))
        
    def test_calculate_overdue_fine_5_days(self):
        """Test Case 175: Calculate overdue fine for 5 days (4-7 day range)"""
        fine_amount = Fine.calculate_overdue_fine(5)
        # First 3 days: 3 * 2 = 6, Next 2 days: 2 * 5 = 10, Total: 16
        self.assertEqual(fine_amount, Decimal('16.00'))
        
    def test_calculate_overdue_fine_7_days(self):
        """Test Case 176: Calculate overdue fine for 7 days"""
        fine_amount = Fine.calculate_overdue_fine(7)
        # First 3 days: 3 * 2 = 6, Next 4 days: 4 * 5 = 20, Total: 26
        self.assertEqual(fine_amount, Decimal('26.00'))
        
    def test_calculate_overdue_fine_10_days(self):
        """Test Case 177: Calculate overdue fine for 10 days (8+ day range)"""
        fine_amount = Fine.calculate_overdue_fine(10)
        # First 3 days: 3 * 2 = 6, Next 4 days: 4 * 5 = 20, Remaining 3 days: 3 * 10 = 30, Total: 56
        self.assertEqual(fine_amount, Decimal('56.00'))
        
    def test_calculate_overdue_fine_large_number(self):
        """Test Case 178: Calculate overdue fine for very large number"""
        fine_amount = Fine.calculate_overdue_fine(100)
        # First 3 days: 3 * 2 = 6, Next 4 days: 4 * 5 = 20, Remaining 93 days: 93 * 10 = 930, Total: 956
        self.assertEqual(fine_amount, Decimal('956.00'))
        
    def test_calculate_damaged_fine_zero_price(self):
        """Test Case 179: Calculate damaged fine for zero price book"""
        fine_amount = Fine.calculate_damaged_fine(0)
        self.assertEqual(fine_amount, Decimal('50.00'))
        
    def test_calculate_damaged_fine_positive_price(self):
        """Test Case 180: Calculate damaged fine for positive price book"""
        fine_amount = Fine.calculate_damaged_fine(25.50)
        self.assertEqual(fine_amount, Decimal('75.50'))
        
    def test_calculate_damaged_fine_large_price(self):
        """Test Case 181: Calculate damaged fine for expensive book"""
        fine_amount = Fine.calculate_damaged_fine(100.00)
        self.assertEqual(fine_amount, Decimal('150.00'))
        
    def test_calculate_damaged_fine_decimal_price(self):
        """Test Case 182: Calculate damaged fine for decimal price"""
        fine_amount = Fine.calculate_damaged_fine(12.75)
        self.assertEqual(fine_amount, Decimal('62.75'))


class FineBusinessLogicTest(TestCase):
    """Test cases for Fine business logic and calculations"""
    
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
        
    def test_overdue_fine_calculation(self):
        """Test Case 183: Overdue fine calculation"""
        # Create borrowing that's 5 days overdue
        borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            due_date=date.today() - timedelta(days=5),
            status='borrowed'
        )
        
        # Calculate fine for 5 days overdue
        overdue_days = 5
        expected_fine = Fine.calculate_overdue_fine(overdue_days)
        
        fine = Fine.objects.create(
            borrowing=borrowing,
            amount=expected_fine,
            days_overdue=overdue_days,
            fine_type='overdue'
        )
        
        self.assertEqual(fine.amount, Decimal('16.00'))  # 3*2 + 2*5 = 16
        
    def test_damage_fine_calculation(self):
        """Test Case 184: Damage fine calculation"""
        borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            due_date=date.today() + timedelta(days=5),
            status='borrowed'
        )
        
        # Damage fine is book price + 50 MVR processing fee
        book_price = 25.00
        damage_fine = Fine.calculate_damaged_fine(book_price)
        
        fine = Fine.objects.create(
            borrowing=borrowing,
            amount=damage_fine,
            days_overdue=0,
            fine_type='damaged'
        )
        
        self.assertEqual(fine.amount, Decimal('75.00'))  # 25 + 50
        
    def test_multiple_fines_for_user(self):
        """Test Case 185: Multiple fines for same user"""
        # Create multiple borrowings
        borrowing1 = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            due_date=date.today() - timedelta(days=3),
            status='borrowed'
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
            due_date=date.today() - timedelta(days=7),
            status='borrowed'
        )
        
        # Create fines for both borrowings
        fine1 = Fine.objects.create(
            borrowing=borrowing1,
            amount=Fine.calculate_overdue_fine(3),
            days_overdue=3,
            fine_type='overdue'
        )
        
        fine2 = Fine.objects.create(
            borrowing=borrowing2,
            amount=Fine.calculate_overdue_fine(7),
            days_overdue=7,
            fine_type='overdue'
        )
        
        # Verify both fines exist
        user_fines = Fine.objects.filter(borrowing__user=self.user)
        self.assertEqual(user_fines.count(), 2)
        
        # Verify total amount
        total_amount = sum(fine.amount for fine in user_fines)
        self.assertEqual(total_amount, Decimal('32.00'))  # 6 + 26
        
    def test_fine_payment_workflow(self):
        """Test Case 186: Complete fine payment workflow"""
        borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            due_date=date.today() - timedelta(days=5),
            status='borrowed'
        )
        
        fine = Fine.objects.create(
            borrowing=borrowing,
            amount=Fine.calculate_overdue_fine(5),
            days_overdue=5,
            fine_type='overdue'
        )
        
        # Initially unpaid
        self.assertFalse(fine.paid)
        self.assertIsNone(fine.paid_at)
        
        # Mark as paid
        fine.paid = True
        fine.paid_at = timezone.now()
        fine.save()
        
        # Verify payment
        self.assertTrue(fine.paid)
        self.assertIsNotNone(fine.paid_at)
        
    def test_fine_statistics(self):
        """Test Case 187: Fine statistics calculation"""
        # Create multiple fines with different statuses
        borrowing1 = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            due_date=date.today() - timedelta(days=5),
            status='borrowed'
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
            due_date=date.today() - timedelta(days=3),
            status='borrowed'
        )
        
        # Create paid and unpaid fines
        paid_fine = Fine.objects.create(
            borrowing=borrowing1,
            amount=Fine.calculate_overdue_fine(5),
            days_overdue=5,
            fine_type='overdue',
            paid=True,
            paid_at=timezone.now()
        )
        
        unpaid_fine = Fine.objects.create(
            borrowing=borrowing2,
            amount=Fine.calculate_overdue_fine(3),
            days_overdue=3,
            fine_type='overdue',
            paid=False
        )
        
        # Calculate statistics
        total_fines = Fine.objects.count()
        paid_fines = Fine.objects.filter(paid=True).count()
        unpaid_fines = Fine.objects.filter(paid=False).count()
        total_amount = sum(fine.amount for fine in Fine.objects.all())
        paid_amount = sum(fine.amount for fine in Fine.objects.filter(paid=True))
        unpaid_amount = sum(fine.amount for fine in Fine.objects.filter(paid=False))
        
        self.assertEqual(total_fines, 2)
        self.assertEqual(paid_fines, 1)
        self.assertEqual(unpaid_fines, 1)
        self.assertEqual(total_amount, Decimal('22.00'))  # 16 + 6
        self.assertEqual(paid_amount, Decimal('16.00'))
        self.assertEqual(unpaid_amount, Decimal('6.00'))
        
    def test_fine_boundary_conditions(self):
        """Test Case 188: Fine boundary conditions"""
        # Test maximum fine amount (9999.99)
        borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            due_date=date.today() - timedelta(days=5),
            status='borrowed'
        )
        
        fine = Fine.objects.create(
            borrowing=borrowing,
            amount=Decimal('9999.99'),
            days_overdue=1000,
            fine_type='overdue'
        )
        
        self.assertEqual(fine.amount, Decimal('9999.99'))
        
        # Test zero fine
        fine_zero = Fine.objects.create(
            borrowing=borrowing,
            amount=Decimal('0.00'),
            days_overdue=0,
            fine_type='overdue'
        )
        
        self.assertEqual(fine_zero.amount, Decimal('0.00'))
        
    def test_fine_type_validation(self):
        """Test Case 189: Fine type validation"""
        borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            due_date=date.today() - timedelta(days=5),
            status='borrowed'
        )
        
        # Test valid fine types
        valid_types = ['overdue', 'damaged']
        for fine_type in valid_types:
            fine = Fine.objects.create(
                borrowing=borrowing,
                amount=Decimal('5.00'),
                days_overdue=5,
                fine_type=fine_type
            )
            self.assertEqual(fine.fine_type, fine_type)
            
    def test_fine_created_at_timestamp(self):
        """Test Case 190: Fine created_at timestamp accuracy"""
        borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            due_date=date.today() - timedelta(days=5),
            status='borrowed'
        )
        
        before_creation = timezone.now()
        fine = Fine.objects.create(
            borrowing=borrowing,
            amount=Decimal('5.00'),
            days_overdue=5,
            fine_type='overdue'
        )
        after_creation = timezone.now()
        
        self.assertGreaterEqual(fine.created_at, before_creation)
        self.assertLessEqual(fine.created_at, after_creation)


# Create your tests here.
