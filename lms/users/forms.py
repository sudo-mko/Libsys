from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.validators import RegexValidator
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User, MembershipType

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'phone_number', 'password1', 'password2']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply consistent styling to all form fields
        field_styling = 'w-full h-12 px-4 py-3 border border-[#D1D5DB] rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:border-indigo-600'
        
        self.fields['username'].widget.attrs.update({
            'class': field_styling,
            'placeholder': 'Enter your username'
        })
        self.fields['email'].widget.attrs.update({
            'class': field_styling,
            'placeholder': 'Enter your email'
        })
        self.fields['first_name'].widget.attrs.update({
            'class': field_styling,
            'placeholder': 'Enter your first name'
        })
        self.fields['last_name'].widget.attrs.update({
            'class': field_styling,
            'placeholder': 'Enter your last name'
        })
        self.fields['phone_number'].widget.attrs.update({
            'class': field_styling,
            'placeholder': 'Enter your phone number'
        })
        self.fields['password1'].widget.attrs.update({
            'class': field_styling,
            'placeholder': '••••••••'
        })
        self.fields['password2'].widget.attrs.update({
            'class': field_styling,
            'placeholder': '••••••••'
        })

class AdminUserCreationForm(UserCreationForm):
    """Form for admin/manager to create users with proper validation"""
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(
        max_length=20,
        required=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message='Phone number must be entered in the format: +999999999. Up to 15 digits allowed.'
            )
        ],
        help_text='Enter phone number in international format (e.g., +1234567890)'
    )
    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
        required=True,
        help_text='Select the user role'
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'phone_number', 'role', 'password1', 'password2']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply consistent styling to all form fields
        field_styling = 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
        
        self.fields['username'].widget.attrs.update({
            'class': field_styling,
            'placeholder': 'Enter username'
        })
        self.fields['email'].widget.attrs.update({
            'class': field_styling,
            'placeholder': 'Enter email address'
        })
        self.fields['first_name'].widget.attrs.update({
            'class': field_styling,
            'placeholder': 'Enter first name'
        })
        self.fields['last_name'].widget.attrs.update({
            'class': field_styling,
            'placeholder': 'Enter last name'
        })
        self.fields['phone_number'].widget.attrs.update({
            'class': field_styling,
            'placeholder': 'Enter phone number (e.g., +1234567890)'
        })
        self.fields['role'].widget.attrs.update({
            'class': field_styling
        })
        self.fields['password1'].widget.attrs.update({
            'class': field_styling,
            'placeholder': '••••••••'
        })
        self.fields['password2'].widget.attrs.update({
            'class': field_styling,
            'placeholder': '••••••••'
        })
        
        # Add help text for password requirements
        self.fields['password1'].help_text = (
            'Password must contain at least 8 characters, including uppercase, lowercase, '
            'numbers, and special characters.'
        )
        self.fields['password2'].help_text = 'Enter the same password as before, for verification.'
    
    def clean_phone_number(self):
        """Validate phone number format"""
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number:
            # Remove any spaces or special characters except + and digits
            cleaned_phone = ''.join(c for c in phone_number if c.isdigit() or c == '+')
            if len(cleaned_phone) < 10:
                raise ValidationError('Phone number must be at least 10 digits long.')
            if len(cleaned_phone) > 15:
                raise ValidationError('Phone number cannot exceed 15 digits.')
        return phone_number
    
    def clean_password1(self):
        """Validate password strength"""
        password = self.cleaned_data.get('password1')
        if password:
            # Use Django's built-in password validation
            validate_password(password)
            
            # Additional custom validation
            if len(password) < 8:
                raise ValidationError('Password must be at least 8 characters long.')
            
            if not any(c.isupper() for c in password):
                raise ValidationError('Password must contain at least one uppercase letter.')
            
            if not any(c.islower() for c in password):
                raise ValidationError('Password must contain at least one lowercase letter.')
            
            if not any(c.isdigit() for c in password):
                raise ValidationError('Password must contain at least one number.')
            
            if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
                raise ValidationError('Password must contain at least one special character.')
        
        return password
    
    def clean(self):
        """Additional validation for the entire form"""
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        email = cleaned_data.get('email')
        
        # Check for existing username
        if username and User.objects.filter(username=username).exists():
            raise ValidationError({'username': 'A user with this username already exists.'})
        
        # Check for existing email
        if email and User.objects.filter(email=email).exists():
            raise ValidationError({'email': 'A user with this email already exists.'})
        
        return cleaned_data

class UserLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'w-full h-12 px-4 py-3 border border-[#D1D5DB] rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:border-indigo-600',
        'placeholder': 'Enter your username'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'w-full h-12 px-4 py-3 border border-[#D1D5DB] rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:border-indigo-600',
        'placeholder': '••••••••'
    }))

class MembershipTypeForm(forms.ModelForm):
    class Meta:
        model = MembershipType
        fields = ['name', 'monthly_fee', 'annual_fee', 'max_books', 'loan_period_days', 'extension_days']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'e.g., Premium Member'
            }),
            'monthly_fee': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'min': '0',
                'max': '10000',
                'step': '0.01',
                'placeholder': '19.99'
            }),
            'annual_fee': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'min': '0',
                'max': '100000',
                'step': '0.01',
                'placeholder': '199.99'
            }),
            'max_books': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'min': '1',
                'max': '100',
                'placeholder': '5'
            }),
            'loan_period_days': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'min': '1',
                'max': '365',
                'placeholder': '14'
            }),
            'extension_days': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'min': '1',
                'max': '365',
                'placeholder': '7'
            }),
        }
        labels = {
            'name': 'Name *',
            'monthly_fee': 'Monthly Fee (MVR) *',
            'annual_fee': 'Annual Fee (MVR) *',
            'max_books': 'Max Books *',
            'loan_period_days': 'Loan Period (Days) *',
            'extension_days': 'Extension Days *',
        }
