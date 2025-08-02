from django.db.models.signals import post_save, post_delete, pre_save
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import AuditLog

User = get_user_model()

def get_client_ip(request):
    """Get client IP address from request"""
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        else:
            return request.META.get('REMOTE_ADDR', 'Unknown')
    return 'Unknown'

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Log user login"""
    ip_address = get_client_ip(request)
    try:
        AuditLog.objects.create(
            user=user,
            action='LOGIN_SUCCESS',
            details=f"User logged in from IP: {ip_address}",
            ip_address=ip_address
        )
    except Exception:
        pass

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """Log user logout"""
    if user:
        ip_address = get_client_ip(request)
        try:
            AuditLog.objects.create(
                user=user,
                action='LOGOUT',
                details=f"User logged out from IP: {ip_address}",
                ip_address=ip_address
            )
        except Exception:
            pass

# Log borrowing activities
@receiver(post_save, sender='borrow.Borrowing')
def log_borrowing_activity(sender, instance, created, **kwargs):
    """Log borrowing creation and updates"""
    if created:
        try:
            AuditLog.objects.create(
                user=instance.user,
                action='BOOK_BORROW',
                details=f"Borrowed book: {instance.book.title} (ID: {instance.book.id})"
            )
        except Exception:
            pass
    else:
        # Check if this is a return
        if instance.return_date and not getattr(instance, '_logged_return', False):
            try:
                AuditLog.objects.create(
                    user=instance.user,
                    action='BOOK_RETURN',
                    details=f"Returned book: {instance.book.title} (ID: {instance.book.id})"
                )
                instance._logged_return = True
            except Exception:
                pass

# Log fine activities
@receiver(post_save, sender='fines.Fine')
def log_fine_activity(sender, instance, created, **kwargs):
    """Log fine creation and payment"""
    if created:
        try:
            AuditLog.objects.create(
                user=instance.user,
                action='FINE_CREATE',
                details=f"Fine created: ${instance.amount} for {instance.fine_type}. Reason: {instance.reason}"
            )
        except Exception:
            pass
    else:
        # Check if fine was paid
        if instance.paid and not getattr(instance, '_logged_payment', False):
            try:
                AuditLog.objects.create(
                    user=instance.user,
                    action='FINE_PAID',
                    details=f"Fine paid: ${instance.amount} for {instance.fine_type}"
                )
                instance._logged_payment = True
            except Exception:
                pass

# Log reservation activities
@receiver(post_save, sender='reservations.Reservation')
def log_reservation_activity(sender, instance, created, **kwargs):
    """Log reservation activities"""
    if created:
        try:
            AuditLog.objects.create(
                user=instance.user,
                action='RESERVATION_CREATE',
                details=f"Reserved book: {instance.book.title} (ID: {instance.book.id})"
            )
        except Exception:
            pass
    else:
        # Log status changes
        if hasattr(instance, '_original_status'):
            if instance._original_status != instance.status:
                action_map = {
                    'approved': 'RESERVATION_APPROVE',
                    'rejected': 'RESERVATION_REJECT',
                    'expired': 'RESERVATION_EXPIRE'
                }
                action = action_map.get(instance.status, 'RESERVATION_UPDATE')
                try:
                    AuditLog.objects.create(
                        user=instance.user,
                        action=action,
                        details=f"Reservation {instance.status}: {instance.book.title}"
                    )
                except Exception:
                    pass

@receiver(pre_save, sender='reservations.Reservation')
def track_reservation_status_changes(sender, instance, **kwargs):
    """Track original status for comparison"""
    if instance.pk:
        try:
            original = sender.objects.get(pk=instance.pk)
            instance._original_status = original.status
        except sender.DoesNotExist:
            pass

# Log book management
@receiver(post_save, sender='library.Book')
def log_book_activity(sender, instance, created, **kwargs):
    """Log book creation and updates"""
    # Only log if we have a user context (avoid logging during data migration)
    request = getattr(instance, '_request', None)
    if request and hasattr(request, 'user') and request.user.is_authenticated:
        if created:
            try:
                AuditLog.objects.create(
                    user=request.user,
                    action='BOOK_CREATE',
                    details=f"Created book: {instance.title} by {instance.author}",
                    ip_address=get_client_ip(request)
                )
            except Exception:
                pass
        else:
            try:
                AuditLog.objects.create(
                    user=request.user,
                    action='BOOK_UPDATE',
                    details=f"Updated book: {instance.title} (ID: {instance.id})",
                    ip_address=get_client_ip(request)
                )
            except Exception:
                pass

@receiver(post_delete, sender='library.Book')
def log_book_deletion(sender, instance, **kwargs):
    """Log book deletion"""
    request = getattr(instance, '_request', None)
    if request and hasattr(request, 'user') and request.user.is_authenticated:
        try:
            AuditLog.objects.create(
                user=request.user,
                action='BOOK_DELETE',
                details=f"Deleted book: {instance.title} by {instance.author}",
                ip_address=get_client_ip(request)
            )
        except Exception:
            pass

# Log user management
@receiver(post_save, sender=User)
def log_user_activity(sender, instance, created, **kwargs):
    """Log user creation and updates"""
    request = getattr(instance, '_request', None)
    if request and hasattr(request, 'user') and request.user.is_authenticated:
        if created:
            try:
                AuditLog.objects.create(
                    user=request.user,
                    action='USER_CREATE',
                    details=f"Created user: {instance.username} ({instance.get_role_display()})",
                    ip_address=get_client_ip(request)
                )
            except Exception:
                pass
        else:
            # Check for role changes
            if hasattr(instance, '_original_role') and instance._original_role != instance.role:
                try:
                    AuditLog.objects.create(
                        user=request.user,
                        action='USER_ROLE_CHANGE',
                        details=f"Changed role for {instance.username}: {instance._original_role} → {instance.role}",
                        ip_address=get_client_ip(request)
                    )
                except Exception:
                    pass
            else:
                try:
                    AuditLog.objects.create(
                        user=request.user,
                        action='USER_UPDATE',
                        details=f"Updated user: {instance.username}",
                        ip_address=get_client_ip(request)
                    )
                except Exception:
                    pass

@receiver(pre_save, sender=User)
def track_user_role_changes(sender, instance, **kwargs):
    """Track original role for comparison"""
    if instance.pk:
        try:
            original = sender.objects.get(pk=instance.pk)
            instance._original_role = original.role
        except sender.DoesNotExist:
            pass

@receiver(post_delete, sender=User)
def log_user_deletion(sender, instance, **kwargs):
    """Log user deletion"""
    request = getattr(instance, '_request', None)
    if request and hasattr(request, 'user') and request.user.is_authenticated:
        try:
            AuditLog.objects.create(
                user=request.user,
                action='USER_DELETE',
                details=f"Deleted user: {instance.username} ({instance.get_role_display()})",
                ip_address=get_client_ip(request)
            )
        except Exception:
            pass