from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from admin_dashboard.models import UserSession
import time

User = get_user_model()

class Command(BaseCommand):
    help = 'Monitor active sessions and show timeout status in real-time'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=30,
            help='Check interval in seconds (default: 30)',
        )
        parser.add_argument(
            '--watch',
            action='store_true',
            help='Continuously monitor sessions',
        )

    def handle(self, *args, **options):
        interval = options.get('interval')
        watch_mode = options.get('watch')
        
        self.stdout.write(
            self.style.SUCCESS('🔍 Session Timeout Monitor')
        )
        self.stdout.write('=' * 60)
        
        try:
            while True:
                self.check_sessions()
                
                if not watch_mode:
                    break
                    
                self.stdout.write(f'\n⏱️  Next check in {interval} seconds...\n')
                time.sleep(interval)
                
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING('\n👋 Monitoring stopped by user')
            )

    def check_sessions(self):
        now = timezone.now()
        
        # Get all active sessions
        active_sessions = UserSession.objects.filter(
            is_active=True
        ).select_related('user').order_by('last_activity')
        
        if not active_sessions:
            self.stdout.write(
                self.style.WARNING('📭 No active sessions found')
            )
            return
        
        self.stdout.write(f'🕐 Current time: {now.strftime("%Y-%m-%d %H:%M:%S")}')
        self.stdout.write(f'📊 Active sessions: {active_sessions.count()}')
        self.stdout.write('-' * 60)
        
        expired_count = 0
        warning_count = 0
        
        for session in active_sessions:
            # Calculate time since last activity
            inactive_time = now - session.last_activity
            inactive_minutes = inactive_time.total_seconds() / 60
            
            # Get timeout setting
            timeout_minutes = session.timeout_minutes
            
            # Calculate remaining time
            remaining_minutes = timeout_minutes - inactive_minutes
            
            # Determine status
            if remaining_minutes <= 0:
                status = self.style.ERROR('🔴 EXPIRED')
                expired_count += 1
            elif remaining_minutes <= 2:
                status = self.style.WARNING('🟡 WARNING')
                warning_count += 1
            else:
                status = self.style.SUCCESS('🟢 ACTIVE')
            
            # Format user info
            user_info = f"{session.user.username} ({session.user.get_role_display()})"
            
            # Format timing info
            last_activity_str = session.last_activity.strftime("%H:%M:%S")
            
            self.stdout.write(
                f'{status} {user_info:<25} '
                f'Inactive: {inactive_minutes:5.1f}m / {timeout_minutes}m '
                f'(Last: {last_activity_str})'
            )
            
            # Show session details for expired sessions
            if remaining_minutes <= 0:
                self.stdout.write(f'   📍 Session: {session.session_key[:16]}...')
                self.stdout.write(f'   ⚠️  Should be logged out automatically on next request')
        
        # Summary
        self.stdout.write('-' * 60)
        summary_parts = []
        if expired_count > 0:
            summary_parts.append(self.style.ERROR(f'{expired_count} expired'))
        if warning_count > 0:
            summary_parts.append(self.style.WARNING(f'{warning_count} expiring soon'))
        
        active_count = active_sessions.count() - expired_count
        if active_count > 0:
            summary_parts.append(self.style.SUCCESS(f'{active_count} active'))
        
        if summary_parts:
            self.stdout.write(f'📈 Summary: {" | ".join(summary_parts)}')
        
        self.stdout.write('')