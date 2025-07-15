from django import forms
from django.utils import formats
from .models_invoice import Invoice, InvoiceLine
from django.forms.models import inlineformset_factory

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

class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = [
            'number', 'date', 'due_date', 'customer', 'description', 'total_amount', 'status'
        ]
        widgets = {
            'date': DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'due_date': DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
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
