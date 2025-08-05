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
    if request.user.is_authenticated and request.user.role == 'admin':
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


@login_required
def book_add(request):
    # Check if user has permission to manage books (librarian, manager, or admin)
    if request.user.role not in ['librarian', 'manager', 'admin']:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("You don't have permission to manage books.")
    
    books = Book.objects.all().order_by('-id') # type: ignore
    paginator = Paginator(books, 15)  # Show 15 books per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    form = BookForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        form.save()
        return redirect('library:book_add')  # Redirect to same page to see new book
    
    context = {
        'form': form, 
        'books': page_obj,  # Paginated books for iteration
        'page_obj': page_obj  # Page object for pagination controls
    }    
    return render(request, 'librarian/book_create.html', context)



@login_required
def book_update(request, book_id):
    # Check if user has permission to manage books (librarian, manager, or admin)
    if request.user.role not in ['librarian', 'manager', 'admin']:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("You don't have permission to manage books.")
    
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

@login_required
def book_delete(request, book_id):
    # Check if user has permission to manage books (librarian, manager, or admin)
    if request.user.role not in ['librarian', 'manager', 'admin']:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("You don't have permission to manage books.")
    
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

def hsts_demo(request):
    """HSTS demonstration page"""
    from django.http import HttpResponse
    
    # Get current request info
    is_secure = request.is_secure()
    protocol = "HTTPS" if is_secure else "HTTP"
    
    response = HttpResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>HSTS Demo - Library Management System</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background: #f8f9fa; }}
            .container {{ max-width: 800px; margin: 0 auto; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; }}
            .info {{ background: white; padding: 25px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .warning {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 20px; border-radius: 8px; margin: 20px 0; }}
            .success {{ background: #d4edda; border: 1px solid #c3e6cb; padding: 20px; border-radius: 8px; margin: 20px 0; }}
            .status {{ font-size: 18px; font-weight: bold; padding: 10px; border-radius: 5px; }}
            .status.secure {{ background: #d4edda; color: #155724; }}
            .status.insecure {{ background: #f8d7da; color: #721c24; }}
            code {{ background: #f8f9fa; padding: 2px 6px; border-radius: 3px; font-family: monospace; }}
            .test-links {{ margin: 20px 0; }}
            .test-links a {{ display: inline-block; margin: 5px; padding: 10px 15px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; }}
            .test-links a:hover {{ background: #0056b3; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔒 HSTS (HTTP Strict Transport Security) Demo</h1>
                <p>Current Connection: <span class="status {'secure' if is_secure else 'insecure'}">{protocol}</span></p>
            </div>
            
            <div class="info">
                <h2>What is HSTS?</h2>
                <p>HTTP Strict Transport Security (HSTS) is a security policy that helps protect websites against protocol downgrade attacks and cookie hijacking.</p>
                
                <h3>How it works:</h3>
                <ul>
                    <li>When you visit this site over HTTPS, your browser receives an HSTS header</li>
                    <li>The browser remembers this policy for the specified duration (1 hour in this demo)</li>
                    <li>Future requests to this domain will automatically use HTTPS, even if you type "http://"</li>
                    <li>This prevents man-in-the-middle attacks that try to downgrade HTTPS to HTTP</li>
                </ul>
            </div>
            
            <div class="warning">
                <h3>⚠️ Demo Instructions:</h3>
                <p><strong>To test HSTS:</strong></p>
                <ol>
                    <li>First, visit this page over HTTPS (you're doing this now)</li>
                    <li>Accept the security warning (self-signed certificate)</li>
                    <li>Try the test links below to see HSTS in action</li>
                    <li>Your browser should automatically redirect HTTP to HTTPS</li>
                    <li>This demonstrates HSTS preventing downgrade attacks!</li>
                </ol>
            </div>
            
            <div class="test-links">
                <h3>🧪 Test HSTS Protection:</h3>
                <a href="http://127.0.0.1:8443/hsts-demo/" target="_blank">Test HTTP → HTTPS Redirect</a>
                <a href="http://localhost:8443/hsts-demo/" target="_blank">Test localhost HTTP → HTTPS</a>
                <a href="https://127.0.0.1:8443/hsts-demo/" target="_blank">Direct HTTPS Access</a>
            </div>
            
            <div class="info">
                <h3>Current HSTS Settings:</h3>
                <ul>
                    <li><strong>max-age:</strong> 3600 seconds (1 hour)</li>
                    <li><strong>includeSubDomains:</strong> Yes</li>
                    <li><strong>preload:</strong> No (for demo purposes)</li>
                </ul>
            </div>
            
            <div class="success">
                <h3>✅ Security Headers Active:</h3>
                <ul>
                    <li>✅ Strict-Transport-Security</li>
                    <li>✅ Secure Cookies (SESSION_COOKIE_SECURE)</li>
                    <li>✅ Secure CSRF Cookies (CSRF_COOKIE_SECURE)</li>
                    <li>✅ XSS Protection (SECURE_BROWSER_XSS_FILTER)</li>
                    <li>✅ Content Type Sniffing Protection (SECURE_CONTENT_TYPE_NOSNIFF)</li>
                    <li>✅ Frame Options (X_FRAME_OPTIONS)</li>
                    <li>✅ Referrer Policy (SECURE_REFERRER_POLICY)</li>
                </ul>
            </div>
            
            <div class="info">
                <h3>🔍 How to Verify HSTS:</h3>
                <ol>
                    <li>Open browser Developer Tools (F12)</li>
                    <li>Go to Network tab</li>
                    <li>Refresh this page</li>
                    <li>Look for <code>Strict-Transport-Security</code> header in the response</li>
                    <li>You should see: <code>max-age=3600; includeSubDomains</code></li>
                </ol>
            </div>
        </div>
    </body>
    </html>
    """)
    
    # Add HSTS header manually for demo
    # Always add HSTS header for HTTPS demo
    response['Strict-Transport-Security'] = 'max-age=3600; includeSubDomains'
    
    return response