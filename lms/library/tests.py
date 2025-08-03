from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date, timedelta
from .models import Author, Category, Book
from branches.models import Branch


class AuthorModelTest(TestCase):
    """Test cases for Author model"""
    
    def test_author_creation_valid(self):
        """Test Case 23: Create author with valid name"""
        author = Author.objects.create(name="J.K. Rowling")
        self.assertEqual(author.name, "J.K. Rowling")
        self.assertEqual(str(author), "J.K. Rowling")
        
    def test_author_name_max_length(self):
        """Test Case 24: Author name exceeding max length should fail"""
        with self.assertRaises(ValidationError):
            author = Author(name="A" * 101)  # Exceeds max_length=100
            author.full_clean()
            
    def test_author_empty_name(self):
        """Test Case 25: Empty author name should fail"""
        with self.assertRaises(ValidationError):
            author = Author(name="")
            author.full_clean()


class CategoryModelTest(TestCase):
    """Test cases for Category model"""
    
    def test_category_creation_valid(self):
        """Test Case 26: Create category with valid name"""
        category = Category.objects.create(category_name="Science Fiction")
        self.assertEqual(category.category_name, "Science Fiction")
        self.assertEqual(str(category), "Science Fiction")
        
    def test_category_name_max_length(self):
        """Test Case 27: Category name exceeding max length should fail"""
        with self.assertRaises(ValidationError):
            category = Category(category_name="C" * 101)  # Exceeds max_length=100
            category.full_clean()
            
    def test_category_empty_name(self):
        """Test Case 28: Empty category name should fail"""
        with self.assertRaises(ValidationError):
            category = Category(category_name="")
            category.full_clean()


class BookModelTest(TestCase):
    """Test cases for Book model"""
    
    def setUp(self):
        """Set up test data"""
        self.author = Author.objects.create(name="Test Author")
        self.category = Category.objects.create(category_name="Test Category")
        self.branch = Branch.objects.create(
            branch_name="Main Branch",
            location="Downtown"
        )
        
    def test_book_creation_valid(self):
        """Test Case 29: Create book with all valid data"""
        book = Book.objects.create(
            title="Test Book",
            author=self.author,
            category=self.category,
            isbn="9781234567890",
            publication_date=date(2020, 1, 1),
            branch=self.branch,
            edition=1,
            description="A test book for testing purposes"
        )
        
        self.assertEqual(book.title, "Test Book")
        self.assertEqual(book.author, self.author)
        self.assertEqual(book.isbn, "9781234567890")
        self.assertEqual(str(book), "Test Book")
        
    def test_book_title_max_length(self):
        """Test Case 30: Book title exceeding max length should fail"""
        with self.assertRaises(ValidationError):
            book = Book(
                title="T" * 101,  # Exceeds max_length=100
                author=self.author,
                category=self.category,
                isbn="9781234567890",
                publication_date=date(2020, 1, 1),
                branch=self.branch,
                edition=1,
                description="Test description"
            )
            book.full_clean()
            
    def test_book_isbn_max_length(self):
        """Test Case 31: ISBN exceeding max length should fail"""
        with self.assertRaises(ValidationError):
            book = Book(
                title="Test Book",
                author=self.author,
                category=self.category,
                isbn="1" * 14,  # Exceeds max_length=13
                publication_date=date(2020, 1, 1),
                branch=self.branch,
                edition=1,
                description="Test description"
            )
            book.full_clean()
            
    def test_book_isbn_too_short(self):
        """Test Case 32: ISBN too short should fail validation"""
        with self.assertRaises(ValidationError):
            book = Book(
                title="Test Book",
                author=self.author,
                category=self.category,
                isbn="123",  # Too short for ISBN
                publication_date=date(2020, 1, 1),
                branch=self.branch,
                edition=1,
                description="Test description"
            )
            book.full_clean()
            
    def test_book_duplicate_isbn(self):
        """Test Case 33: Duplicate ISBN should not be allowed"""
        # Create first book
        Book.objects.create(
            title="First Book",
            author=self.author,
            category=self.category,
            isbn="9781234567890",
            publication_date=date(2020, 1, 1),
            branch=self.branch,
            edition=1,
            description="First book"
        )
        
        # Try to create second book with same ISBN
        with self.assertRaises(ValidationError):
            book = Book(
                title="Second Book",
                author=self.author,
                category=self.category,
                isbn="9781234567890",  # Duplicate ISBN
                publication_date=date(2021, 1, 1),
                branch=self.branch,
                edition=1,
                description="Second book"
            )
            book.full_clean()
            
    def test_book_future_publication_date(self):
        """Test Case 34: Future publication date should be allowed but noted"""
        future_date = date.today() + timedelta(days=365)
        book = Book.objects.create(
            title="Future Book",
            author=self.author,
            category=self.category,
            isbn="9781234567891",
            publication_date=future_date,
            branch=self.branch,
            edition=1,
            description="A book from the future"
        )
        
        # Future dates are allowed, but this is a boundary test
        self.assertEqual(book.publication_date, future_date)
        
    def test_book_very_old_publication_date(self):
        """Test Case 35: Very old publication date boundary test"""
        old_date = date(1000, 1, 1)  # Very old date
        book = Book.objects.create(
            title="Ancient Book",
            author=self.author,
            category=self.category,
            isbn="9781234567892",
            publication_date=old_date,
            branch=self.branch,
            edition=1,
            description="An ancient book"
        )
        
        # Very old dates should be allowed
        self.assertEqual(book.publication_date, old_date)
        
    def test_book_negative_edition(self):
        """Test Case 36: Negative edition number should fail"""
        with self.assertRaises(ValidationError):
            book = Book(
                title="Test Book",
                author=self.author,
                category=self.category,
                isbn="9781234567893",
                publication_date=date(2020, 1, 1),
                branch=self.branch,
                edition=-1,  # Negative edition
                description="Test description"
            )
            book.full_clean()
            
    def test_book_zero_edition(self):
        """Test Case 37: Zero edition should fail"""
        with self.assertRaises(ValidationError):
            book = Book(
                title="Test Book",
                author=self.author,
                category=self.category,
                isbn="9781234567894",
                publication_date=date(2020, 1, 1),
                branch=self.branch,
                edition=0,  # Zero edition
                description="Test description"
            )
            book.full_clean()
            
    def test_book_large_edition_number(self):
        """Test Case 38: Very large edition number boundary test"""
        book = Book.objects.create(
            title="Multi-Edition Book",
            author=self.author,
            category=self.category,
            isbn="9781234567895",
            publication_date=date(2020, 1, 1),
            branch=self.branch,
            edition=999999,  # Very large edition number
            description="A book with many editions"
        )
        
        self.assertEqual(book.edition, 999999)
        
    def test_book_empty_title(self):
        """Test Case 39: Empty book title should fail"""
        with self.assertRaises(ValidationError):
            book = Book(
                title="",  # Empty title
                author=self.author,
                category=self.category,
                isbn="9781234567896",
                publication_date=date(2020, 1, 1),
                branch=self.branch,
                edition=1,
                description="Test description"
            )
            book.full_clean()
            
    def test_book_missing_required_fields(self):
        """Test Case 40: Missing required fields should fail"""
        with self.assertRaises(ValidationError):
            book = Book(
                title="Test Book",
                # Missing author, category, branch, etc.
                isbn="9781234567897",
                publication_date=date(2020, 1, 1),
                edition=1,
                description="Test description"
            )
            book.full_clean()


# Create your tests here.
