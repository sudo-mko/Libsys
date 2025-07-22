from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse
from datetime import timedelta
from .models import Borrowing, ExtensionRequest
from .forms import BorrowingForm
from library.models import Book
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.utils import timezone
from datetime import timedelta

# Create your views here.
def borrow_list(request):
    borrow = Borrowing.objects.all() # type: ignore
    return render(request, 'borrow_list.html', {'borrow': borrow})


@login_required
def borrow_book(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    
    # Check if user is a member
    if request.user.role != 'member':
        messages.error(request, "Only library members can borrow books.")
        return redirect('library:book_detail', book_id=book_id)
    
    # Check if user has a membership assigned
    if not request.user.membership:
        messages.error(request, "You need to have a membership to borrow books. Please contact a librarian.")
        return redirect('library:book_detail', book_id=book_id)
    
    # Check if user has already borrowed this book and not returned it
    existing_borrowing = Borrowing.objects.filter( # type: ignore
        user=request.user, 
        book=book, 
        status__in=['borrowed', 'overdue']
    ).first()
    
    if existing_borrowing:
        messages.error(request, "You have already borrowed this book.")
        return redirect('library:book_detail', book_id=book_id)
    
    # Check if book is already borrowed by someone else (only check actual borrowed status, not pending/approved)
    book_borrowed = Borrowing.objects.filter( # type: ignore
        book=book, 
        status__in=['borrowed', 'overdue']
    ).exists()
    
    if book_borrowed:
        messages.error(request, "This book is currently borrowed. You can reserve it instead.")
        return redirect('library:book_detail', book_id=book_id)
    
    # Check if user has reached their borrowing limit based on membership
    active_borrowings_count = Borrowing.objects.filter( # type: ignore
        user=request.user,
        status__in=['borrowed', 'overdue'],
        return_date__isnull=True
    ).count()
    
    max_books = request.user.membership.max_books
    if active_borrowings_count >= max_books:
        messages.error(request, f"You have reached your borrowing limit of {max_books} books for your {request.user.membership.name} membership.")
        return redirect('library:book_detail', book_id=book_id)
    
    # Create new borrowing request with pending status
    # Note: due_date will be calculated when librarian approves and user picks up the book
    borrowing = Borrowing.objects.create( # type: ignore
        user=request.user,
        book=book,
        due_date=timezone.now().date(),  # Temporary date, will be updated on pickup
        is_extended=False,
        status='pending'
    )
    
    messages.success(request, f"Borrowing request submitted for '{book.title}'. A librarian will review your request.")
    return redirect('borrow:borrowing_history')


@login_required
def borrowing_history(request):
    # Get borrowings for the current user, ordered by borrow date (newest first)
    borrowings = Borrowing.objects.filter(user=request.user).order_by('-borrow_date')  # type: ignore
    
    # Calculate status for each borrowing
 
    
    today = timezone.now().date()
    enhanced_borrowings = []
    
    for borrowing in borrowings:
        # Create a copy of the borrowing object with additional fields
        enhanced_borrowing = borrowing
        
        # Handle different status types
        if borrowing.status == 'pending':
            enhanced_borrowing.calculated_status = 'pending'
        elif borrowing.status == 'approved':
            # Check if code has expired
            if borrowing.is_code_expired():
                enhanced_borrowing.calculated_status = 'expired'
            else:
                enhanced_borrowing.calculated_status = 'approved'
                enhanced_borrowing.days_until_expiry = borrowing.days_until_code_expiry()
        elif borrowing.status in ['borrowed', 'overdue']:
            days_until_due = (borrowing.due_date - today).days
            
            if days_until_due < 0:
                # Past due date
                enhanced_borrowing.calculated_status = 'overdue'
                enhanced_borrowing.days_overdue = abs(days_until_due)
            elif days_until_due == 0:
                # Due today
                enhanced_borrowing.calculated_status = 'due_today'
            elif days_until_due <= 2:
                # Due within 2 days
                enhanced_borrowing.calculated_status = 'due_soon'
                enhanced_borrowing.days_until_due = days_until_due
            else:
                # More than 2 days away
                enhanced_borrowing.calculated_status = 'borrowed'
                enhanced_borrowing.days_until_due = days_until_due
        else:
            # Returned, expired, or other status
            enhanced_borrowing.calculated_status = borrowing.status
        
        enhanced_borrowings.append(enhanced_borrowing)
    
    return render(request, 'borrowing_history.html', {'borrowings': enhanced_borrowings})


@login_required
@require_POST
@csrf_protect
def request_extension(request, borrowing_id):
    borrowing = get_object_or_404(Borrowing, id=borrowing_id)
    
    # Check if the borrowing belongs to the current user
    if borrowing.user != request.user:
        messages.error(request, "You can only request extensions for your own borrowings.")
        return redirect('borrow:borrowing_history')
    
    # Check if user has premium membership
    if not request.user.membership or request.user.membership.name.lower() != 'premium':
        messages.error(request, "Extension requests are only available for premium members.")
        return redirect('borrow:borrowing_history')
    
    # Check if book is currently borrowed (not overdue or returned)
    if borrowing.status != 'borrowed':
        messages.error(request, "Extension can only be requested for currently borrowed books.")
        return redirect('borrow:borrowing_history')
    
    # Check if already extended
    if borrowing.is_extended:
        messages.error(request, "This book has already been extended.")
        return redirect('borrow:borrowing_history')
    
    # Check if extension request already exists
    existing_request = ExtensionRequest.objects.filter(borrowing=borrowing).first() # type: ignore
    if existing_request:
        messages.error(request, "Extension request already exists for this book.")
        return redirect('borrow:borrowing_history')
    
    # Create extension request
    ExtensionRequest.objects.create(borrowing=borrowing) # type: ignore
    
    messages.success(request, f"Extension request submitted for '{borrowing.book.title}'. A librarian will review your request.")
    return redirect('borrow:borrowing_history')

@login_required
def extension_requests_list(request):
    # Check if user is librarian or admin
    if request.user.role not in ['librarian', 'admin']:
        messages.error(request, "Access denied. Only librarians and admins can view extension requests.")
        return redirect('library:home')
    
    # Get all extension requests, ordered by request date
    extension_requests = ExtensionRequest.objects.select_related('borrowing__user', 'borrowing__book').order_by('-request_date') # type: ignore
    
    return render(request, 'extension_requests_list.html', {'extension_requests': extension_requests})

@login_required
def approve_extension_confirm(request, extension_id):
    # Check if user is librarian or admin
    if request.user.role not in ['librarian', 'admin']:
        return HttpResponse(b'<div class="text-red-600">Access denied.</div>')
    
    extension_request = get_object_or_404(ExtensionRequest, id=extension_id)
    
    # If it's an HTMX request, return just the modal content
    if request.headers.get('HX-Request'):
        return render(request, 'extension_approve_confirm.html', {'extension_request': extension_request})
    
    # For regular requests, redirect to extension requests list (fallback)
    return redirect('borrow:extension_requests_list')

@login_required
@require_POST
@csrf_protect
def approve_extension(request, extension_id):
    # Check if user is librarian or admin
    if request.user.role not in ['librarian', 'admin']:
        if request.headers.get('HX-Request'):
            return HttpResponse(b'<div class="text-red-600">Access denied.</div>')
        messages.error(request, "Access denied.")
        return redirect('library:home')
    
    extension_request = get_object_or_404(ExtensionRequest, id=extension_id)
    
    if extension_request.status != 'pending':
        error_msg = "Only pending extension requests can be approved."
        if request.headers.get('HX-Request'):
            return HttpResponse(f'<div class="text-red-600">{error_msg}</div>'.encode())
        messages.error(request, error_msg)
        return redirect('borrow:extension_requests_list')
    
    # Update borrowing record
    borrowing = extension_request.borrowing
    extension_days = 7  # Fixed 7-day extension for premium members
    
    borrowing.due_date = borrowing.due_date + timedelta(days=extension_days)
    borrowing.is_extended = True
    borrowing.save()
    
    # Update extension request
    extension_request.status = 'approved'
    extension_request.approved_by = request.user
    extension_request.approval_date = timezone.now()
    extension_request.save()
    
    # If it's an HTMX request, return the success template
    if request.headers.get('HX-Request'):
        return render(request, 'extension_approve_success.html', {'extension_request': extension_request})
    
    # Otherwise, redirect normally
    messages.success(request, f"Extension approved for {borrowing.user.username} - {borrowing.book.title}")
    return redirect('borrow:extension_requests_list')

@login_required
@require_POST 
@csrf_protect
def reject_extension(request, extension_id):
    # Check if user is librarian or admin
    if request.user.role not in ['librarian', 'admin']:
        messages.error(request, "Access denied.")
        return redirect('library:home')
    
    extension_request = get_object_or_404(ExtensionRequest, id=extension_id)
    
    if extension_request.status != 'pending':
        messages.error(request, "Only pending extension requests can be rejected.")
        return redirect('borrow:extension_requests_list')
    
    # Get rejection reason from form
    rejection_reason = request.POST.get('rejection_reason', '')
    
    # Update extension request
    extension_request.status = 'rejected'
    extension_request.approved_by = request.user
    extension_request.approval_date = timezone.now()
    extension_request.rejection_reason = rejection_reason
    extension_request.save()
    
    messages.success(request, f"Extension rejected for {extension_request.borrowing.user.username} - {extension_request.borrowing.book.title}")
    return redirect('borrow:extension_requests_list')


@login_required
def pending_requests_list(request):
    """View for librarians to see and manage pending borrowing requests"""
    # Check if user is librarian or admin
    if request.user.role not in ['librarian', 'admin']:
        messages.error(request, "Access denied. Only librarians and admins can view pending requests.")
        return redirect('library:home')
    
    # Get all pending borrowing requests, ordered by request date
    pending_requests = Borrowing.objects.filter(status='pending').select_related('user', 'book').order_by('borrow_date') # type: ignore
    
    return render(request, 'pending_requests_list.html', {'pending_requests': pending_requests})


@login_required
@require_POST
@csrf_protect
def approve_borrowing_request(request, borrowing_id):
    """Approve a pending borrowing request and generate pickup code"""
    # Check if user is librarian or admin
    if request.user.role not in ['librarian', 'admin']:
        messages.error(request, "Access denied.")
        return redirect('library:home')
    
    borrowing = get_object_or_404(Borrowing, id=borrowing_id)
    
    if borrowing.status != 'pending':
        messages.error(request, "Only pending requests can be approved.")
        return redirect('borrow:pending_requests_list')
    
    # Check if book is still available (not borrowed by someone else)
    book_borrowed = Borrowing.objects.filter( # type: ignore
        book=borrowing.book, 
        status__in=['borrowed', 'overdue']
    ).exclude(id=borrowing_id).exists()
    
    if book_borrowed:
        messages.error(request, "This book is currently borrowed by someone else.")
        return redirect('borrow:pending_requests_list')
    
    # Generate pickup code and update status
    borrowing.generate_pickup_code()
    borrowing.status = 'approved'
    borrowing.approved_date = timezone.now()
    borrowing.save()
    
    messages.success(request, f"Request approved for {borrowing.user.username} - {borrowing.book.title}. Pickup code: {borrowing.pickup_code}")
    return redirect('borrow:pending_requests_list')


@login_required
@require_POST
@csrf_protect
def reject_borrowing_request(request, borrowing_id):
    """Reject a pending borrowing request"""
    # Check if user is librarian or admin
    if request.user.role not in ['librarian', 'admin']:
        messages.error(request, "Access denied.")
        return redirect('library:home')
    
    borrowing = get_object_or_404(Borrowing, id=borrowing_id)
    
    if borrowing.status != 'pending':
        messages.error(request, "Only pending requests can be rejected.")
        return redirect('borrow:pending_requests_list')
    
    # Delete the borrowing request (since it was never actually borrowed)
    book_title = borrowing.book.title
    username = borrowing.user.username
    borrowing.delete()
    
    messages.success(request, f"Request rejected for {username} - {book_title}")
    return redirect('borrow:pending_requests_list')


@login_required
def pickup_code_entry(request):
    """View for librarians to enter pickup codes and complete borrowing"""
    # Check if user is librarian or admin
    if request.user.role not in ['librarian', 'admin']:
        messages.error(request, "Access denied. Only librarians and admins can access this page.")
        return redirect('library:home')
    
    if request.method == 'POST':
        pickup_code = request.POST.get('pickup_code', '').strip().upper()
        
        if not pickup_code:
            messages.error(request, "Please enter a pickup code.")
            return render(request, 'pickup_code_entry.html')
        
        try:
            borrowing = Borrowing.objects.get(pickup_code=pickup_code, status='approved') # type: ignore
            
            # Check if code has expired
            if borrowing.is_code_expired():
                borrowing.status = 'expired'
                borrowing.save()
                messages.error(request, f"This pickup code has expired. Code: {pickup_code}")
                return render(request, 'pickup_code_entry.html')
            
            # Calculate proper due date based on membership loan period (from pickup date)
            loan_period_days = borrowing.user.membership.loan_period_days
            pickup_date = timezone.now().date()
            due_date = pickup_date + timedelta(days=loan_period_days)
            
            # Complete the borrowing process
            borrowing.status = 'borrowed'
            borrowing.due_date = due_date
            borrowing.pickup_date = timezone.now()
            borrowing.borrow_date = pickup_date  # Update borrow_date to actual pickup date
            borrowing.pickup_code = None  # Remove code after successful pickup
            borrowing.save()
            
            messages.success(request, f"Book successfully checked out to {borrowing.user.username}. Due date: {due_date}")
            return render(request, 'pickup_code_entry.html', {'success_borrowing': borrowing})
            
        except Borrowing.DoesNotExist:
            messages.error(request, f"Invalid or expired pickup code: {pickup_code}")
            return render(request, 'pickup_code_entry.html')
    
    return render(request, 'pickup_code_entry.html')


@login_required
@require_POST
@csrf_protect
def cancel_borrowing_request(request, borrowing_id):
    """Allow members to cancel their own pending requests"""
    borrowing = get_object_or_404(Borrowing, id=borrowing_id)
    
    # Check if the borrowing belongs to the current user
    if borrowing.user != request.user:
        messages.error(request, "You can only cancel your own borrowing requests.")
        return redirect('borrow:borrowing_history')
    
    # Can only cancel pending requests, not approved ones
    if borrowing.status != 'pending':
        messages.error(request, "You can only cancel pending requests.")
        return redirect('borrow:borrowing_history')
    
    # Delete the borrowing request
    book_title = borrowing.book.title
    borrowing.delete()
    
    messages.success(request, f"Borrowing request cancelled for '{book_title}'.")
    return redirect('borrow:borrowing_history')


def cleanup_expired_codes():
    """Utility function to mark expired pickup codes as expired"""
    from django.utils import timezone
    from datetime import timedelta
    
    expired_borrowings = Borrowing.objects.filter( # type: ignore
        status='approved',
        approved_date__lt=timezone.now() - timedelta(days=3)
    )
    
    count = expired_borrowings.count()
    expired_borrowings.update(status='expired')
    
    return count