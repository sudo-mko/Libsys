from django.shortcuts import render, get_object_or_404
from .models import Book
from .forms import BookForm
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from borrow.models import Borrowing
from reservations.models import Reservation
from django.db.models import Q
from django.http import JsonResponse
from django.urls import reverse

# Create your views here.
def index(request):
    # Redirect admin users to admin dashboard
    if request.user.is_authenticated and request.user.role in ['admin', 'manager']:
        return redirect(reverse('admin_dashboard:dashboard'))
    
    books = Book.objects.all() # type: ignore
    context = {
        'books': books
    }
    return render(request, 'index.html', context)

def book_detail(request, book_id):
    book = Book.objects.get(id=book_id) # type: ignore
    
    # Check borrowing status
    user_borrowed = False
    book_available = True
    
    if request.user.is_authenticated:
        # Check if current user has any active request/borrowing for this book
        user_borrowing_status = Borrowing.objects.filter( # type: ignore
            user=request.user, 
            book=book, 
            status__in=['pending', 'approved', 'borrowed', 'overdue']
        ).first()
        
        user_borrowed = user_borrowing_status and user_borrowing_status.status in ['borrowed', 'overdue']
        user_has_pending = user_borrowing_status and user_borrowing_status.status == 'pending'
        user_has_approved = user_borrowing_status and user_borrowing_status.status == 'approved'
        
        # Check if book is available (not borrowed by anyone)
        book_available = not Borrowing.objects.filter( # type: ignore
            book=book, 
            status__in=['borrowed', 'overdue']
        ).exists()

          # Check if user already has a reservation for this book
        # Import Reservation model at the top of the file
        from reservations.models import Reservation
        user_has_reservation = Reservation.objects.filter( # type: ignore
            user=request.user,
            book=book,
            status__in=['pending', 'confirmed']
        ).exists()
    else:
        user_borrowed = False
        user_has_pending = False 
        user_has_approved = False
        user_borrowing_status = None
        user_has_reservation = False
    
    context = {
        'book': book,
        'user_borrowed': user_borrowed,
        'user_has_pending': user_has_pending,
        'user_has_approved': user_has_approved,
        'user_borrowing_status': user_borrowing_status,
        'book_available': book_available,
        'user_has_reservation': user_has_reservation,
        'is_member': request.user.is_authenticated and request.user.role == 'member'
    }
    return render(request, 'librarian/book_detail.html', context)


def book_add(request):
    books = Book.objects.all() # type: ignore
    paginator = Paginator(books, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    form = BookForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        form.save()
        return redirect('library:home')
    context = {'form': form, 'books': page_obj}    
    return render(request, 'librarian/book_create.html', context)



def book_update(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES, instance=book)
        if form.is_valid():
            book = form.save()
            # If it's an HTMX request, return the success template
            if request.headers.get('HX-Request'):
                return render(request, 'librarian/book_update_success.html', {'book': book})
            # Otherwise, redirect normally
            return redirect('library:book_add')
        else:
            # If form is invalid and it's HTMX, return the form with errors
            if request.headers.get('HX-Request'):
                return render(request, 'librarian/book_update_modal.html', {'form': form, 'book': book})
    
    # For GET requests
    form = BookForm(instance=book)
    
    # If it's an HTMX request, return just the modal content
    if request.headers.get('HX-Request'):
        return render(request, 'librarian/book_update_modal.html', {'form': form, 'book': book})
    
    # For regular requests, render the full page (fallback)
    context = {'form': form, 'book': book}
    return render(request, 'librarian/book_update.html', context)

def book_delete(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    
    if request.method == 'POST':
        # User confirmed deletion
        book_title = book.title
        book.delete()
        
        # If it's an HTMX request, return the success message
        if request.headers.get('HX-Request'):
            return render(request, 'librarian/book_delete_success.html', {'book_title': book_title})
        # Otherwise, redirect normally
        return redirect('library:book_add')
    
    # For GET requests, show confirmation modal
    if request.headers.get('HX-Request'):
        return render(request, 'librarian/book_delete_confirm.html', {'book': book})
    
    # For regular requests, redirect to book list (fallback)
    return redirect('library:book_add')

def book_search(request):
    """
    Real-time search view for books using HTMX
    Searches across title, author, category, description, and ISBN
    """
    query = request.GET.get('q', '').strip()
    
    if not query or len(query) < 2:
        # Return empty results for queries less than 2 characters
        return render(request, 'components/search_results.html', {'books': []})
    
    # Search across multiple fields using Q objects
    search_results = Book.objects.filter( # type: ignore
        Q(title__icontains=query) |
        Q(author__name__icontains=query) |
        Q(category__category_name__icontains=query) |
        Q(description__icontains=query) |
        Q(isbn__icontains=query)
    ).select_related('author', 'category').distinct()[:8]  # Limit to top 8 results
    
    return render(request, 'components/search_results.html', {'books': search_results, 'query': query})


@login_required
def reports(request):
    # Check if user has permission to view reports (manager or librarian)
    if request.user.role not in ['manager', 'librarian']:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("You don't have permission to view reports.")
    from users.models import User, MembershipType
    from borrow.models import Borrowing
    from reservations.models import Reservation
    from fines.models import Fine
    from django.db.models import Count, Sum, Case, When, DecimalField, Value
    from decimal import Decimal
    
    # Total Books
    total_books = Book.objects.count()
    
    # Total Members (users with role='member')
    total_members = User.objects.filter(role='member').count()
    
    # Members by membership type
    membership_stats = User.objects.filter(role='member').values(
        'membership__name'
    ).annotate(
        count=Count('id')
    ).order_by('membership__name')
    
    # Prepare membership data with fees
    membership_breakdown = []
    total_fees_collected = Decimal('0.00')
    
    # Define annual fees
    annual_fees = {
        'Premium Member': Decimal('750.00'),
        'Basic Member': Decimal('500.00'), 
        'Student Member': Decimal('300.00')
    }
    
    for stat in membership_stats:
        membership_name = stat['membership__name']
        count = stat['count']
        
        if membership_name in annual_fees:
            annual_fee = annual_fees[membership_name]
            total_fee = annual_fee * count
            total_fees_collected += total_fee
            
            membership_breakdown.append({
                'name': membership_name,
                'count': count,
                'annual_fee': annual_fee,
                'total_fee': total_fee
            })
    
    # Total Borrowings
    total_borrowings = Borrowing.objects.count()
    
    # Total Reservations
    total_reservations = Reservation.objects.count()
    
    # Books not returned yet (borrowed or overdue status)
    books_not_returned = Borrowing.objects.filter(
        status__in=['borrowed', 'overdue']
    ).count()
    
    # Books with fines
    books_fined = Fine.objects.values('borrowing').distinct().count()
    
    # Additional useful stats
    pending_requests = Borrowing.objects.filter(status='pending').count()
    overdue_books = Borrowing.objects.filter(status='overdue').count()
    total_fine_amount = Fine.objects.filter(paid=False).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')
    
    # Recent activity (last 30 days)
    from datetime import datetime, timedelta
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    recent_borrowings = Borrowing.objects.filter(
        borrow_date__gte=thirty_days_ago
    ).count()
    
    recent_reservations = Reservation.objects.filter(
        created_at__gte=thirty_days_ago
    ).count()
    
    context = {
        'total_books': total_books,
        'total_members': total_members,
        'membership_breakdown': membership_breakdown,
        'total_fees_collected': total_fees_collected,
        'total_borrowings': total_borrowings,
        'total_reservations': total_reservations,
        'books_not_returned': books_not_returned,
        'books_fined': books_fined,
        'pending_requests': pending_requests,
        'overdue_books': overdue_books,
        'total_fine_amount': total_fine_amount,
        'recent_borrowings': recent_borrowings,
        'recent_reservations': recent_reservations,
    }
    
    return render(request, 'manager/reports.html', context)