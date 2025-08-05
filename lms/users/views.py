from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from decimal import Decimal, InvalidOperation
from .forms import UserRegistrationForm, UserLoginForm
from .models import User, MembershipType

# Create your views here.

def register_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, "Registration successful!")
            
            # Redirect admin users to admin dashboard, others to library home
            if user.role == 'admin':
                from django.urls import reverse
                return redirect(reverse('admin_dashboard:dashboard'))
            else:
                return redirect('library:home')
        else:
            messages.error(request, "Registration failed. Please correct the errors.")
    else:
        form = UserRegistrationForm()
    return render(request, 'register.html', {'form': form})

def login_view(request):
    lock_context = {}
    
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        username = request.POST.get('username', '')
        
        # Get the user to check lock status
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = None
            
        if user and user.is_account_locked():
            remaining_seconds = user.get_lock_remaining_seconds()
            minutes = remaining_seconds // 60
            seconds = remaining_seconds % 60
            
            lock_context = {
                'is_locked': True,
                'remaining_seconds': remaining_seconds,
                'lock_message': f"Account is locked. Try again in {minutes}m {seconds}s"
            }
            messages.error(request, f"Account is locked due to too many failed login attempts. Please try again in {minutes} minutes and {seconds} seconds.")
        else:
            # Process login attempt - handle both valid and invalid forms
            # Try to authenticate regardless of form validation
            password = request.POST.get('password', '')
            authenticated_user = authenticate(username=username, password=password)
            
            if authenticated_user is not None:
                # Reset lock status on successful login (but keep failed attempts for analytics)
                authenticated_user.reset_lock_status()
                
                # Mark admin login time for password change delay
                if authenticated_user.role == 'admin':
                    authenticated_user.mark_admin_login(request)
                
                login(request, authenticated_user, backend='django.contrib.auth.backends.ModelBackend')
                messages.success(request, f"Welcome back, {username}!")
                
                # Redirect admin users to admin dashboard, others to library home
                if authenticated_user.role == 'admin':
                    from django.urls import reverse
                    return redirect(reverse('admin_dashboard:dashboard'))
                else:
                    return redirect('library:home')
            else:
                # Invalid credentials - increment failed attempts for the existing user
                if user:  # user was already fetched at the top
                    user.increment_failed_attempts()
                    
                    # Check if user should get a warning
                    if user.should_show_warning() and not user.is_account_locked():
                        lock_settings = getattr(settings, 'ACCOUNT_LOCK_SETTINGS', {})
                        max_attempts = lock_settings.get('MAX_FAILED_ATTEMPTS', 5)
                        remaining_attempts = max_attempts - user.failed_login_attempts
                        messages.warning(request, f"Warning: {remaining_attempts} more failed attempts will lock your account for 5 minutes.")
                    elif user.is_account_locked():
                        remaining_seconds = user.get_lock_remaining_seconds()
                        minutes = remaining_seconds // 60
                        seconds = remaining_seconds % 60
                        lock_context = {
                            'is_locked': True,
                            'remaining_seconds': remaining_seconds,
                            'lock_message': f"Account is locked. Try again in {minutes}m {seconds}s"
                        }
                        messages.error(request, f"Account locked due to too many failed attempts. Try again in {minutes} minutes and {seconds} seconds.")
                
                if not lock_context.get('is_locked'):
                    messages.error(request, "Invalid username or password.")
    else:
        form = UserLoginForm()
    
    context = {
        'form': form,
        **lock_context
    }
    return render(request, 'login.html', context)

def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully!")
    return redirect('library:home')

@login_required
def profile_view(request):
    user = request.user
    if not user.is_authenticated:
        return redirect('login')
    if user.role == 'admin':
        users = User.objects.all()
        selected_user_id = request.GET.get('user_id')
        selected_user = None
        if selected_user_id:
            try:
                selected_user = User.objects.get(id=selected_user_id)
            except User.DoesNotExist:
                selected_user = None
        return render(request, 'profile.html', {
            'is_admin': True,
            'users': users,
            'selected_user': selected_user,
        })
    else:
        return render(request, 'profile.html', {
            'is_admin': False,
            'user': user,
        })
@login_required
def membership_view(request):
    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, "Please log in to select a membership.")
            return redirect('users:login')
        
        selected_plan = request.POST.get('selected_plan')
        
        if not selected_plan:
            messages.error(request, "Please select a membership plan.")
            # Get membership types for template context
            membership_types = MembershipType.objects.all().order_by('monthly_fee')
            return render(request, 'membership.html', {'membership_types': membership_types})
        
        try:
            # Get membership type directly by ID
            membership_type = MembershipType.objects.get(id=selected_plan)
            
            # Assign membership to user
            old_membership = request.user.membership
            request.user.membership = membership_type
            request.user.save()
            
            if old_membership:
                messages.success(request, f"Your membership has been updated from {old_membership.name} to {membership_type.name}!")
            else:
                messages.success(request, f"Welcome to {membership_type.name} membership! Your account has been upgraded.")
            
            return redirect('users:membership')
            
        except MembershipType.DoesNotExist:
            messages.error(request, "Selected membership type not found. Please contact support.")
        except Exception as e:
            messages.error(request, f"Error updating membership: {str(e)}")
    
    # Get all membership types from database for display
    membership_types = MembershipType.objects.all().order_by('monthly_fee')
    
    context = {
        'membership_types': membership_types,
    }
    
    return render(request, 'membership.html', context)


@login_required
def manage_users(request):
    # Check if user has permission to manage users (manager only)
    if request.user.role != 'manager':
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("You don't have permission to manage users.")
    
    from users.models import User, MembershipType
    from django.db.models import Count, Q
    from datetime import datetime, timedelta
    
    # Get search and filter parameters
    search_query = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')
    
    # Base queryset
    users = User.objects.filter(role__in=['member', 'librarian'])
    
    # Apply filters
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    if role_filter:
        users = users.filter(role=role_filter)
    
    if status_filter == 'locked':
        users = users.filter(account_locked_until__isnull=False)
    elif status_filter == 'active':
        users = users.filter(account_locked_until__isnull=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    
    # Calculate statistics
    total_users = User.objects.count()
    active_members = User.objects.filter(role='member', membership__isnull=False).count()
    staff_members = User.objects.filter(role__in=['librarian', 'manager', 'admin']).count()
    locked_accounts = User.objects.filter(account_locked_until__isnull=False).count()
    
    # Role distribution
    role_distribution = User.objects.filter(role__in=['member', 'librarian']).values('role').annotate(
    count=Count('id')
    ).order_by('role')
    
    # Calculate percentages for role distribution
    total_for_percentage = sum(role['count'] for role in role_distribution)
    for role in role_distribution:
        role['percentage'] = round((role['count'] / total_for_percentage) * 100) if total_for_percentage > 0 else 0
        role['name'] = role['role'].title()
        role['role_type'] = 'Staff' if role['role'] in ['librarian', 'manager', 'admin'] else 'Member'
    
    # Account status
    active_accounts = User.objects.filter(account_locked_until__isnull=True, is_active=True).count()
    inactive_accounts = User.objects.filter(is_active=False).count()
    
    # Recent activity (last 30 days)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    new_registrations = User.objects.filter(created_at__gte=thirty_days_ago).count()
    
    # Membership upgrades (users who got membership in last 30 days)
    membership_upgrades = User.objects.filter(
        membership__isnull=False,
        created_at__gte=thirty_days_ago
    ).count()
    
    # Account locks in last 30 days
    account_locks = User.objects.filter(
        account_locked_until__isnull=False,
        last_failed_attempt__gte=thirty_days_ago
    ).count()
    
    context = {
        'users': users,
        'total_users': total_users,
        'active_members': active_members,
        'staff_members': staff_members,
        'locked_accounts': locked_accounts,
        'role_distribution': role_distribution,
        'active_accounts': active_accounts,
        'inactive_accounts': inactive_accounts,
        'new_registrations': new_registrations,
        'membership_upgrades': membership_upgrades,
        'account_locks': account_locks,
    }
    
    return render(request, 'manager/manage_user.html', context)

@login_required
def create_user(request):
    if request.user.role not in ['manager', 'admin']:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("You don't have permission to create users.")
    
    from django.contrib import messages
    from .forms import AdminUserCreationForm
    
    if request.method == 'POST':
        form = AdminUserCreationForm(request.POST, current_user=request.user)
        if form.is_valid():
            try:
                # Create user with proper validation
                user = form.save(commit=False)
                user.set_password(form.cleaned_data['password1'])
                user.save()
                
                messages.success(request, f'User {user.username} created successfully!')
                return redirect('users:user_list')
            except Exception as e:
                messages.error(request, f'Error creating user: {str(e)}')
        else:
            # Form validation failed - errors will be displayed in template
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = AdminUserCreationForm(current_user=request.user)
    
    context = {'form': form}
    return render(request, 'manager/create_user.html', context)

@login_required
def manage_memberships(request):
    """Main membership management dashboard with comprehensive functionality"""
    if request.user.role not in ['manager', 'admin']:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("You don't have permission to manage memberships.")
    
    from django.db.models import Q, Count
    from django.urls import reverse
    from .forms import MembershipTypeForm
    import re
    
    # Get search and filter parameters
    search_query = request.GET.get('search', '').strip()
    membership_filter = request.GET.get('membership', '')
    
    # Handle tab and edit state
    active_tab = request.GET.get('tab', 'users')
    edit_id = request.GET.get('edit', '')
    edit_membership = None
    
    if edit_id and edit_id.isdigit():
        try:
            edit_membership = MembershipType.objects.get(id=edit_id)
            active_tab = 'types'  # Switch to types tab when editing
        except MembershipType.DoesNotExist:
            messages.error(request, "Membership type not found")
    
    # Handle form submissions
    create_form = MembershipTypeForm()
    edit_form = None
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create':
            create_form = MembershipTypeForm(request.POST)
            if create_form.is_valid():
                create_form.save()
                messages.success(request, f"Membership type '{create_form.cleaned_data['name']}' created successfully!")
                return redirect(f"{reverse('users:manage_memberships')}?tab=types")
            else:
                active_tab = 'types'
                
        elif action == 'edit' and edit_membership:
            edit_form = MembershipTypeForm(request.POST, instance=edit_membership)
            if edit_form.is_valid():
                edit_form.save()
                messages.success(request, f"Membership type '{edit_form.cleaned_data['name']}' updated successfully!")
                return redirect(f"{reverse('users:manage_memberships')}?tab=types")
            else:
                active_tab = 'types'
    
    # Create edit form if editing
    if edit_membership:
        edit_form = MembershipTypeForm(instance=edit_membership)
    
    # Base queryset - only members and librarians
    users_queryset = User.objects.filter(role__in=['member', 'librarian']).select_related('membership')
    
    # Apply search filter
    if search_query:
        users_queryset = users_queryset.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # Apply membership filter
    if membership_filter == 'no_membership':
        users_queryset = users_queryset.filter(membership__isnull=True)
    elif membership_filter and membership_filter.isdigit():
        users_queryset = users_queryset.filter(membership_id=membership_filter)
    
    # Get all users for processing (handle corrupted data gracefully)
    users_list = []
    corrupted_data_count = 0
    
    for user in users_queryset:
        try:
            # Validate membership data if exists
            if user.membership:
                # Test decimal fields for corruption
                test_monthly = Decimal(str(user.membership.monthly_fee))
                test_annual = Decimal(str(user.membership.annual_fee))
                
            users_list.append(user)
        except (InvalidOperation, ValueError) as e:
            corrupted_data_count += 1
            continue
    
    # Get all membership types with validation
    membership_types_list = []
    corrupted_types_count = 0
    
    for membership_type in MembershipType.objects.all():
        try:
            # Validate decimal fields
            test_monthly = Decimal(str(membership_type.monthly_fee))
            test_annual = Decimal(str(membership_type.annual_fee))
            membership_types_list.append(membership_type)
        except (InvalidOperation, ValueError):
            corrupted_types_count += 1
            continue
    
    # Calculate statistics
    total_users_with_membership = len([u for u in users_list if u.membership])
    total_users_without_membership = len([u for u in users_list if not u.membership])
    total_membership_types = len(membership_types_list)
    
    # Membership distribution
    membership_distribution = {}
    for user in users_list:
        if user.membership:
            name = user.membership.name
            membership_distribution[name] = membership_distribution.get(name, 0) + 1
    
    # Most popular membership
    most_popular_membership = max(membership_distribution.items(), key=lambda x: x[1]) if membership_distribution else None
    
    # Add warning messages for corrupted data
    if corrupted_data_count > 0:
        messages.warning(request, f"Warning: {corrupted_data_count} users with corrupted membership data were skipped.")
    
    if corrupted_types_count > 0:
        messages.warning(request, f"Warning: {corrupted_types_count} membership types with corrupted data were skipped.")
    
    context = {
        'users': users_list,
        'membership_types': membership_types_list,
        'search_query': search_query,
        'membership_filter': membership_filter,
        
        # Statistics
        'total_users_with_membership': total_users_with_membership,
        'total_users_without_membership': total_users_without_membership,
        'total_membership_types': total_membership_types,
        'membership_distribution': membership_distribution,
        'most_popular_membership': most_popular_membership,
        
        # Additional data
        'total_users': len(users_list),
        
        # Tab and form state
        'active_tab': active_tab,
        'create_form': create_form,
        'edit_form': edit_form,
        'edit_membership': edit_membership,
    }
    
    return render(request, 'manager/manage_memberships.html', context)





@login_required
def update_membership(request):
    """Handle inline membership assignment for users"""
    if request.user.role not in ['manager', 'admin']:
        from django.http import JsonResponse
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        membership_id = request.POST.get('membership_id')
        
        try:
            user = User.objects.get(id=user_id)
            
            if membership_id == '' or membership_id == 'none':
                # Remove membership
                old_membership = user.membership.name if user.membership else None
                user.membership = None
                user.save()
                messages.success(request, f"Membership removed from {user.get_full_name() or user.username}")
            else:
                # Assign new membership
                membership_type = MembershipType.objects.get(id=membership_id)
                old_membership = user.membership.name if user.membership else None
                user.membership = membership_type
                user.save()
                
                if old_membership:
                    messages.success(request, f"Membership updated from {old_membership} to {membership_type.name} for {user.get_full_name() or user.username}")
                else:
                    messages.success(request, f"Membership {membership_type.name} assigned to {user.get_full_name() or user.username}")
            
            return redirect('users:manage_memberships')
            
        except User.DoesNotExist:
            messages.error(request, "User not found")
        except MembershipType.DoesNotExist:
            messages.error(request, "Membership type not found")
        except Exception as e:
            messages.error(request, f"Error updating membership: {str(e)}")
    
    return redirect('users:manage_memberships')





@login_required
def delete_membership_type(request, membership_id):
    """Delete a membership type with safety checks"""
    if request.user.role not in ['manager', 'admin']:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("You don't have permission to manage membership types.")
    
    try:
        membership_type = MembershipType.objects.get(id=membership_id)
        
        # Check if any users are assigned to this membership type
        user_count = User.objects.filter(membership=membership_type).count()
        
        if user_count > 0:
            messages.error(request, f"Cannot delete membership type '{membership_type.name}' because {user_count} user(s) are currently assigned to it. Please reassign these users first.")
        else:
            name = membership_type.name
            membership_type.delete()
            messages.success(request, f"Membership type '{name}' deleted successfully!")
            
    except MembershipType.DoesNotExist:
        messages.error(request, "Membership type not found")
    except Exception as e:
        messages.error(request, f"Error deleting membership type: {str(e)}")
    
    return redirect('users:manage_memberships')


@login_required
def unlock_accounts(request):
    """View for managing locked accounts (Manager + Admin access)"""
    if request.user.role not in ['manager', 'admin']:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("You don't have permission to manage locked accounts.")
    
    from users.models import User
    from django.db.models import Q
    
    # Handle GET parameters for lock user form
    lock_user_id = request.GET.get('lock')
    lock_user = None
    if lock_user_id and lock_user_id.isdigit() and request.user.role == 'admin':
        try:
            lock_user = User.objects.get(
                id=lock_user_id,
                account_locked_until__isnull=True,
                role__in=['member', 'librarian']
            )
        except User.DoesNotExist:
            messages.error(request, "User not found or not eligible for locking")

    # Handle POST requests for unlock/lock actions
    if request.method == 'POST':
        action = request.POST.get('action')
        user_id = request.POST.get('user_id')
        reason = request.POST.get('reason', '')
        
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                
                if action == 'unlock':
                    user.reset_lock_status(performed_by=request.user, reason=reason)
                    messages.success(request, f'Account for {user.get_full_name() or user.username} has been unlocked.')
                    return redirect('users:unlock_accounts')
                
                elif action == 'lock' and request.user.role == 'admin':
                    duration_minutes = request.POST.get('duration_minutes')
                    try:
                        duration = int(duration_minutes) if duration_minutes else None
                    except ValueError:
                        duration = None
                    
                    user.lock_account_manually(
                        performed_by=request.user,
                        reason=reason,
                        duration_minutes=duration
                    )
                    messages.success(request, f'Account for {user.get_full_name() or user.username} has been locked.')
                    return redirect('users:unlock_accounts')
                
                else:
                    messages.error(request, 'Invalid action or insufficient permissions.')
                    
            except User.DoesNotExist:
                messages.error(request, 'User not found.')
            except Exception as e:
                messages.error(request, f'Error performing action: {str(e)}')
    
    # Get search parameter
    search_query = request.GET.get('search', '').strip()
    
    # Get locked accounts with user details
    locked_users = User.objects.filter(account_locked_until__isnull=False).select_related('membership')
    
    # Apply search filter
    if search_query:
        locked_users = locked_users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # Get all users for admin lock functionality (excluding locked ones)
    all_users = User.objects.filter(
        account_locked_until__isnull=True,
        role__in=['member', 'librarian']
    ).select_related('membership') if request.user.role == 'admin' else None
    
    # Apply search to all users too
    if all_users and search_query:
        all_users = all_users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    

    
    # Statistics
    total_locked = User.objects.filter(account_locked_until__isnull=False).count()
    locked_today = User.objects.filter(
        account_locked_until__isnull=False,
        last_failed_attempt__date=timezone.now().date()
    ).count()
    unlocked_today = 0  # Removed audit log feature
    
    context = {
        'locked_users': locked_users,
        'all_users': all_users,
        'search_query': search_query,
        'is_admin': request.user.role == 'admin',
        'now': timezone.now(),
        'lock_user': lock_user,
        # Statistics
        'total_locked': total_locked,
        'locked_today': locked_today,
        'unlocked_today': unlocked_today,
    }
    
    return render(request, 'manager/unlock_accounts.html', context)

@login_required
def user_list(request):
    if request.user.role not in ['manager', 'admin']:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("You don't have permission to view user list.")
    
    from django.db.models import Q
    from django.core.paginator import Paginator

    if request.method == 'POST' and 'user_id' in request.POST:
        user_id = request.POST.get('user_id')
        try:
            user = User.objects.get(id=user_id)
            user.reset_lock_status()
            messages.success(request, f"Account for {user.username} has been unlocked.")
        except User.DoesNotExist:
            messages.error(request, "User not found.")
        return redirect('users:user_list')
    
    # Get filter parameters
    search_query = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')
    membership_filter = request.GET.get('membership', '')
    
    # Base queryset
    users = User.objects.filter(role__in=['member', 'librarian'])
    
    # Apply filters
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    if role_filter:
        users = users.filter(role=role_filter)
    
    if status_filter == 'locked':
        users = users.filter(account_locked_until__isnull=False)
    elif status_filter == 'active':
        users = users.filter(account_locked_until__isnull=True, is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    
    if membership_filter == 'none':
        users = users.filter(membership__isnull=True)
    elif membership_filter:
        users = users.filter(membership__name__icontains=membership_filter)
    
    # Order by creation date (newest first)
    users = users.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(users, 20)  # 20 users per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get membership types for the modal
    membership_types = MembershipType.objects.all()
    
    # Calculate total users for display
    total_users = User.objects.count()
    
    context = {
        'users': page_obj,
        'total_users': total_users,
        'membership_types': membership_types,
    }
    
    return render(request, 'manager/user_list.html', context)

@login_required
def edit_user(request, user_id):
    if request.user.role != 'manager':
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("You don't have permission to edit users.")
    
    from django.contrib import messages
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('users:user_list')
    
    if request.method == 'POST':
        # Update user fields
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.phone_number = request.POST.get('phone_number', '')
        
        # Handle role changes with permission checks (managers can only assign member/librarian roles)
        new_role = request.POST.get('role', user.role)
        if new_role != user.role:
            if new_role in ['member', 'librarian']:
                user.role = new_role
            else:
                messages.error(request, "As a manager, you can only assign member and librarian roles.")
        
        try:
            user.save()
            messages.success(request, f'User {user.username} updated successfully!')
            return redirect('users:user_list')
        except Exception as e:
            messages.error(request, f'Error updating user: {str(e)}')
    
    # Filter role choices based on manager permissions
    allowed_roles = [
        ('member', 'Library Member'),
        ('librarian', 'Librarian'),
    ]
    
    context = {
        'user': user,
        'role_choices': allowed_roles,
    }
    
    return render(request, 'manager/edit_user.html', context)

@login_required
def delete_user(request, user_id):
    if request.user.role != 'manager':
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("You don't have permission to delete users.")
    
    from django.contrib import messages
    
    try:
        user = User.objects.get(id=user_id)
        
        # Prevent deletion of admin users or self
        if user.role == 'admin':
            messages.error(request, 'Cannot delete admin users.')
            return redirect('users:user_list')
        
        if user == request.user:
            messages.error(request, 'Cannot delete your own account.')
            return redirect('users:user_list')
        
        username = user.username
        user.delete()
        messages.success(request, f'User {username} deleted successfully!')
        
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
    except Exception as e:
        messages.error(request, f'Error deleting user: {str(e)}')
    
    return redirect('users:user_list')




