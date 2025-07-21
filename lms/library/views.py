from django.shortcuts import render, get_object_or_404
from .models import Book
from .forms import BookForm
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from borrow.models import Borrowing
from reservations.models import Reservation

# Create your views here.
def index(request):
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
        # Check if current user has borrowed this book
        user_borrowed = Borrowing.objects.filter( # type: ignore
            user=request.user, 
            book=book, 
            status__in=['borrowed', 'overdue']
        ).exists()
        
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
    
    context = {
        'book': book,
        'user_borrowed': user_borrowed,
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