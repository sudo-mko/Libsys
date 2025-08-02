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
from .signals import get_client_ip
from datetime import datetime, timedelta
from django.utils import timezone
from .reports import ReportGenerator, generate_chart_data, export_report_to_csv
from django.http import HttpResponse
import json
from functools import wraps

User = get_user_model()

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
    """Decorator to ensure only admin users can access admin views"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != 'admin':
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
        user.role = request.POST.get('role', user.role)
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
    
    context = {
        'user_obj': user,
        'membership_types': MembershipType.objects.all(),
        'role_choices': User.ROLE_CHOICES,
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
            action_type = 'TIMEOUT_SETTINGS_UPDATE' if created else 'TIMEOUT_SETTINGS_UPDATE'
            AuditLog.objects.create(
                user=request.user,
                action=action_type,
                details=f"{'Created' if created else 'Updated'} system setting: {setting_key}",
                ip_address=get_client_ip(request)
            )
            
            messages.success(request, f"Setting '{setting_key}' {'created' if created else 'updated'} successfully.")
            return redirect('admin_dashboard:system_settings')
    
    # Default settings to create if they don't exist
    default_settings = [
        {
            'key': 'max_borrowing_days',
            'value': '14',
            'setting_type': 'number',
            'description': 'Maximum number of days a book can be borrowed'
        },
        {
            'key': 'max_books_per_user',
            'value': '5',
            'setting_type': 'number',
            'description': 'Maximum number of books a user can borrow at once'
        },
        {
            'key': 'fine_per_day',
            'value': '1.00',
            'setting_type': 'number',
            'description': 'Fine amount per day for overdue books'
        },
        {
            'key': 'reservation_timeout_hours',
            'value': '24',
            'setting_type': 'number',
            'description': 'Hours before a reservation expires'
        },
    ]
    
    context = {
        'settings': settings,
        'default_settings': default_settings,
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
            action='TIMEOUT_SETTINGS_UPDATE',
            details=f"Deleted system setting: {setting_key}",
            ip_address=get_client_ip(request)
        )
        
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
            from_date = datetime.strptime(date_from, '%Y-%m-%d')
            # Make timezone aware
            from_date = timezone.make_aware(from_date.replace(hour=0, minute=0, second=0))
            logs = logs.filter(timestamp__gte=from_date)
        except (ValueError, TypeError):
            messages.warning(request, f"Invalid from date format: {date_from}")
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d')
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
        date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
    
    if not date_to:
        date_to = timezone.now().date()
    else:
        date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
    
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
        date_from_dt = timezone.make_aware(datetime.strptime(date_from, '%Y-%m-%d'))
    
    if not date_to:
        date_to_dt = timezone.now()
    else:
        date_to_dt = timezone.make_aware(datetime.strptime(date_to, '%Y-%m-%d'))
    
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
        date_from_dt = timezone.make_aware(datetime.strptime(date_from, '%Y-%m-%d'))
    
    if not date_to:
        date_to_dt = timezone.now()
    else:
        date_to_dt = timezone.make_aware(datetime.strptime(date_to, '%Y-%m-%d'))
    
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
        date_from_dt = timezone.make_aware(datetime.strptime(date_from, '%Y-%m-%d'))
    
    if not date_to:
        date_to_dt = timezone.now()
    else:
        date_to_dt = timezone.make_aware(datetime.strptime(date_to, '%Y-%m-%d'))
    
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
        date_from_dt = timezone.make_aware(datetime.strptime(date_from, '%Y-%m-%d'))
    
    if not date_to:
        date_to_dt = timezone.now()
    else:
        date_to_dt = timezone.make_aware(datetime.strptime(date_to, '%Y-%m-%d'))
    
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
        date_from_dt = timezone.make_aware(datetime.strptime(date_from, '%Y-%m-%d'))
    
    if not date_to:
        date_to_dt = timezone.now()
    else:
        date_to_dt = timezone.make_aware(datetime.strptime(date_to, '%Y-%m-%d'))
    
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

