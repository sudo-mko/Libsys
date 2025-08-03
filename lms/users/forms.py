from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
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
