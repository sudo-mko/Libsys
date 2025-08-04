# Generated manually to populate initial system settings

from django.db import migrations
from decimal import Decimal


def create_initial_settings(apps, schema_editor):
    """
    Create initial system settings that match current hardcoded defaults.
    This ensures a smooth transition without breaking existing functionality.
    """
    SystemSetting = apps.get_model('admin_dashboard', 'SystemSetting')
    
    # Define default settings based on current hardcoded values in the codebase
    default_settings = [
        {
            'key': 'max_books_per_user',
            'value': '5',
            'setting_type': 'number',
            'description': 'Maximum number of books a user can borrow at once (fallback if membership type not specified)',
        },
        {
            'key': 'max_borrowing_days',
            'value': '14',
            'setting_type': 'number',
            'description': 'Default maximum number of days a book can be borrowed (fallback if membership type not specified)',
        },
        {
            'key': 'fine_per_day',
            'value': '2.00',
            'setting_type': 'decimal',
            'description': 'Base fine amount per day for overdue books (used in tiered calculation)',
        },
        {
            'key': 'reservation_timeout_hours',
            'value': '24',
            'setting_type': 'number',
            'description': 'Hours before a reservation expires and becomes available to others',
        },
        {
            'key': 'session_timeout_minutes',
            'value': '15',
            'setting_type': 'number',
            'description': 'Default session timeout in minutes for regular users (admin/manager may have different timeouts)',
        },
        {
            'key': 'pickup_code_expiry_days',
            'value': '3',
            'setting_type': 'number',
            'description': 'Number of days before an approved borrowing pickup code expires',
        },
        {
            'key': 'fine_tier_1_days',
            'value': '3',
            'setting_type': 'number',
            'description': 'Days for tier 1 fine calculation (1-3 days)',
        },
        {
            'key': 'fine_tier_1_rate',
            'value': '2.00',
            'setting_type': 'decimal',
            'description': 'Fine rate per day for tier 1 (1-3 days overdue)',
        },
        {
            'key': 'fine_tier_2_days',
            'value': '7',
            'setting_type': 'number',
            'description': 'Days for tier 2 fine calculation (4-7 days)',
        },
        {
            'key': 'fine_tier_2_rate',
            'value': '5.00',
            'setting_type': 'decimal',
            'description': 'Fine rate per day for tier 2 (4-7 days overdue)',
        },
        {
            'key': 'fine_tier_3_rate',
            'value': '10.00',
            'setting_type': 'decimal',
            'description': 'Fine rate per day for tier 3 (8+ days overdue)',
        },
        {
            'key': 'damaged_book_processing_fee',
            'value': '50.00',
            'setting_type': 'decimal',
            'description': 'Processing fee added to damaged/lost book fines',
        },
        {
            'key': 'admin_session_timeout_minutes',
            'value': '30',
            'setting_type': 'number',
            'description': 'Session timeout in minutes for admin users',
        },
        {
            'key': 'manager_session_timeout_minutes',
            'value': '30',
            'setting_type': 'number',
            'description': 'Session timeout in minutes for manager users',
        },
        {
            'key': 'member_session_timeout_minutes',
            'value': '15',
            'setting_type': 'number',
            'description': 'Session timeout in minutes for member users',
        },
        {
            'key': 'librarian_session_timeout_minutes',
            'value': '15',
            'setting_type': 'number',
            'description': 'Session timeout in minutes for librarian users',
        },
    ]
    
    # Create settings only if they don't already exist
    for setting_data in default_settings:
        SystemSetting.objects.get_or_create(
            key=setting_data['key'],
            defaults={
                'value': setting_data['value'],
                'setting_type': setting_data['setting_type'],
                'description': setting_data['description'],
                'updated_by': None,  # System-created
            }
        )


def remove_initial_settings(apps, schema_editor):
    """
    Remove the initial settings if migration is reversed.
    """
    SystemSetting = apps.get_model('admin_dashboard', 'SystemSetting')
    
    # List of keys to remove
    settings_to_remove = [
        'max_books_per_user',
        'max_borrowing_days',
        'fine_per_day',
        'reservation_timeout_hours',
        'session_timeout_minutes',
        'pickup_code_expiry_days',
        'fine_tier_1_days',
        'fine_tier_1_rate',
        'fine_tier_2_days',
        'fine_tier_2_rate',
        'fine_tier_3_rate',
        'damaged_book_processing_fee',
        'admin_session_timeout_minutes',
        'manager_session_timeout_minutes',
        'member_session_timeout_minutes',
        'librarian_session_timeout_minutes',
    ]
    
    # Remove only settings that were created by this migration
    # (we don't want to remove user-customized settings)
    SystemSetting.objects.filter(
        key__in=settings_to_remove,
        updated_by__isnull=True  # Only remove system-created settings
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('admin_dashboard', '0005_update_audit_log_actions'),
    ]

    operations = [
        migrations.RunPython(
            create_initial_settings,
            remove_initial_settings,
            elidable=True,
        ),
    ]