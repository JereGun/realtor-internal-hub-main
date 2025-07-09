from django import forms
from .models import Contract, ContractIncrease, Invoice, InvoiceItem


class ContractForm(forms.ModelForm):
    class Meta:
        model = Contract
        exclude = ['created_at', 'updated_at']
        widgets = {
            'property': forms.Select(attrs={'class': 'form-control'}),
            'customer': forms.Select(attrs={'class': 'form-control'}),
            'agent': forms.Select(attrs={'class': 'form-control'}),
            'contract_type': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'currency': forms.TextInput(attrs={'class': 'form-control'}),
            'terms': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ContractIncreaseForm(forms.ModelForm):
    class Meta:
        model = ContractIncrease
        exclude = ['created_at', 'updated_at', 'contract']
        widgets = {
            'previous_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'new_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'increase_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'effective_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ContractSearchForm(forms.Form):
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Buscar contratos...'})
    )
    contract_type = forms.ChoiceField(
        choices=[('', 'Todos los tipos')] + Contract.CONTRACT_TYPES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    is_active = forms.ChoiceField(
        choices=[('', 'Todos'), ('true', 'Activos'), ('false', 'Inactivos')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['due_date', 'status', 'notes']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }


class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        fields = ['description', 'amount']
