
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import Agent


class AgentLoginForm(AuthenticationForm):
    username = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña'})
    )


class AgentForm(forms.ModelForm):
    class Meta:
        model = Agent
        fields = ['first_name', 'last_name', 'email', 'phone', 'license_number', 'commission_rate', 'image_path']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'license_number': forms.TextInput(attrs={'class': 'form-control'}),
            'commission_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'image_path': forms.FileInput(attrs={'class': 'form-control-file'}),
        }
