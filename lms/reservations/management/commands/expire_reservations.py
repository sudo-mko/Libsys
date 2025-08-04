"""
Management command to automatically expire reservations based on system settings.

This command can be run periodically (e.g., via cron) to automatically expire
reservations that have been confirmed but not picked up within the timeout period.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from reservations.models import Reservation
from utils.system_settings import SystemSettingsHelper
from admin_dashboard.models import AuditLog


class Command(BaseCommand):
    help = 'Expire reservations that have exceeded the timeout period'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be expired without actually expiring them',
        )
        parser.add_argument(
            '--timeout-hours',
            type=int,
            help='Override system setting for timeout hours',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Get timeout from system settings or command line override
        if options['timeout_hours']:
            timeout_hours = options['timeout_hours']
            self.stdout.write(f"Using command line timeout: {timeout_hours} hours")
        else:
            timeout_hours = SystemSettingsHelper.get_reservation_timeout_hours(24)
            self.stdout.write(f"Using system setting timeout: {timeout_hours} hours")
        
        # Calculate cutoff time
        cutoff = timezone.now() - timedelta(hours=timeout_hours)
        
        # Find reservations that should be expired
        reservations_to_expire = Reservation.objects.filter(
            status='confirmed',
            created_at__lt=cutoff
        )
        
        count = reservations_to_expire.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('No reservations found that need to be expired.')
            )
            return
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'DRY RUN: Would expire {count} reservations:')
            )
            for reservation in reservations_to_expire:
                self.stdout.write(
                    f"  - {reservation.user.username}: {reservation.book.title} "
                    f"(created: {reservation.created_at})"
                )
        else:
            # Actually expire the reservations
            expired_count = 0
            for reservation in reservations_to_expire:
                old_status = reservation.status
                reservation.status = 'expired'
                reservation.save()
                
                # Log the action (create a system user for audit logs if needed)
                try:
                    AuditLog.objects.create(
                        user=reservation.user,  # Log against the user who had the reservation
                        action='RESERVATION_EXPIRE',
                        details=f"Reservation automatically expired after {timeout_hours} hours: {reservation.book.title}",
                        ip_address='system'
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f"Could not create audit log: {e}")
                    )
                
                expired_count += 1
                self.stdout.write(
                    f"Expired: {reservation.user.username} - {reservation.book.title}"
                )
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully expired {expired_count} reservations.')
            )