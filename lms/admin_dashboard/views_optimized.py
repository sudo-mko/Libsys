from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.conf import settings
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie
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

# Cache timeouts
STATS_CACHE_TIMEOUT = 300  # 5 minutes
SESSION_CACHE_TIMEOUT = 60  # 1 minute

def get_cached_stats():
    """Get cached dashboard statistics"""
    cache_key = 'admin_dashboard_stats'
    stats = cache.get(cache_key)
    
    if stats is None:
        # Calculate statistics only when cache is empty
        stats = {
            'total_users': User.objects.count(),
            'total_members': User.objects.filter(role='member').count(),
            'total_librarians': User.objects.filter(role='librarian').count(),
            'total_managers': User.objects.filter(role='manager').count(),
            'recent_users': User.objects.filter(
                created_at__gte=timezone.now() - timedelta(days=30)
            ).count(),
            'recent_audit_logs': AuditLog.objects.filter(
                timestamp__gte=timezone.now() - timedelta(days=30)
            ).count(),
            'locked_accounts': User.objects.filter(account_locked_until__isnull=False).count(),
            'active_accounts': User.objects.filter(is_active=True).count(),
        }
        
        # Cache the results
        cache.set(cache_key, stats, STATS_CACHE_TIMEOUT)
    
    return stats

def invalidate_stats_cache():
    """Invalidate dashboard statistics cache"""
    cache.delete('admin_dashboard_stats')

def optimized_session_check(request):
    """Optimized session validation with caching"""
    if not request.user.is_authenticated:
        return False
    
    # Cache session validation for 1 minute
    session_cache_key = f'user_session_{request.user.id}'
    session_valid = cache.get(session_cache_key)
    
    if session_valid is None:
        # Check session validity
        session_valid = (
            request.user.is_active and 
            not request.user.account_locked_until and
            request.user.role in ['admin', 'manager']
        )
        
        # Cache the result
        cache.set(session_cache_key, session_valid, SESSION_CACHE_TIMEOUT)
    
    return session_valid

def admin_required_optimized(view_func):
    """Optimized decorator with session caching"""
    def wrapper(request, *args, **kwargs):
        if not optimized_session_check(request):
            return HttpResponseForbidden("You don't have permission to access admin features.")
        return view_func(request, *args, **kwargs)
    return wrapper

@login_required
@admin_required_optimized
def admin_dashboard_optimized(request):
    """Optimized admin dashboard with lazy loading"""
    # Use cached statistics
    stats = get_cached_stats()
    
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
@admin_required_optimized
def manage_users_optimized(request):
    """Optimized user management with lazy loading"""
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
    
    # Cache user statistics
    stats_cache_key = f'user_stats_{search_query}_{role_filter}_{status_filter}'
    user_stats = cache.get(stats_cache_key)
    
    if user_stats is None:
        user_stats = {
            'total': User.objects.count(),
            'active': User.objects.filter(is_active=True).count(),
            'locked': User.objects.filter(account_locked_until__isnull=False).count(),
            'members': User.objects.filter(role='member').count(),
            'librarians': User.objects.filter(role='librarian').count(),
            'managers': User.objects.filter(role='manager').count(),
            'admins': User.objects.filter(role='admin').count(),
        }
        cache.set(stats_cache_key, user_stats, STATS_CACHE_TIMEOUT)
    
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
@admin_required_optimized
def system_settings_optimized(request):
    """Optimized system settings with lazy loading"""
    # Cache settings by category
    settings_cache_key = 'system_settings_categories'
    setting_categories = cache.get(settings_cache_key)
    
    if setting_categories is None:
        # Load settings only when cache is empty
        settings = SystemSetting.objects.all().order_by('key')
        existing_settings = {setting.key: setting for setting in settings}
        
        # Define setting categories (same as original)
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
                        'description': 'Maximum number of books a user can borrow simultaneously',
                        'min': 1,
                        'max': 50
                    },
                    # ... other settings
                ]
            },
            # ... other categories
        }
        
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
        
        cache.set(settings_cache_key, setting_categories, STATS_CACHE_TIMEOUT)
    
    context = {
        'setting_categories': setting_categories,
    }
    
    return render(request, 'admin_dashboard/system_settings.html', context)

# AJAX endpoint for lazy loading detailed statistics
@login_required
@admin_required_optimized
def get_dashboard_stats_ajax(request):
    """AJAX endpoint for lazy loading dashboard statistics"""
    stats_type = request.GET.get('type', 'basic')
    
    if stats_type == 'detailed':
        # Load detailed statistics only when requested
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
    return JsonResponse(get_cached_stats())

# Signal handlers to invalidate cache when data changes
def invalidate_cache_on_user_change(sender, instance, **kwargs):
    """Invalidate cache when user data changes"""
    invalidate_stats_cache()
    cache.delete(f'user_session_{instance.id}')

def invalidate_cache_on_audit_log_change(sender, instance, **kwargs):
    """Invalidate cache when audit log changes"""
    invalidate_stats_cache()

# Connect signals
from django.db.models.signals import post_save, post_delete
post_save.connect(invalidate_cache_on_user_change, sender=User)
post_save.connect(invalidate_cache_on_audit_log_change, sender=AuditLog)
post_delete.connect(invalidate_cache_on_audit_log_change, sender=AuditLog) 