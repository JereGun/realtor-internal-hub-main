from django import forms
from .models import Contract, ContractIncrease # Removed Invoice, InvoiceItem


class ContractForm(forms.ModelForm):
    class Meta:
        model = Contract
        exclude = ['created_at', 'updated_at'] # is_active was implicitly excluded, now status is included by default
        fields = [
            'property', 'customer', 'agent', 'contract_type', 'start_date', 
            'end_date', 'amount', 'currency', 'terms', 'notes', 'status'
        ]
        widgets = {
            'property': forms.Select(attrs={'class': 'form-control'}),
            'customer': forms.Select(attrs={'class': 'form-control'}),
            'agent': forms.Select(attrs={'class': 'form-control'}), # Consider filtering agents if needed
            'contract_type': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'currency': forms.TextInput(attrs={'class': 'form-control'}), # Could be Select if limited choices
            'terms': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If agent is linked to request.user, it might be better to set it in the view
        # and make the field read-only or not included in the form if it's always the current user.
        # For now, assuming agent is selectable or pre-filled as needed.
        if self.instance and self.instance.pk: # For existing instances
             # Make status read-only if contract is finished or cancelled?
            if self.instance.status in [Contract.STATUS_FINISHED, Contract.STATUS_CANCELLED]:
                self.fields['status'].widget.attrs['disabled'] = True
                # Or for all fields:
                # for field_name in self.fields:
                #     self.fields[field_name].widget.attrs['disabled'] = True
        
        # Ensure status choices are correctly populated
        self.fields['status'].choices = Contract.STATUS_CHOICES


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
    status = forms.ChoiceField(
        # Add 'All' option dynamically
        choices=[], 
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Prepend 'All' option to status choices
        status_choices = [('', 'Todos los Estados')] + Contract.STATUS_CHOICES
        self.fields['status'].choices = status_choices

# Removed InvoiceForm and InvoiceItemForm as Invoice models are now managed by 'accounting' app.
# Their logic should be in accounting/forms.py