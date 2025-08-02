from django import forms
from .models import Branch, Section

class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = ['branch_name', 'location']
        widgets = {
            'branch_name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Enter branch name'
            }),
            'location': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Enter branch location'
            })
        }

class SectionForm(forms.ModelForm):
    class Meta:
        model = Section
        fields = ['name', 'branch_id']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Enter section name'
            }),
            'branch_id': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
            })
        } 