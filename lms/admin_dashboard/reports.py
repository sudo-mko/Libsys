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
        
        # Calculate success rate
        success_rate = 100
        if total_security_events > 0:
            failure_rate = (failed_logins / total_security_events) * 100
            success_rate = max(0, 100 - failure_rate)
        
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
            'success_rate': round(success_rate, 1),
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
    
    elif report_type == 'activity':
        writer.writerow(['Activity Metric', 'Count'])
        data = report_data['activity_report']
        writer.writerow(['Total Activities', data['total_activities']])
        writer.writerow(['Logins', data['login_count']])
        writer.writerow(['Logouts', data['logout_count']])
        writer.writerow(['Password Changes', data['password_changes']])
        
        writer.writerow([])
        writer.writerow(['Date', 'Activity Count'])
        for activity in data['daily_activities']:
            writer.writerow([activity['day'], activity['count']])
        
        writer.writerow([])
        writer.writerow(['Action Type', 'Count'])
        for activity in data['activities_by_type']:
            writer.writerow([activity['action'], activity['count']])
    
    elif report_type == 'library_operations':
        writer.writerow(['Library Metric', 'Count'])
        data = report_data['library_operations']
        writer.writerow(['Total Books', data['total_books']])
        writer.writerow(['Available Books', data['available_books']])
        writer.writerow(['Borrowed Books', data['borrowed_books']])
        writer.writerow(['Total Borrowings', data['total_borrowings']])
        writer.writerow(['Active Borrowings', data['active_borrowings']])
        writer.writerow(['Total Returns', data['total_returns']])
        writer.writerow(['Total Reservations', data['total_reservations']])
        writer.writerow(['Active Reservations', data['active_reservations']])
        writer.writerow(['Total Fines', f"${data['total_fines']:.2f}"])
        writer.writerow(['Paid Fines', f"${data['paid_fines']:.2f}"])
        writer.writerow(['Unpaid Fines', f"${data['unpaid_fines']:.2f}"])
        
        writer.writerow([])
        writer.writerow(['Popular Books'])
        writer.writerow(['Title', 'Author', 'Borrow Count'])
        for book in data['popular_books']:
            writer.writerow([book['title'], book['author'], book['borrow_count']])
    
    elif report_type == 'comprehensive':
        # Write comprehensive report with all sections
        writer.writerow(['COMPREHENSIVE LIBRARY MANAGEMENT SYSTEM REPORT'])
        writer.writerow(['=' * 50])
        writer.writerow([])
        
        # Report period
        period = report_data.get('report_period', {})
        writer.writerow(['Report Period:', f"{period.get('from', 'N/A')} to {period.get('to', 'N/A')}"])
        writer.writerow(['Days Covered:', period.get('days', 'N/A')])
        writer.writerow([])
        
        # User Statistics Section
        writer.writerow(['USER STATISTICS'])
        writer.writerow(['-' * 30])
        user_data = report_data.get('user_statistics', {})
        writer.writerow(['Total Users', user_data.get('total_users', 0)])
        writer.writerow(['Active Users', user_data.get('active_users', 0)])
        writer.writerow(['Inactive Users', user_data.get('inactive_users', 0)])
        writer.writerow(['Locked Accounts', user_data.get('locked_accounts', 0)])
        writer.writerow([])
        
        # Activity Section
        writer.writerow(['SYSTEM ACTIVITY'])
        writer.writerow(['-' * 30])
        activity_data = report_data.get('activity_report', {})
        writer.writerow(['Total Activities', activity_data.get('total_activities', 0)])
        writer.writerow(['Logins', activity_data.get('login_count', 0)])
        writer.writerow(['Logouts', activity_data.get('logout_count', 0)])
        writer.writerow(['Password Changes', activity_data.get('password_changes', 0)])
        writer.writerow([])
        
        # Security Section
        writer.writerow(['SECURITY REPORT'])
        writer.writerow(['-' * 30])
        security_data = report_data.get('security_report', {})
        writer.writerow(['Total Security Events', security_data.get('total_security_events', 0)])
        writer.writerow(['Failed Logins', security_data.get('failed_logins', 0)])
        writer.writerow(['Account Lockouts', security_data.get('account_lockouts', 0)])
        writer.writerow([])
        
        # Library Operations Section
        writer.writerow(['LIBRARY OPERATIONS'])
        writer.writerow(['-' * 30])
        lib_data = report_data.get('library_operations', {})
        writer.writerow(['Total Books', lib_data.get('total_books', 0)])
        writer.writerow(['Available Books', lib_data.get('available_books', 0)])
        writer.writerow(['Borrowed Books', lib_data.get('borrowed_books', 0)])
        writer.writerow(['Total Borrowings', lib_data.get('total_borrowings', 0)])
        writer.writerow(['Active Borrowings', lib_data.get('active_borrowings', 0)])
        writer.writerow(['Total Reservations', lib_data.get('total_reservations', 0)])
        writer.writerow(['Active Reservations', lib_data.get('active_reservations', 0)])
        writer.writerow(['Total Fines', f"${lib_data.get('total_fines', 0):.2f}"])
        writer.writerow(['Paid Fines', f"${lib_data.get('paid_fines', 0):.2f}"])
        writer.writerow(['Unpaid Fines', f"${lib_data.get('unpaid_fines', 0):.2f}"])
    
    else:
        # Fallback for unknown report types
        writer.writerow(['Error', f'Unknown report type: {report_type}'])
    
    return output.getvalue()