"""
Admin Dashboard Reports Module
Comprehensive reporting functionality for library management system
"""

from django.db.models import Count, Sum, Q, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from .models import AuditLog
from decimal import Decimal

User = get_user_model()

class ReportGenerator:
    """Generate various reports for the library management system"""
    
    def __init__(self, date_from=None, date_to=None):
        self.date_from = date_from or (timezone.now() - timedelta(days=30))
        self.date_to = date_to or timezone.now()
    
    def get_user_statistics_report(self):
        """Generate comprehensive user statistics report"""
        total_users = User.objects.count()
        
        # Users by role
        users_by_role = User.objects.values('role').annotate(
            count=Count('id')
        ).order_by('role')
        
        # User registration trends
        user_registrations = User.objects.filter(
            created_at__gte=self.date_from,
            created_at__lte=self.date_to
        ).extra(
            select={'day': 'date(created_at)'}
        ).values('day').annotate(
            count=Count('id')
        ).order_by('day')
        
        # Active vs inactive users
        active_users = User.objects.filter(is_active=True).count()
        inactive_users = total_users - active_users
        
        # Account security status
        locked_accounts = User.objects.filter(
            account_locked_until__isnull=False
        ).count()
        
        return {
            'total_users': total_users,
            'users_by_role': users_by_role,
            'user_registrations': user_registrations,
            'active_users': active_users,
            'inactive_users': inactive_users,
            'locked_accounts': locked_accounts,
        }
    
    def get_activity_report(self):
        """Generate system activity report"""
        # Total activities in period
        total_activities = AuditLog.objects.filter(
            timestamp__gte=self.date_from,
            timestamp__lte=self.date_to
        ).count()
        
        # Activities by action type
        activities_by_action = AuditLog.objects.filter(
            timestamp__gte=self.date_from,
            timestamp__lte=self.date_to
        ).values('action').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # Daily activity trends
        daily_activities = AuditLog.objects.filter(
            timestamp__gte=self.date_from,
            timestamp__lte=self.date_to
        ).extra(
            select={'day': 'date(timestamp)'}
        ).values('day').annotate(
            count=Count('id')
        ).order_by('day')
        
        # Most active users
        most_active_users = AuditLog.objects.filter(
            timestamp__gte=self.date_from,
            timestamp__lte=self.date_to,
            user__isnull=False
        ).values(
            'user__username', 'user__first_name', 'user__last_name', 'user__role'
        ).annotate(
            activity_count=Count('id')
        ).order_by('-activity_count')[:10]
        
        return {
            'total_activities': total_activities,
            'activities_by_action': activities_by_action,
            'daily_activities': daily_activities,
            'most_active_users': most_active_users,
        }
    
    def get_security_report(self):
        """Generate security and audit report"""
        # Security events
        security_actions = [
            'LOGIN_FAILED', 'MULTIPLE_LOGIN_FAILURES', 'ACCOUNT_LOCKED',
            'SUSPICIOUS_ACTIVITY', 'SESSION_TIMEOUT', 'FORCE_LOGOUT'
        ]
        
        security_events = AuditLog.objects.filter(
            timestamp__gte=self.date_from,
            timestamp__lte=self.date_to,
            action__in=security_actions
        )
        
        total_security_events = security_events.count()
        
        # Security events by type
        security_by_type = security_events.values('action').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Failed login attempts
        failed_logins = AuditLog.objects.filter(
            timestamp__gte=self.date_from,
            timestamp__lte=self.date_to,
            action='LOGIN_FAILED'
        ).count()
        
        # Account lockouts
        account_lockouts = AuditLog.objects.filter(
            timestamp__gte=self.date_from,
            timestamp__lte=self.date_to,
            action='ACCOUNT_LOCKED'
        ).count()
        
        # Top security threat IPs
        threat_ips = AuditLog.objects.filter(
            timestamp__gte=self.date_from,
            timestamp__lte=self.date_to,
            action__in=['LOGIN_FAILED', 'MULTIPLE_LOGIN_FAILURES'],
            ip_address__isnull=False
        ).values('ip_address').annotate(
            attempt_count=Count('id')
        ).order_by('-attempt_count')[:10]
        
        return {
            'total_security_events': total_security_events,
            'security_by_type': security_by_type,
            'failed_logins': failed_logins,
            'account_lockouts': account_lockouts,
            'threat_ips': threat_ips,
        }
    
    def get_library_operations_report(self):
        """Generate library operations report"""
        # Book-related activities
        book_activities = AuditLog.objects.filter(
            timestamp__gte=self.date_from,
            timestamp__lte=self.date_to,
            action__in=['BOOK_BORROW', 'BOOK_RETURN', 'RESERVATION_CREATE', 'RESERVATION_APPROVE']
        )
        
        total_book_activities = book_activities.count()
        
        # Activities by type
        book_activities_by_type = book_activities.values('action').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Fine-related activities
        fine_activities = AuditLog.objects.filter(
            timestamp__gte=self.date_from,
            timestamp__lte=self.date_to,
            action__in=['FINE_CREATE', 'FINE_PAID', 'FINE_WAIVE']
        )
        
        fine_activities_by_type = fine_activities.values('action').annotate(
            count=Count('id')
        ).order_by('-count')
        
        return {
            'total_book_activities': total_book_activities,
            'book_activities_by_type': book_activities_by_type,
            'fine_activities_by_type': fine_activities_by_type,
        }
    
    def get_session_management_report(self):
        """Generate session and timeout management report"""
        from .models import UserSession
        
        # Current active sessions
        active_sessions = UserSession.objects.filter(is_active=True)
        total_active_sessions = active_sessions.count()
        
        # Sessions by role
        sessions_by_role = active_sessions.values(
            'user__role'
        ).annotate(
            count=Count('id')
        ).order_by('user__role')
        
        # Session timeouts in period
        session_timeouts = AuditLog.objects.filter(
            timestamp__gte=self.date_from,
            timestamp__lte=self.date_to,
            action='SESSION_TIMEOUT'
        ).count()
        
        # Average session duration (for completed sessions)
        completed_sessions = UserSession.objects.filter(
            is_active=False,
            created_at__gte=self.date_from,
            last_activity__lte=self.date_to
        )
        
        session_durations = []
        for session in completed_sessions:
            duration = session.last_activity - session.created_at
            session_durations.append(duration.total_seconds() / 60)  # Convert to minutes
        
        avg_session_duration = sum(session_durations) / len(session_durations) if session_durations else 0
        
        return {
            'total_active_sessions': total_active_sessions,
            'sessions_by_role': sessions_by_role,
            'session_timeouts': session_timeouts,
            'avg_session_duration': round(avg_session_duration, 2),
        }
    
    def get_comprehensive_report(self):
        """Generate a comprehensive report combining all metrics"""
        return {
            'report_period': {
                'from': self.date_from,
                'to': self.date_to,
                'days': (self.date_to - self.date_from).days
            },
            'user_statistics': self.get_user_statistics_report(),
            'activity_report': self.get_activity_report(),
            'security_report': self.get_security_report(),
            'library_operations': self.get_library_operations_report(),
            'session_management': self.get_session_management_report(),
        }

def generate_chart_data(data_points, label_field='day', value_field='count'):
    """Generate chart-ready data from query results"""
    labels = []
    values = []
    
    for point in data_points:
        labels.append(str(point[label_field]))
        values.append(point[value_field])
    
    return {
        'labels': labels,
        'values': values
    }

def export_report_to_csv(report_data, report_type='comprehensive'):
    """Export report data to CSV format"""
    import csv
    from io import StringIO
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Write headers and data based on report type
    if report_type == 'user_statistics':
        writer.writerow(['Metric', 'Value'])
        data = report_data['user_statistics']
        writer.writerow(['Total Users', data['total_users']])
        writer.writerow(['Active Users', data['active_users']])
        writer.writerow(['Inactive Users', data['inactive_users']])
        writer.writerow(['Locked Accounts', data['locked_accounts']])
        
        writer.writerow([])  # Empty row
        writer.writerow(['Role', 'Count'])
        for role_data in data['users_by_role']:
            writer.writerow([role_data['role'], role_data['count']])
    
    elif report_type == 'security':
        writer.writerow(['Security Metric', 'Count'])
        data = report_data['security_report']
        writer.writerow(['Total Security Events', data['total_security_events']])
        writer.writerow(['Failed Logins', data['failed_logins']])
        writer.writerow(['Account Lockouts', data['account_lockouts']])
        
        writer.writerow([])
        writer.writerow(['Event Type', 'Count'])
        for event in data['security_by_type']:
            writer.writerow([event['action'], event['count']])
    
    return output.getvalue()