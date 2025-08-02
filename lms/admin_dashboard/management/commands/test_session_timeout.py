from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from admin_dashboard.models import UserSession, AuditLog
from django.contrib.sessions.models import Session

User = get_user_model()

class Command(BaseCommand):
    help = 'Test and demonstrate session timeout functionality'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Username to test (defaults to first user found)',
        )
        parser.add_argument(
            '--timeout-minutes',
            type=int,
            default=1,
            help='Minutes to simulate timeout (default: 1 minute)',
        )

    def handle(self, *args, **options):
        username = options.get('username')
        timeout_minutes = options.get('timeout_minutes')
        
        # Get user
        if username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'User "{username}" not found')
                )
                return
        else:
            user = User.objects.first()
            if not user:
                self.stdout.write(
                    self.style.ERROR('No users found in database')
                )
                return

        self.stdout.write(
            self.style.SUCCESS(f'Testing session timeout for user: {user.username}')
        )
        self.stdout.write(f'User role: {user.role}')
        self.stdout.write(f'Simulated timeout: {timeout_minutes} minutes')
        
        # Create a mock session
        session_key = f'test_session_{timezone.now().timestamp()}'
        
        # Create UserSession record with backdated last_activity
        past_time = timezone.now() - timedelta(minutes=timeout_minutes + 1)
        
        user_session = UserSession.objects.create(
            user=user,
            session_key=session_key,
            is_active=True,
            timeout_minutes=timeout_minutes,
            last_activity=past_time,
            created_at=past_time
        )
        
        self.stdout.write(
            self.style.WARNING(f'Created test session: {session_key}')
        )
        self.stdout.write(f'Last activity: {past_time}')
        self.stdout.write(f'Current time: {timezone.now()}')
        
        # Calculate inactivity duration
        inactive_duration = timezone.now() - past_time
        self.stdout.write(f'Inactive for: {inactive_duration.total_seconds() / 60:.1f} minutes')
        
        # Check if session should be timed out
        if inactive_duration > timedelta(minutes=timeout_minutes):
            self.stdout.write(
                self.style.ERROR(f'❌ Session SHOULD be timed out (inactive > {timeout_minutes} min)')
            )
            
            # Mark session as inactive (simulating middleware action)
            user_session.is_active = False
            user_session.save()
            
            # Log timeout event
            AuditLog.objects.create(
                user=user,
                action='SESSION_TIMEOUT',
                details=f'Test session timeout after {inactive_duration.total_seconds() / 60:.1f} minutes of inactivity'
            )
            
            self.stdout.write(
                self.style.SUCCESS('✅ Session marked as inactive and logged')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'✅ Session is still valid (inactive < {timeout_minutes} min)')
            )
        
        # Show current status
        self.stdout.write('\n--- Session Status ---')
        self.stdout.write(f'Session Key: {user_session.session_key}')
        self.stdout.write(f'Active: {user_session.is_active}')
        self.stdout.write(f'Timeout Setting: {user_session.timeout_minutes} minutes')
        self.stdout.write(f'Last Activity: {user_session.last_activity}')
        
        # Check recent audit logs
        recent_logs = AuditLog.objects.filter(
            user=user,
            action='SESSION_TIMEOUT'
        ).order_by('-timestamp')[:3]
        
        if recent_logs:
            self.stdout.write('\n--- Recent Session Timeout Logs ---')
            for log in recent_logs:
                self.stdout.write(f'{log.timestamp}: {log.details}')
        
        # Show all active sessions for this user
        active_sessions = UserSession.objects.filter(
            user=user,
            is_active=True
        ).count()
        
        self.stdout.write(f'\n--- User Session Summary ---')
        self.stdout.write(f'User: {user.username} ({user.get_role_display()})')
        self.stdout.write(f'Active Sessions: {active_sessions}')
        
        # Show timeout configuration
        from django.conf import settings
        role_timeout = getattr(settings, 'SESSION_TIMEOUT_BY_ROLE', {}).get(user.role, 15)
        self.stdout.write(f'Role Default Timeout: {role_timeout} minutes')
        
        self.stdout.write(
            self.style.SUCCESS('\n✅ Session timeout test completed!')
        )