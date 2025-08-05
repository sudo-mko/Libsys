from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.conf import settings
from users.models import MembershipType
from .models import SystemSetting, AuditLog
from utils.system_settings import SystemSettingsHelper
from .signals import get_client_ip
from datetime import datetime, timedelta
from django.utils import timezone
from .reports import ReportGenerator, generate_chart_data, export_report_to_csv
from django.http import HttpResponse
import json
from functools import wraps

User = get_user_model()

def parse_date_flexibly(date_string):
    """
    Parse date string in various formats and return datetime object
    """
    if not date_string:
        return None
    
    # List of possible date formats
    date_formats = [
        '%Y-%m-%d',           # 2025-07-03
        '%m/%d/%Y',           # 07/03/2025
        '%m/%d/%y',           # 07/03/25
        '%B %d, %Y',          # July 3, 2025
        '%b %d, %Y',          # Jul 3, 2025
        '%B %d %Y',           # July 3 2025
        '%b %d %Y',           # Jul 3 2025
        '%d %B %Y',           # 3 July 2025
        '%d %b %Y',           # 3 Jul 2025
        '%d/%m/%Y',           # 03/07/2025
        '%Y-%m-%d %H:%M:%S',  # With time
    ]
    
    # Clean up the date string
    date_string = date_string.strip()
    
    # Handle abbreviated months with periods (Aug. -> Aug)
    date_string = date_string.replace('Jan.', 'Jan').replace('Feb.', 'Feb').replace('Mar.', 'Mar')
    date_string = date_string.replace('Apr.', 'Apr').replace('May.', 'May').replace('Jun.', 'Jun')
    date_string = date_string.replace('Jul.', 'Jul').replace('Aug.', 'Aug').replace('Sep.', 'Sep')
    date_string = date_string.replace('Oct.', 'Oct').replace('Nov.', 'Nov').replace('Dec.', 'Dec')
    
    # Try each format until one works
    for date_format in date_formats:
        try:
            return datetime.strptime(date_string, date_format)
        except ValueError:
            continue
    
    # If all formats fail, raise an error with helpful message
    raise ValueError(f"Unable to parse date '{date_string}'. Supported formats include: YYYY-MM-DD, MM/DD/YYYY, Month DD, YYYY")

def log_audit_event(user, action, details, ip_address=None, request=None):
    """
    Utility function to log audit events
    """
    if request and not ip_address:
        # Get IP address from request
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')
    
    try:
        AuditLog.objects.create(
            user=user,
            action=action,
            details=details,
            ip_address=ip_address
        )
    except Exception as e:
        # Don't let audit logging break the application
        print(f"Audit logging failed: {e}")

def audit_view_access(view_name):
    """
    Decorator to automatically log view access
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated:
                log_audit_event(
                    user=request.user,
                    action=f'{view_name.upper()}_ACCESS',
                    details=f"Accessed {view_name}",
                    request=request
                )
            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator

def admin_required(view_func):
    """Decorator to ensure only admin and manager users can access admin views"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role not in ['admin', 'manager']:
            return HttpResponseForbidden("You don't have permission to access admin features.")
        return view_func(request, *args, **kwargs)
    return wrapper

@login_required
@admin_required
def admin_dashboard(request):
    """Main admin dashboard with overview statistics"""
    # Basic statistics
    total_users = User.objects.count()
    total_members = User.objects.filter(role='member').count()
    total_librarians = User.objects.filter(role='librarian').count()
    total_managers = User.objects.filter(role='manager').count()
    
    # Recent activity (last 30 days)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_users = User.objects.filter(created_at__gte=thirty_days_ago).count()
    recent_audit_logs = AuditLog.objects.filter(timestamp__gte=thirty_days_ago).count()
    
    # Account status
    locked_accounts = User.objects.filter(account_locked_until__isnull=False).count()
    active_accounts = User.objects.filter(is_active=True).count()
    
    context = {
        'total_users': total_users,
        'total_members': total_members,
        'total_librarians': total_librarians,
        'total_managers': total_managers,
        'recent_users': recent_users,
        'recent_audit_logs': recent_audit_logs,
        'locked_accounts': locked_accounts,
        'active_accounts': active_accounts,
    }
    
    return render(request, 'admin_dashboard/dashboard.html', context)

@login_required
@admin_required
def manage_users(request):
    """Admin user management interface"""
    # Get search and filter parameters
    search_query = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')
    
    # Base queryset
    users = User.objects.all().order_by('-created_at')
    
    # Apply filters
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    if role_filter:
        users = users.filter(role=role_filter)
    
    if status_filter == 'locked':
        users = users.filter(account_locked_until__isnull=False)
    elif status_filter == 'active':
        users = users.filter(is_active=True, account_locked_until__isnull=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    
    # Pagination
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    user_stats = {
        'total': User.objects.count(),
        'active': User.objects.filter(is_active=True).count(),
        'locked': User.objects.filter(account_locked_until__isnull=False).count(),
        'members': User.objects.filter(role='member').count(),
        'librarians': User.objects.filter(role='librarian').count(),
        'managers': User.objects.filter(role='manager').count(),
        'admins': User.objects.filter(role='admin').count(),
    }
    
    context = {
        'users': page_obj,
        'user_stats': user_stats,
        'search_query': search_query,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'membership_types': MembershipType.objects.all(),
    }
    
    return render(request, 'admin_dashboard/manage_users.html', context)

@login_required
@admin_required
def edit_user(request, user_id):
    """Edit user details and permissions"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        # Update user fields
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        
        # Handle role changes with permission checks
        new_role = request.POST.get('role', user.role)
        if new_role != user.role:
            # Check if current user can assign this role
            if request.user.role == 'admin':
                # Admins can assign any role
                user.role = new_role
            elif request.user.role == 'manager':
                # Managers can only assign member and librarian roles
                if new_role in ['member', 'librarian']:
                    user.role = new_role
                else:
                    messages.error(request, "You don't have permission to assign admin or manager roles.")
            else:
                messages.error(request, "You don't have permission to change user roles.")
        
        user.is_active = request.POST.get('is_active') == 'on'
        
        # Handle membership
        membership_id = request.POST.get('membership')
        if membership_id:
            try:
                membership = MembershipType.objects.get(id=membership_id)
                user.membership = membership
            except MembershipType.DoesNotExist:
                pass
        
        user.save()
        
        # Log the action
        AuditLog.objects.create(
            user=request.user,
            action='USER_UPDATE',
            details=f"Updated user {user.username}",
            ip_address=get_client_ip(request)
        )
        
        messages.success(request, f"User {user.username} updated successfully.")
        return redirect('admin_dashboard:manage_users')
    
    # Filter role choices based on current user's permissions
    if request.user.role == 'admin':
        allowed_roles = User.ROLE_CHOICES
    elif request.user.role == 'manager':
        allowed_roles = [
            ('member', 'Library Member'),
            ('librarian', 'Librarian'),
        ]
    else:
        allowed_roles = []
    
    context = {
        'user_obj': user,
        'membership_types': MembershipType.objects.all(),
        'role_choices': allowed_roles,
    }
    
    return render(request, 'admin_dashboard/edit_user.html', context)

@login_required
@admin_required
def delete_user(request, user_id):
    """Delete a user account"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        username = user.username
        
        # Log the action before deletion
        AuditLog.objects.create(
            user=request.user,
            action='USER_DELETE',
            details=f"Deleted user {username}",
            ip_address=get_client_ip(request)
        )
        
        user.delete()
        messages.success(request, f"User {username} deleted successfully.")
        return redirect('admin_dashboard:manage_users')
    
    context = {'user_obj': user}
    return render(request, 'admin_dashboard/delete_user_confirm.html', context)

@login_required
@admin_required
def system_settings(request):
    """System configuration interface"""
    settings = SystemSetting.objects.all().order_by('key')
    
    if request.method == 'POST':
        setting_key = request.POST.get('key')
        setting_value = request.POST.get('value')
        setting_type = request.POST.get('setting_type', 'text')
        description = request.POST.get('description', '')
        
        if setting_key and setting_value:
            setting, created = SystemSetting.objects.get_or_create(
                key=setting_key,
                defaults={
                    'value': setting_value,
                    'setting_type': setting_type,
                    'description': description,
                    'updated_by': request.user
                }
            )
            
            if not created:
                setting.value = setting_value
                setting.setting_type = setting_type
                setting.description = description
                setting.updated_by = request.user
                setting.save()
            
            # Log the action
            action_type = 'SETTING_UPDATE'
            AuditLog.objects.create(
                user=request.user,
                action=action_type,
                details=f"{'Created' if created else 'Updated'} system setting: {setting_key}",
                ip_address=get_client_ip(request)
            )
            
            # Invalidate cache for this setting
            SystemSettingsHelper.invalidate_cache(setting_key)
            
            messages.success(request, f"Setting '{setting_key}' {'created' if created else 'updated'} successfully.")
            return redirect('admin_dashboard:system_settings')
    
    # Organize settings by category for better UI
    setting_categories = {
        'borrowing': {
            'name': 'Borrowing & Loans',
            'icon': 'fas fa-book',
            'description': 'Settings that control book borrowing behavior',
            'settings': [
                {
                    'key': 'max_books_per_user',
                    'name': 'Max Books Per User',
                    'default': '5',
                    'type': 'number',
                    'description': 'Maximum number of books a user can borrow simultaneously (fallback if membership limits not set)',
                    'min': 1,
                    'max': 50
                },
                {
                    'key': 'max_borrowing_days',
                    'name': 'Default Loan Period',
                    'default': '14',
                    'type': 'number',
                    'description': 'Default number of days for book loans (fallback if membership periods not set)',
                    'min': 1,
                    'max': 365,
                    'unit': 'days'
                },
                {
                    'key': 'pickup_code_expiry_days',
                    'name': 'Pickup Code Expiry',
                    'default': '3',
                    'type': 'number',
                    'description': 'Days before approved borrowing pickup codes expire',
                    'min': 1,
                    'max': 30,
                    'unit': 'days'
                }
            ]
        },
        'fines': {
            'name': 'Fines & Penalties',
            'icon': 'fas fa-dollar-sign',
            'description': 'Configure fine calculation rules and rates',
            'settings': [
                {
                    'key': 'fine_tier_1_days',
                    'name': 'Tier 1 Days',
                    'default': '3',
                    'type': 'number',
                    'description': 'Number of days for tier 1 fine rate (usually 1-3 days)',
                    'min': 1,
                    'max': 30,
                    'unit': 'days'
                },
                {
                    'key': 'fine_tier_1_rate',
                    'name': 'Tier 1 Rate',
                    'default': '2.00',
                    'type': 'decimal',
                    'description': 'Fine amount per day for tier 1 (early overdue)',
                    'min': 0.01,
                    'unit': 'MVR/day'
                },
                {
                    'key': 'fine_tier_2_days',
                    'name': 'Tier 2 Days',
                    'default': '7',
                    'type': 'number',
                    'description': 'Maximum days for tier 2 fine rate (usually 4-7 days)',
                    'min': 1,
                    'max': 30,
                    'unit': 'days'
                },
                {
                    'key': 'fine_tier_2_rate',
                    'name': 'Tier 2 Rate',
                    'default': '5.00',
                    'type': 'decimal',
                    'description': 'Fine amount per day for tier 2 (moderate overdue)',
                    'min': 0.01,
                    'unit': 'MVR/day'
                },
                {
                    'key': 'fine_tier_3_rate',
                    'name': 'Tier 3 Rate',
                    'default': '10.00',
                    'type': 'decimal',
                    'description': 'Fine amount per day for tier 3 (severely overdue, 8+ days)',
                    'min': 0.01,
                    'unit': 'MVR/day'
                },
                {
                    'key': 'damaged_book_processing_fee',
                    'name': 'Damaged Book Fee',
                    'default': '50.00',
                    'type': 'decimal',
                    'description': 'Processing fee added to damaged/lost book replacement cost',
                    'min': 0,
                    'unit': 'MVR'
                }
            ]
        },
        'sessions': {
            'name': 'Session Management',
            'icon': 'fas fa-clock',
            'description': 'Control user session timeouts by role',
            'settings': [
                {
                    'key': 'member_session_timeout_minutes',
                    'name': 'Member Session Timeout',
                    'default': '15',
                    'type': 'number',
                    'description': 'Session timeout for regular library members',
                    'min': 5,
                    'max': 480,
                    'unit': 'minutes'
                },
                {
                    'key': 'librarian_session_timeout_minutes',
                    'name': 'Librarian Session Timeout',
                    'default': '15',
                    'type': 'number',
                    'description': 'Session timeout for librarian users',
                    'min': 5,
                    'max': 480,
                    'unit': 'minutes'
                },
                {
                    'key': 'manager_session_timeout_minutes',
                    'name': 'Manager Session Timeout',
                    'default': '30',
                    'type': 'number',
                    'description': 'Session timeout for manager users',
                    'min': 5,
                    'max': 480,
                    'unit': 'minutes'
                },
                {
                    'key': 'admin_session_timeout_minutes',
                    'name': 'Admin Session Timeout',
                    'default': '30',
                    'type': 'number',
                    'description': 'Session timeout for admin users',
                    'min': 5,
                    'max': 480,
                    'unit': 'minutes'
                }
            ]
        },
        'reservations': {
            'name': 'Reservations',
            'icon': 'fas fa-calendar-check',
            'description': 'Settings for book reservations and holds',
            'settings': [
                {
                    'key': 'reservation_timeout_hours',
                    'name': 'Reservation Expiry',
                    'default': '24',
                    'type': 'number',
                    'description': 'Hours before confirmed reservations automatically expire',
                    'min': 1,
                    'max': 168,
                    'unit': 'hours'
                }
            ]
        }
    }
    
    # Create a dictionary of existing settings for easy lookup
    existing_settings = {setting.key: setting for setting in settings}
    
    # Add current values to setting definitions
    for category_key, category in setting_categories.items():
        for setting_def in category['settings']:
            if setting_def['key'] in existing_settings:
                setting_def['current_value'] = existing_settings[setting_def['key']].value
                setting_def['is_configured'] = True
                setting_def['setting_object'] = existing_settings[setting_def['key']]
            else:
                setting_def['current_value'] = setting_def['default']
                setting_def['is_configured'] = False
                setting_def['setting_object'] = None
    
    context = {
        'setting_categories': setting_categories,
        'settings': settings,
    }
    
    return render(request, 'admin_dashboard/system_settings.html', context)

@login_required
@admin_required
def delete_setting(request, setting_id):
    """Delete a system setting"""
    setting = get_object_or_404(SystemSetting, id=setting_id)
    
    if request.method == 'POST':
        setting_key = setting.key
        
        # Log the action
        AuditLog.objects.create(
            user=request.user,
            action='SETTING_UPDATE',
            details=f"Deleted system setting: {setting_key}",
            ip_address=get_client_ip(request)
        )
        
        # Invalidate cache for this setting
        SystemSettingsHelper.invalidate_cache(setting_key)
        
        setting.delete()
        messages.success(request, f"Setting '{setting_key}' deleted successfully.")
    
    return redirect('admin_dashboard:system_settings')

@login_required
@admin_required
@audit_view_access('audit_logs')
def audit_logs(request):
    """View comprehensive audit logs with security monitoring"""
    logs = AuditLog.objects.all().select_related('user')
    
    # Apply filters
    action_filter = request.GET.get('action', '').strip()
    user_filter = request.GET.get('user', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    security_filter = request.GET.get('security', '').strip()
    
    # Convert empty strings to None for cleaner logic
    action_filter = action_filter if action_filter else None
    user_filter = user_filter if user_filter else None
    date_from = date_from if date_from else None
    date_to = date_to if date_to else None
    security_filter = security_filter if security_filter else None
    
    if action_filter:
        logs = logs.filter(action=action_filter)
    
    if user_filter:
        # Support filtering by username or full name
        logs = logs.filter(
            Q(user__username__icontains=user_filter) |
            Q(user__first_name__icontains=user_filter) |
            Q(user__last_name__icontains=user_filter)
        )
    
    if date_from:
        try:
            from_date = parse_date_flexibly(date_from)
            # Make timezone aware
            from_date = timezone.make_aware(from_date.replace(hour=0, minute=0, second=0))
            logs = logs.filter(timestamp__gte=from_date)
        except (ValueError, TypeError):
            messages.warning(request, f"Invalid from date format: {date_from}")
    
    if date_to:
        try:
            to_date = parse_date_flexibly(date_to)
            # Make timezone aware and set to end of day
            to_date = timezone.make_aware(to_date.replace(hour=23, minute=59, second=59))
            logs = logs.filter(timestamp__lte=to_date)
        except (ValueError, TypeError):
            messages.warning(request, f"Invalid to date format: {date_to}")
    
    if security_filter == 'security_events':
        security_actions = [
            'LOGIN_FAILED', 'MULTIPLE_LOGIN_FAILURES', 'ACCOUNT_LOCKED', 
            'SUSPICIOUS_ACTIVITY', 'SESSION_TIMEOUT', 'FORCE_LOGOUT'
        ]
        logs = logs.filter(action__in=security_actions)
    
    # Get security statistics
    now = timezone.now()
    today = now.date()
    week_ago = today - timedelta(days=7)
    
    security_stats = {
        'failed_logins_today': AuditLog.objects.filter(
            action='LOGIN_FAILED',
            timestamp__date=today
        ).count(),
        'locked_accounts_today': AuditLog.objects.filter(
            action='ACCOUNT_LOCKED',
            timestamp__date=today
        ).count(),
        'failed_logins_week': AuditLog.objects.filter(
            action='LOGIN_FAILED',
            timestamp__date__gte=week_ago
        ).count(),
        'suspicious_activities_week': AuditLog.objects.filter(
            action__in=['SUSPICIOUS_ACTIVITY', 'MULTIPLE_LOGIN_FAILURES'],
            timestamp__date__gte=week_ago
        ).count(),
    }
    
    # Get top failed login IPs
    failed_login_ips = AuditLog.objects.filter(
        action='LOGIN_FAILED',
        timestamp__date__gte=week_ago,
        ip_address__isnull=False
    ).values('ip_address').annotate(
        count=Count('ip_address')
    ).order_by('-count')[:10]
    
    # Get recent security events
    recent_security_events = AuditLog.objects.filter(
        action__in=[
            'LOGIN_FAILED', 'MULTIPLE_LOGIN_FAILURES', 'ACCOUNT_LOCKED',
            'SUSPICIOUS_ACTIVITY', 'SESSION_TIMEOUT'
        ],
        timestamp__gte=now - timedelta(hours=24)
    ).order_by('-timestamp')[:20]
    
    # Pagination
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'logs': page_obj,
        'action_choices': AuditLog.ACTION_CHOICES,
        'security_stats': security_stats,
        'failed_login_ips': failed_login_ips,
        'recent_security_events': recent_security_events,
        'action_filter': action_filter,
        'user_filter': user_filter,
        'date_from': date_from,
        'date_to': date_to,
        'security_filter': security_filter,
        'today': today,
    }
    
    return render(request, 'admin_dashboard/audit_logs.html', context)

@login_required
def change_password(request):
    """Force password change for admin and manager users"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Mark password as changed
            user.mark_password_changed()
            
            # Clear admin login time from session after password change
            if user.role == 'admin':
                request.session.pop('admin_login_time', None)
            
            # Update session to prevent logout
            update_session_auth_hash(request, user)
            
            # Log the action
            AuditLog.objects.create(
                user=request.user,
                action='PASSWORD_CHANGE',
                details=f"User {user.username} changed password",
                ip_address=get_client_ip(request)
            )
            
            messages.success(request, 'Your password has been changed successfully!')
            
            # Redirect based on user role
            if request.user.role == 'admin':
                return redirect('admin_dashboard:dashboard')
            else:
                return redirect('library:home')
    else:
        form = PasswordChangeForm(request.user)
    
    # Check if password change is mandatory
    is_mandatory = (request.user.password_change_required or 
                   request.user.is_password_expired())
    
    # For admin users, check if delay has passed
    if request.user.role == 'admin' and request.session.get('admin_login_time'):
        remaining_seconds = request.user.get_password_change_remaining_seconds(request)
        
        if remaining_seconds > 0:
            is_mandatory = False
            messages.info(request, 
                f"Password change will be required in {remaining_seconds} seconds.")
    
    context = {
        'form': form,
        'is_mandatory': is_mandatory,
    }
    
    return render(request, 'admin_dashboard/change_password.html', context)

@login_required
@admin_required
def session_management(request):
    """Manage session timeout settings for users"""
    from django.contrib.auth import get_user_model
    from .models import UserSession
    
    User = get_user_model()
    
    # Handle timeout updates
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_timeout':
            user_id = request.POST.get('user_id')
            timeout_minutes = request.POST.get('timeout_minutes')
            
            try:
                timeout_minutes = int(timeout_minutes)
                if timeout_minutes < 5 or timeout_minutes > 480:  # 5 min to 8 hours
                    messages.error(request, "Timeout must be between 5 and 480 minutes")
                else:
                    user = User.objects.get(id=user_id)
                    
                    # Update all active sessions for this user
                    UserSession.objects.filter(
                        user=user,
                        is_active=True
                    ).update(timeout_minutes=timeout_minutes)
                    
                    # Log the action
                    AuditLog.objects.create(
                        user=request.user,
                        action='UPDATE_TIMEOUT',
                        details=f"Updated session timeout for {user.username} to {timeout_minutes} minutes"
                    )
                    
                    messages.success(request, f"Updated session timeout for {user.username} to {timeout_minutes} minutes")
            except (ValueError, User.DoesNotExist):
                messages.error(request, "Invalid user or timeout value")
        
        return redirect('admin_dashboard:session_management')
    
    # Get all users with their current session info
    users_with_sessions = []
    for user in User.objects.all().order_by('username'):
        active_session = UserSession.objects.filter(
            user=user,
            is_active=True
        ).first()
        
        # Get current timeout (from session or default)
        if active_session:
            current_timeout = active_session.timeout_minutes
            is_active = True
            last_activity = active_session.last_activity
        else:
            # Default timeout based on role
            role_timeouts = getattr(settings, 'SESSION_TIMEOUT_BY_ROLE', {})
            current_timeout = role_timeouts.get(user.role, 15)
            is_active = False
            last_activity = None
        
        users_with_sessions.append({
            'user': user,
            'current_timeout': current_timeout,
            'is_active': is_active,
            'last_activity': last_activity
        })
    
    context = {
        'users_with_sessions': users_with_sessions,
    }
    
    return render(request, 'admin_dashboard/session_management.html', context)

@login_required
@admin_required
@audit_view_access('reports')
def reports_dashboard(request):
    """Main reports dashboard with overview and navigation"""
    # Get date filters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Set default date range (last 30 days)
    if not date_from:
        date_from = (timezone.now() - timedelta(days=30)).date()
    else:
        try:
            date_from = parse_date_flexibly(date_from).date()
        except ValueError as e:
            messages.error(request, f"Invalid from date format: {e}")
            date_from = (timezone.now() - timedelta(days=30)).date()
    
    if not date_to:
        date_to = timezone.now().date()
    else:
        try:
            date_to = parse_date_flexibly(date_to).date()
        except ValueError as e:
            messages.error(request, f"Invalid to date format: {e}")
            date_to = timezone.now().date()
    
    # Convert to timezone-aware datetime
    date_from_dt = timezone.make_aware(datetime.combine(date_from, datetime.min.time()))
    date_to_dt = timezone.make_aware(datetime.combine(date_to, datetime.max.time()))
    
    # Generate report
    report_generator = ReportGenerator(date_from_dt, date_to_dt)
    comprehensive_report = report_generator.get_comprehensive_report()
    
    # Prepare chart data
    user_reg_chart = generate_chart_data(
        comprehensive_report['user_statistics']['user_registrations']
    )
    
    activity_chart = generate_chart_data(
        comprehensive_report['activity_report']['daily_activities']
    )
    
    context = {
        'report': comprehensive_report,
        'date_from': date_from,
        'date_to': date_to,
        'user_reg_chart': user_reg_chart,
        'activity_chart': activity_chart,
    }
    
    return render(request, 'admin_dashboard/reports/dashboard.html', context)

@login_required
@admin_required
def user_statistics_report(request):
    """Detailed user statistics report"""
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if not date_from:
        date_from_dt = timezone.now() - timedelta(days=30)
    else:
        try:
            date_from_dt = timezone.make_aware(parse_date_flexibly(date_from))
        except ValueError as e:
            messages.error(request, f"Invalid from date format: {e}")
            return redirect('admin_dashboard:reports_dashboard')
    
    if not date_to:
        date_to_dt = timezone.now()
    else:
        try:
            date_to_dt = timezone.make_aware(parse_date_flexibly(date_to))
        except ValueError as e:
            messages.error(request, f"Invalid to date format: {e}")
            return redirect('admin_dashboard:reports_dashboard')
    
    report_generator = ReportGenerator(date_from_dt, date_to_dt)
    report_data = report_generator.get_user_statistics_report()
    
    context = {
        'report': report_data,
        'date_from': date_from_dt.date() if date_from else None,
        'date_to': date_to_dt.date() if date_to else None,
    }
    
    return render(request, 'admin_dashboard/reports/user_statistics.html', context)

@login_required
@admin_required
def security_report(request):
    """Detailed security and audit report"""
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if not date_from:
        date_from_dt = timezone.now() - timedelta(days=30)
    else:
        try:
            date_from_dt = timezone.make_aware(parse_date_flexibly(date_from))
        except ValueError as e:
            messages.error(request, f"Invalid from date format: {e}")
            return redirect('admin_dashboard:reports_dashboard')
    
    if not date_to:
        date_to_dt = timezone.now()
    else:
        try:
            date_to_dt = timezone.make_aware(parse_date_flexibly(date_to))
        except ValueError as e:
            messages.error(request, f"Invalid to date format: {e}")
            return redirect('admin_dashboard:reports_dashboard')
    
    report_generator = ReportGenerator(date_from_dt, date_to_dt)
    report_data = report_generator.get_security_report()
    
    context = {
        'report': report_data,
        'date_from': date_from_dt.date() if date_from else None,
        'date_to': date_to_dt.date() if date_to else None,
    }
    
    return render(request, 'admin_dashboard/reports/security.html', context)

@login_required
@admin_required
def activity_report(request):
    """Detailed system activity report"""
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if not date_from:
        date_from_dt = timezone.now() - timedelta(days=30)
    else:
        try:
            date_from_dt = timezone.make_aware(parse_date_flexibly(date_from))
        except ValueError as e:
            messages.error(request, f"Invalid from date format: {e}")
            return redirect('admin_dashboard:reports_dashboard')
    
    if not date_to:
        date_to_dt = timezone.now()
    else:
        try:
            date_to_dt = timezone.make_aware(parse_date_flexibly(date_to))
        except ValueError as e:
            messages.error(request, f"Invalid to date format: {e}")
            return redirect('admin_dashboard:reports_dashboard')
    
    report_generator = ReportGenerator(date_from_dt, date_to_dt)
    report_data = report_generator.get_activity_report()
    
    # Prepare chart data
    daily_chart = generate_chart_data(report_data['daily_activities'])
    
    context = {
        'report': report_data,
        'daily_chart': daily_chart,
        'date_from': date_from_dt.date() if date_from else None,
        'date_to': date_to_dt.date() if date_to else None,
    }
    
    return render(request, 'admin_dashboard/reports/activity.html', context)

@login_required
@admin_required
def library_operations_report(request):
    """Library operations and usage report"""
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if not date_from:
        date_from_dt = timezone.now() - timedelta(days=30)
    else:
        try:
            date_from_dt = timezone.make_aware(parse_date_flexibly(date_from))
        except ValueError as e:
            messages.error(request, f"Invalid from date format: {e}")
            return redirect('admin_dashboard:reports_dashboard')
    
    if not date_to:
        date_to_dt = timezone.now()
    else:
        try:
            date_to_dt = timezone.make_aware(parse_date_flexibly(date_to))
        except ValueError as e:
            messages.error(request, f"Invalid to date format: {e}")
            return redirect('admin_dashboard:reports_dashboard')
    
    report_generator = ReportGenerator(date_from_dt, date_to_dt)
    report_data = report_generator.get_library_operations_report()
    
    context = {
        'report': report_data,
        'date_from': date_from_dt.date() if date_from else None,
        'date_to': date_to_dt.date() if date_to else None,
    }
    
    return render(request, 'admin_dashboard/reports/library_operations.html', context)

@login_required
@admin_required
def export_report(request):
    """Export reports to CSV format"""
    report_type = request.GET.get('type', 'comprehensive')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if not date_from:
        date_from_dt = timezone.now() - timedelta(days=30)
    else:
        try:
            parsed_date = parse_date_flexibly(date_from)
            date_from_dt = timezone.make_aware(parsed_date)
        except ValueError as e:
            messages.error(request, f"Invalid from date format: {e}")
            return redirect('admin_dashboard:reports_dashboard')
    
    if not date_to:
        date_to_dt = timezone.now()
    else:
        try:
            parsed_date = parse_date_flexibly(date_to)
            date_to_dt = timezone.make_aware(parsed_date)
        except ValueError as e:
            messages.error(request, f"Invalid to date format: {e}")
            return redirect('admin_dashboard:reports_dashboard')
    
    report_generator = ReportGenerator(date_from_dt, date_to_dt)
    
    if report_type == 'user_statistics':
        report_data = {'user_statistics': report_generator.get_user_statistics_report()}
        filename = f'user_statistics_report_{date_from_dt.strftime("%Y%m%d")}_{date_to_dt.strftime("%Y%m%d")}.csv'
    elif report_type == 'security':
        report_data = {'security_report': report_generator.get_security_report()}
        filename = f'security_report_{date_from_dt.strftime("%Y%m%d")}_{date_to_dt.strftime("%Y%m%d")}.csv'
    elif report_type == 'activity':
        report_data = {'activity_report': report_generator.get_activity_report()}
        filename = f'activity_report_{date_from_dt.strftime("%Y%m%d")}_{date_to_dt.strftime("%Y%m%d")}.csv'
    elif report_type == 'library_operations':
        report_data = {'library_operations': report_generator.get_library_operations_report()}
        filename = f'library_operations_report_{date_from_dt.strftime("%Y%m%d")}_{date_to_dt.strftime("%Y%m%d")}.csv'
    else:
        report_data = report_generator.get_comprehensive_report()
        filename = f'comprehensive_report_{date_from_dt.strftime("%Y%m%d")}_{date_to_dt.strftime("%Y%m%d")}.csv'
    
    # Generate CSV
    csv_content = export_report_to_csv(report_data, report_type)
    
    # Log the export
    log_audit_event(
        user=request.user,
        action='SETTING_UPDATE',
        details=f"Exported {report_type} report for period {date_from_dt.date()} to {date_to_dt.date()}",
        request=request
    )
    
    # Return CSV response
    response = HttpResponse(csv_content, content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

