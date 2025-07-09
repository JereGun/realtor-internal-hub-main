from django import forms
from .models_invoice import Invoice, InvoiceLine
from django.forms.models import inlineformset_factory

class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = [
            'number', 'date', 'due_date', 'customer', 'description', 'total_amount', 'state', 'contract', 'property'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }

InvoiceLineFormSet = inlineformset_factory(
    Invoice,
    InvoiceLine,
    fields=[
        'concept', 'amount'
    ],
    widgets={
        'amount': forms.NumberInput(attrs={'type': 'number'}),
    },
    extra=1,
    can_delete=True
)
