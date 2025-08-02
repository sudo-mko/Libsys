from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class Command(BaseCommand):
    help = 'Initialize password policy for existing admin and manager users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force-change',
            action='store_true',
            help='Force all admin and manager users to change password on next login',
        )

    def handle(self, *args, **options):
        admin_manager_users = User.objects.filter(role__in=['admin', 'manager'])
        
        if not admin_manager_users.exists():
            self.stdout.write(
                self.style.WARNING('No admin or manager users found.')
            )
            return
        
        updated_count = 0
        
        for user in admin_manager_users:
            if not user.last_password_change:
                # Set password change date to account creation date
                # This ensures existing users don't get forced to change immediately
                user.last_password_change = user.date_joined or timezone.now()
                
                if options['force_change']:
                    user.password_change_required = True
                    self.stdout.write(f"  - {user.username}: Set password change required")
                else:
                    self.stdout.write(f"  - {user.username}: Set last password change to {user.last_password_change}")
                
                user.save()
                updated_count += 1
        
        if updated_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully initialized password policy for {updated_count} users.'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('All admin and manager users already have password policy initialized.')
            )