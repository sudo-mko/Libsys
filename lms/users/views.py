from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
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
            return render(request, 'membership.html')
        
        # Map frontend plan names to database membership names
        plan_mapping = {
            'student': 'Student Member',
            'basic': 'Basic Member',
            'premium': 'Premium Member'
        }
        
        if selected_plan in plan_mapping:
            membership_name = plan_mapping[selected_plan]
            
            try:
                # Fetch the existing membership type from database
                membership_type = MembershipType.objects.get(name=membership_name)
                
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
                messages.error(request, f"Membership type '{membership_name}' not found. Please contact support.")
        else:
            messages.error(request, "Invalid membership plan selected.")
    
    return render(request, 'membership.html')


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
    from django.contrib.auth.forms import UserCreationForm
    
    if request.method == 'POST':
        # Get form data
        username = request.POST.get('username')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        role = request.POST.get('role')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        # Basic validation
        errors = []
        if not username:
            errors.append('Username is required.')
        if not first_name:
            errors.append('First name is required.')
        if not last_name:
            errors.append('Last name is required.')
        if not email:
            errors.append('Email is required.')
        if not role:
            errors.append('Role is required.')
        if not password1:
            errors.append('Password is required.')
        if password1 != password2:
            errors.append('Passwords do not match.')
        
        # Check if username already exists
        if User.objects.filter(username=username).exists():
            errors.append('Username already exists.')
        
        # Check if email already exists
        if User.objects.filter(email=email).exists():
            errors.append('Email already exists.')
        
        if errors:
            for error in errors:
                messages.error(request, error)
            # Return form data for re-display
            context = {
                'form': {
                    'username': {'value': username},
                    'first_name': {'value': first_name},
                    'last_name': {'value': last_name},
                    'email': {'value': email},
                    'phone_number': {'value': phone_number},
                    'role': {'value': role},
                    'username': {'errors': []},
                    'first_name': {'errors': []},
                    'last_name': {'errors': []},
                    'email': {'errors': []},
                    'phone_number': {'errors': []},
                    'role': {'errors': []},
                    'password1': {'errors': []},
                    'password2': {'errors': []},
                }
            }
            return render(request, 'manager/create_user.html', context)
        
        try:
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password1,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                role=role
            )
            messages.success(request, f'User {username} created successfully!')
            return redirect('users:user_list')
        except Exception as e:
            messages.error(request, f'Error creating user: {str(e)}')
            return render(request, 'manager/create_user.html', {'form': {}})
    else:
        context = {'form': {}}
    
    return render(request, 'manager/create_user.html', context)

@login_required
def manage_memberships(request):
    if request.user.role != 'manager':
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("You don't have permission to manage memberships.")
    
    from users.models import User, MembershipType
    
    # Get all users with their membership info
    users = User.objects.select_related('membership').all()
    membership_types = MembershipType.objects.all()
    
    context = {
        'users': users,
        'membership_types': membership_types,
    }
    
    return render(request, 'manager/manage_memberships.html', context)

# @login_required
# def unlock_accounts(request):
#     if request.user.role != 'manager':
#         from django.http import HttpResponseForbidden
#         return HttpResponseForbidden("You don't have permission to unlock accounts.")
    
#     from users.models import User
#     from django.contrib import messages
    
#     # Get locked accounts
#     locked_users = User.objects.filter(account_locked_until__isnull=False)
    
#     if request.method == 'POST':
#         user_id = request.POST.get('user_id')
#         if user_id:
#             try:
#                 user = User.objects.get(id=user_id)
#                 user.reset_lock_status()
#                 messages.success(request, f'Account for {user.username} has been unlocked.')
#             except User.DoesNotExist:
#                 messages.error(request, 'User not found.')
    
#     context = {
#         'locked_users': locked_users,
#     }
    
#     return render(request, 'manager/unlock_accounts.html', context)

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
        user.role = request.POST.get('role', 'member')
        user.phone_number = request.POST.get('phone_number', '')
        
        try:
            user.save()
            messages.success(request, f'User {user.username} updated successfully!')
            return redirect('users:user_list')
        except Exception as e:
            messages.error(request, f'Error updating user: {str(e)}')
    
    context = {
        'user': user,
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




