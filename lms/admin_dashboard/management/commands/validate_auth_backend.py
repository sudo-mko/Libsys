from django.core.management.base import BaseCommand
from django.conf import settings
from admin_dashboard.auth_backends import LibraryManagementAuditAuthBackend


class Command(BaseCommand):
    help = 'Validate the uniqueness and configuration of the custom authentication backend'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed information about the backend configuration',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.HTTP_INFO('=' * 60))
        self.stdout.write(self.style.HTTP_INFO('  AUTHENTICATION BACKEND VALIDATION'))
        self.stdout.write(self.style.HTTP_INFO('=' * 60))
        
        # Get backend info
        backend = LibraryManagementAuditAuthBackend()
        backend_info = backend.get_backend_info()
        
        self.stdout.write('\n📋 Backend Information:')
        self.stdout.write(f'  • ID: {backend_info["id"]}')
        self.stdout.write(f'  • Name: {backend_info["name"]}')
        self.stdout.write(f'  • Version: {backend_info["version"]}')
        self.stdout.write(f'  • Description: {backend_info["description"]}')
        
        if options['verbose']:
            self.stdout.write(f'  • Features: {", ".join(backend_info["features"])}')
        
        # Validate uniqueness
        validation = LibraryManagementAuditAuthBackend.validate_uniqueness()
        
        self.stdout.write('\n🔍 Uniqueness Validation:')
        
        if validation['is_unique']:
            self.stdout.write(self.style.SUCCESS('  ✅ Backend is uniquely configured'))
        else:
            self.stdout.write(self.style.ERROR('  ❌ Backend configuration conflicts detected'))
        
        # Show conflicts
        if validation['conflicts']:
            self.stdout.write('\n⚠️  Conflicts:')
            for conflict in validation['conflicts']:
                self.stdout.write(self.style.ERROR(f'  • {conflict}'))
        
        # Show warnings
        if validation['warnings']:
            self.stdout.write('\n🔶 Warnings:')
            for warning in validation['warnings']:
                self.stdout.write(self.style.WARNING(f'  • {warning}'))
        
        # Show current configuration
        self.stdout.write('\n⚙️  Current Authentication Backend Configuration:')
        auth_backends = getattr(settings, 'AUTHENTICATION_BACKENDS', [])
        for i, backend in enumerate(auth_backends, 1):
            status = '🟢' if i == 1 else '🔵'
            self.stdout.write(f'  {status} {i}. {backend}')
        
        if not validation['conflicts'] and not validation['warnings']:
            self.stdout.write(self.style.SUCCESS('\n🎉 All checks passed! Backend is properly configured.'))
        elif validation['conflicts']:
            self.stdout.write(self.style.ERROR('\n❌ Critical issues found. Please fix conflicts.'))
            return 1
        else:
            self.stdout.write(self.style.WARNING('\n⚠️  Minor issues detected. Consider reviewing warnings.'))
        
        self.stdout.write('\n' + '=' * 60)
        return 0