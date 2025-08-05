"""
Cached Views for Admin Dashboard
Views that use the cache manager for improved performance
"""

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
from .cache_manager import AdminDashboardCacheManager, cached_dashboard_stats, cached_user_stats
from utils.system_settings import SystemSettingsHelper
from .signals import get_client_ip
from datetime import datetime, timedelta
from django.utils import timezone
from .reports import ReportGenerator, generate_chart_data, export_report_to_csv
from django.http import HttpResponse
import json
from functools import wraps

User = get_user_model()

def admin_required(view_func):
    """Decorator to ensure only admin and manager users can access admin views"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role not in ['admin', 'manager']:
            return HttpResponseForbidden("You don't have permission to access admin features.")
        return view_func(request, *args, **kwargs)
    return wrapper

@login_required
@admin_required
def admin_dashboard_cached(request):
    """Cached admin dashboard with overview statistics"""
    # Use cache manager to get dashboard statistics
    stats = AdminDashboardCacheManager.get_dashboard_stats()
    
    # Only load additional data if specifically requested
    load_detailed_stats = request.GET.get('detailed', 'false').lower() == 'true'
    
    context = {
        **stats,  # Include cached stats
        'load_detailed_stats': load_detailed_stats,
    }
    
    # Load detailed stats only when requested
    if load_detailed_stats:
        context.update({
            'recent_activities': AuditLog.objects.select_related('user').order_by('-timestamp')[:10],
            'user_registration_trend': User.objects.extra(
                select={'day': 'date(created_at)'}
            ).values('day').annotate(count=Count('id')).order_by('-day')[:7],
        })
    
    return render(request, 'admin_dashboard/dashboard.html', context)

@login_required
@admin_required
def manage_users_cached(request):
    """Cached user management interface"""
    # Get search and filter parameters
    search_query = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')
    
    # Base queryset with select_related for optimization
    users = User.objects.select_related('membership').order_by('-created_at')
    
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
    
    # Use cache manager to get user statistics
    user_stats = AdminDashboardCacheManager.get_user_stats(
        search_query=search_query,
        role_filter=role_filter,
        status_filter=status_filter
    )
    
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
def system_settings_cached(request):
    """Cached system configuration interface"""
    # Use cache manager to get system settings
    setting_categories = AdminDashboardCacheManager.get_system_settings()
    
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
            AdminDashboardCacheManager.invalidate_cache('SETTINGS')
            
            messages.success(request, f"Setting '{setting_key}' {'created' if created else 'updated'} successfully.")
            return redirect('admin_dashboard:system_settings')
    
    context = {
        'setting_categories': setting_categories,
    }
    
    return render(request, 'admin_dashboard/system_settings.html', context)

@login_required
@admin_required
def audit_logs_cached(request):
    """Cached audit logs with security monitoring"""
    # Get filter parameters
    action_filter = request.GET.get('action', '').strip()
    user_filter = request.GET.get('user', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    security_filter = request.GET.get('security', '').strip()
    page = request.GET.get('page', 1)
    
    # Use cache manager to get audit logs
    logs_data = AdminDashboardCacheManager.get_audit_logs(
        action_filter=action_filter,
        user_filter=user_filter,
        date_from=date_from,
        date_to=date_to,
        security_filter=security_filter,
        page=page
    )
    
    # Get security statistics
    security_stats = AdminDashboardCacheManager.get_security_stats()
    
    # Get recent security events
    recent_security_events = AuditLog.objects.filter(
        action__in=[
            'LOGIN_FAILED', 'MULTIPLE_LOGIN_FAILURES', 'ACCOUNT_LOCKED',
            'SUSPICIOUS_ACTIVITY', 'SESSION_TIMEOUT'
        ],
        timestamp__gte=timezone.now() - timedelta(hours=24)
    ).order_by('-timestamp')[:20]
    
    context = {
        'logs': logs_data.get('page_obj'),
        'action_choices': AuditLog.ACTION_CHOICES,
        'security_stats': security_stats,
        'failed_login_ips': security_stats.get('failed_login_ips', []),
        'recent_security_events': recent_security_events,
        'action_filter': action_filter,
        'user_filter': user_filter,
        'date_from': date_from,
        'date_to': date_to,
        'security_filter': security_filter,
        'today': timezone.now().date(),
    }
    
    return render(request, 'admin_dashboard/audit_logs.html', context)

@login_required
@admin_required
def reports_dashboard_cached(request):
    """Cached reports dashboard with overview and navigation"""
    # Get date filters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Set default date range (last 30 days)
    if not date_from:
        date_from = (timezone.now() - timedelta(days=30)).date()
    else:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, f"Invalid from date format: {date_from}")
            date_from = (timezone.now() - timedelta(days=30)).date()
    
    if not date_to:
        date_to = timezone.now().date()
    else:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, f"Invalid to date format: {date_to}")
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

# AJAX endpoints for dynamic loading
@login_required
@admin_required
def get_dashboard_stats_ajax(request):
    """AJAX endpoint for dashboard statistics"""
    stats_type = request.GET.get('type', 'basic')
    
    if stats_type == 'detailed':
        # Load detailed statistics
        detailed_stats = {
            'recent_activities': list(AuditLog.objects.select_related('user').order_by('-timestamp')[:10].values(
                'user__username', 'action', 'timestamp', 'ip_address'
            )),
            'user_registration_trend': list(User.objects.extra(
                select={'day': 'date(created_at)'}
            ).values('day').annotate(count=Count('id')).order_by('-day')[:7]),
            'security_events': list(AuditLog.objects.filter(
                action__in=['LOGIN_FAILED', 'ACCOUNT_LOCKED', 'SUSPICIOUS_ACTIVITY']
            ).order_by('-timestamp')[:5].values('action', 'timestamp', 'ip_address')),
        }
        return JsonResponse(detailed_stats)
    
    # Return basic cached stats
    return JsonResponse(AdminDashboardCacheManager.get_dashboard_stats())

@login_required
@admin_required
def get_user_stats_ajax(request):
    """AJAX endpoint for user statistics"""
    search_query = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')
    
    user_stats = AdminDashboardCacheManager.get_user_stats(
        search_query=search_query,
        role_filter=role_filter,
        status_filter=status_filter
    )
    
    return JsonResponse(user_stats)

@login_required
@admin_required
def get_security_stats_ajax(request):
    """AJAX endpoint for security statistics"""
    security_stats = AdminDashboardCacheManager.get_security_stats()
    return JsonResponse(security_stats)

@login_required
@admin_required
def get_audit_logs_ajax(request):
    """AJAX endpoint for audit logs"""
    action_filter = request.GET.get('action', '')
    user_filter = request.GET.get('user', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    security_filter = request.GET.get('security', '')
    page = request.GET.get('page', 1)
    
    logs_data = AdminDashboardCacheManager.get_audit_logs(
        action_filter=action_filter,
        user_filter=user_filter,
        date_from=date_from,
        date_to=date_to,
        security_filter=security_filter,
        page=page
    )
    
    return JsonResponse({
        'logs': list(logs_data.get('logs', [])),
        'total_count': logs_data.get('total_count', 0),
    })

# Cache management endpoints
@login_required
@admin_required
def clear_cache(request):
    """Clear all admin dashboard caches"""
    if request.method == 'POST':
        AdminDashboardCacheManager.invalidate_cache()
        messages.success(request, "All admin dashboard caches have been cleared.")
        return redirect('admin_dashboard:dashboard')
    
    return render(request, 'admin_dashboard/clear_cache_confirm.html')

@login_required
@admin_required
def cache_info(request):
    """Display cache information and statistics"""
    cache_info = AdminDashboardCacheManager.get_cache_info()
    
    context = {
        'cache_info': cache_info,
        'cache_timeouts': AdminDashboardCacheManager.CACHE_TIMEOUTS,
        'cache_prefixes': AdminDashboardCacheManager.CACHE_PREFIXES,
    }
    
    return render(request, 'admin_dashboard/cache_info.html', context)

# Decorator examples for caching
@cached_dashboard_stats(timeout=300)
def get_dashboard_statistics():
    """Example function using cache decorator"""
    # This function's result will be cached for 5 minutes
    return AdminDashboardCacheManager._calculate_dashboard_stats()

@cached_user_stats(timeout=180)
def get_user_statistics(search_query='', role_filter='', status_filter=''):
    """Example function using cache decorator with parameters"""
    # This function's result will be cached for 3 minutes
    return AdminDashboardCacheManager._calculate_user_stats() 