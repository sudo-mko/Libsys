from django.core.management.base import BaseCommand
from users.models import MembershipType


class Command(BaseCommand):
    help = 'Create default membership types for the library system'

    def handle(self, *args, **options):
        membership_types = [
            {
                'name': 'Basic Member',
                'monthly_fee': 50.00,
                'annual_fee': 500.00,
                'max_books': 3,
                'loan_period_days': 14,
                'extension_days': 0,
            },
            {
                'name': 'Premium Member',
                'monthly_fee': 75.00,
                'annual_fee': 750.00,
                'max_books': 5,
                'loan_period_days': 14,
                'extension_days': 7,
            },
            {
                'name': 'Student Member',
                'monthly_fee': 30.00,
                'annual_fee': 300.00,
                'max_books': 4,
                'loan_period_days': 21,
                'extension_days': 0,
            },
        ]

        for membership_data in membership_types:
            membership_type, created = MembershipType.objects.get_or_create(
                name=membership_data['name'],
                defaults=membership_data
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully created membership type: {membership_type.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Membership type already exists: {membership_type.name}')
                )

        self.stdout.write(
            self.style.SUCCESS('Membership types setup completed!')
        ) 