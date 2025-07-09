from django import forms
from .models_invoice import InvoiceLine

class InvoiceLineForm(forms.ModelForm):
    class Meta:
        model = InvoiceLine
        fields = [
            'concept', 'amount'
        ]
        widgets = {
            'concept': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'style': 'min-width:90px;'}),
        }
