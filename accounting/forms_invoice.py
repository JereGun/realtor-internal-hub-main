from django import forms
from .models_invoice import Invoice, InvoiceLine
from django.forms.models import inlineformset_factory

class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = [
            'number', 'date', 'due_date', 'customer', 'description', 'total_amount', 'state'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }

class InvoiceLineForm(forms.ModelForm):
    class Meta:
        model = InvoiceLine
        fields = ['concept', 'amount']
        widgets = {
            'concept': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'style': 'min-width:90px;'}),
        }

InvoiceLineFormSet = inlineformset_factory(
    Invoice,
    InvoiceLine,
    form=InvoiceLineForm,
    fields=['concept', 'amount'],
    extra=1,
    can_delete=True
)
