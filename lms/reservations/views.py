from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from .models import Reservation
from library.models import Book
from borrow.models import Borrowing

# Create your views here.
@login_required
def reservation_list(request):
    # Check if user is librarian
    if request.user.role != 'librarian':
        messages.error(request, "Access denied. Only librarians can view reservations.")
        return redirect('library:home')
    
    reservations = Reservation.objects.all().order_by('-created_at') # type: ignore
    
    # Pagination
    paginator = Paginator(reservations, 10)  # 10 reservations per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'reservation_list.html', {'reservations': page_obj})

@login_required
def approve_reservation_confirm(request, reservation_id):
    # Check if user is librarian
    if request.user.role != 'librarian':
        return HttpResponse(b'<div class="text-red-600">Access denied.</div>')
    
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    # If it's an HTMX request, return just the modal content
    if request.headers.get('HX-Request'):
        return render(request, 'reservation_approve_confirm.html', {'reservation': reservation})
    
    # For regular requests, redirect to reservation list (fallback)
    return redirect('reservations:reservation_list')

@login_required
@require_POST
@csrf_protect
def approve_reservation(request, reservation_id):
    # Check if user is librarian
    if request.user.role != 'librarian':
        return HttpResponse(b'<div class="text-red-600">Access denied.</div>')
    
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    if reservation.status != 'pending':
        return HttpResponse(b'<div class="text-red-600">Only pending reservations can be approved.</div>')
    
    reservation.status = 'confirmed'
    reservation.save()
    
    # If it's an HTMX request, return the success template
    if request.headers.get('HX-Request'):
        return render(request, 'reservation_approve_success.html', {'reservation': reservation})
    
    # Otherwise, redirect normally
    return redirect('reservations:reservation_list')

@login_required
def expire_reservation_confirm(request, reservation_id):
    # Check if user is librarian
    if request.user.role != 'librarian':
        return HttpResponse(b'<div class="text-red-600">Access denied.</div>')
    
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    # If it's an HTMX request, return just the modal content
    if request.headers.get('HX-Request'):
        return render(request, 'reservation_expire_confirm.html', {'reservation': reservation})
    
    # For regular requests, redirect to reservation list (fallback)
    return redirect('reservations:reservation_list')

@login_required
@require_POST
@csrf_protect
def mark_expired(request, reservation_id):
    # Check if user is librarian
    if request.user.role != 'librarian':
        return HttpResponse(b'<div class="text-red-600">Access denied.</div>')
    
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    if reservation.status != 'confirmed':
        return HttpResponse(b'<div class="text-red-600">Only confirmed reservations can be marked as expired.</div>')
    
    reservation.status = 'expired'
    reservation.save()
    
    # If it's an HTMX request, return the success template
    if request.headers.get('HX-Request'):
        return render(request, 'reservation_expire_success.html', {'reservation': reservation})
    
    # Otherwise, redirect normally
    return redirect('reservations:reservation_list')

# Keep the existing reserve_book function as is
@login_required
def reserve_book(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    
    # Main check: Does user already have a reservation for this book?
    existing_reservation = Reservation.objects.filter( # type: ignore
        user=request.user, 
        book=book,
        status__in=['pending', 'confirmed']
    ).first()
    
    if existing_reservation:
        messages.error(request, "You have already requested a reservation for this book.")
        return redirect('library:book_detail', book_id=book_id)
    
    # Create new reservation
    reservation = Reservation.objects.create( # type: ignore
        user=request.user,
        book=book,
        status='pending',
        type='regular'
    )
    
    messages.success(request, f"Successfully reserved '{book.title}'. Your reservation is pending approval.")
    return redirect('library:book_detail', book_id=book_id)

@login_required
def user_reservations(request):
    # Get reservations for the current user, ordered by created_at (newest first)
    reservations = Reservation.objects.filter(user=request.user).order_by('-created_at')  # type: ignore
    return render(request, 'user_reservations.html', {'reservations': reservations})

@login_required
@require_POST
@csrf_protect
def cancel_reservation(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    # Check if the reservation belongs to the current user
    if reservation.user != request.user:
        messages.error(request, "You can only cancel your own reservations.")
        return redirect('reservations:user_reservations')
    
    # Check if the reservation is still pending
    if reservation.status != 'pending':
        messages.error(request, "Only pending reservations can be cancelled.")
        return redirect('reservations:user_reservations')
    
    # Delete the reservation
    book_title = reservation.book.title
    reservation.delete()
    
    messages.success(request, f"Successfully cancelled reservation for '{book_title}'.")
    return redirect('reservations:user_reservations')


@login_required
def reject_reservation_confirm(request, reservation_id):
    # Check if user is librarian
    if request.user.role != 'librarian':
        return HttpResponse(b'<div class="text-red-600">Access denied.</div>')
    
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    # If it's an HTMX request, return just the modal content
    if request.headers.get('HX-Request'):
        return render(request, 'reservation_reject_confirm.html', {'reservation': reservation})
    
    # For regular requests, redirect to reservation list (fallback)
    return redirect('reservations:reservation_list')

@login_required
@require_POST
@csrf_protect
def reject_reservation(request, reservation_id):
    # Check if user is librarian
    if request.user.role != 'librarian':
        return HttpResponse(b'<div class="text-red-600">Access denied.</div>')
    
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    if reservation.status != 'pending':
        return HttpResponse(b'<div class="text-red-600">Only pending reservations can be rejected.</div>')
    
    reservation.status = 'rejected'
    reservation.save()
    
    # If it's an HTMX request, return the success template
    if request.headers.get('HX-Request'):
        return render(request, 'reservation_reject_success.html', {'reservation': reservation})
    
    # Otherwise, redirect normally
    return redirect('reservations:reservation_list')