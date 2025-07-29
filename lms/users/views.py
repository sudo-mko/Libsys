from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
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
            login(request, user)
            messages.success(request, "Registration successful!")
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
                login(request, authenticated_user)
                messages.success(request, f"Welcome back, {username}!")
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

