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
    
    # Check if user has already borrowed this book and not returned it
    existing_borrowing = Borrowing.objects.filter( # type: ignore
        user=request.user, 
        book=book, 
        status__in=['borrowed', 'overdue']
    ).first()
    
    if existing_borrowing:
        messages.error(request, "You have already borrowed this book.")
        return redirect('library:book_detail', book_id=book_id)
    
    # Check if book is already borrowed by someone else
    book_borrowed = Borrowing.objects.filter( # type: ignore
        book=book, 
        status__in=['borrowed', 'overdue']
    ).exists()
    
    if book_borrowed:
        messages.error(request, "This book is currently borrowed. You can reserve it instead.")
        return redirect('library:book_detail', book_id=book_id)
    
    # Create new borrowing record
    borrowing = Borrowing.objects.create( # type: ignore
        user=request.user,
        book=book,
        due_date=timezone.now().date() + timedelta(days=7),
        is_extended=False,
        status='borrowed'
    )
    
    messages.success(request, f"Successfully borrowed '{book.title}'. Due date: {borrowing.due_date}")
    return redirect('library:home')


@login_required
def borrowing_history(request):
    # Get borrowings for the current user, ordered by borrow date (newest first)
    borrowings = Borrowing.objects.filter(user=request.user).order_by('-borrow_date')  # type: ignore
    return render(request, 'borrowing_history.html', {'borrowings': borrowings})


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
    if not request.user.membership or request.user.membership.extension_days <= 0:
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
    extension_days = 7  # Default 7 days extension
    if borrowing.user.membership and borrowing.user.membership.extension_days > 0:
        extension_days = borrowing.user.membership.extension_days
    
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