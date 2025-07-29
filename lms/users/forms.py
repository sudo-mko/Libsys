from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User

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
