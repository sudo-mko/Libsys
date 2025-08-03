from django.core.management.base import BaseCommand
from users.models import MembershipType

class Command(BaseCommand):
    help = 'Setup initial membership types with MVR pricing'

    def handle(self, *args, **options):
        # Define membership types with MVR pricing
        memberships = [
            {
                'name': 'Student Member',
                'monthly_fee': 30,
                'annual_fee': 300,
                'max_books': 4,
                'loan_period_days': 21,
                'extension_days': 7,
            },
            {
                'name': 'Basic Member',
                'monthly_fee': 50,
                'annual_fee': 500,
                'max_books': 3,
                'loan_period_days': 14,
                'extension_days': 5,
            },
            {
                'name': 'Premium Member',
                'monthly_fee': 75,
                'annual_fee': 750,
                'max_books': 5,
                'loan_period_days': 14,
                'extension_days': 7,
            },
        ]

        created_count = 0
        updated_count = 0

        for membership_data in memberships:
            membership_type, created = MembershipType.objects.get_or_create(
                name=membership_data['name'],
                defaults=membership_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created membership type: {membership_type.name}')
                )
            else:
                # Update existing membership with new pricing
                for field, value in membership_data.items():
                    if field != 'name':
                        setattr(membership_type, field, value)
                membership_type.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated membership type: {membership_type.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSetup complete! Created {created_count} new membership types, '
                f'updated {updated_count} existing ones.'
            )
        )