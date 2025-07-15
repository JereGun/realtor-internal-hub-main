from django import forms
from django.utils import formats
from .models import Contract, ContractIncrease # Removed Invoice, InvoiceItem


class DateInput(forms.DateInput):
    def format_value(self, value):
        if isinstance(value, str):
            # Convertir el formato dd/MM/yyyy a yyyy-MM-dd
            try:
                parts = value.split('/')
                if len(parts) == 3:
                    return f"{parts[2]}-{parts[1]}-{parts[0]}"
            except:
                pass
        return super().format_value(value)


class ContractForm(forms.ModelForm):
    class Meta:
        model = Contract
        fields = [
            'property', 'customer', 'agent', 'start_date', 'end_date', 'amount', 
            'currency', 'frequency', 'increase_percentage', 'next_increase_date', 
            'terms', 'notes', 'status'
        ]
        widgets = {
            'property': forms.Select(attrs={'class': 'form-control', 'id': 'id_property'}),
            'customer': forms.Select(attrs={'class': 'form-control'}),
            'agent': forms.Select(attrs={'class': 'form-control','id': 'id_agent'}),
            'start_date': DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'end_date': DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'id': 'id_amount'}),
            'currency': forms.TextInput(attrs={'class': 'form-control'}),
            'frequency': forms.Select(attrs={'class': 'form-control'}),
            'increase_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'next_increase_date': DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'terms': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:

            if self.instance.status in [Contract.STATUS_FINISHED, Contract.STATUS_CANCELLED]:
                self.fields['status'].widget.attrs['disabled'] = True
        
        # Ensure status choices are correctly populated
        self.fields['status'].choices = Contract.STATUS_CHOICES
        from agents.models import Agent
        self.fields['agent'].queryset = Agent.objects.filter(is_active=True).order_by('first_name', 'last_name')
        self.fields['agent'].empty_label = None 


class ContractIncreaseForm(forms.ModelForm):
    class Meta:
        model = ContractIncrease
        exclude = ['created_at', 'updated_at', 'contract']
        widgets = {
            'previous_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'new_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'increase_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'effective_date': DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ContractSearchForm(forms.Form):
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Buscar contratos...'})
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