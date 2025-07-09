from django import forms
from .models import Invoice, InvoiceItem, Payment
from customers.models import Customer

class InvoiceForm(forms.ModelForm):
    customer = forms.ModelChoiceField(queryset=Customer.objects.all(), label="Cliente", widget=forms.Select(attrs={'class': 'form-control'}))
    class Meta:
        model = Invoice
        fields = ['customer', 'contract', 'name', 'invoice_date', 'invoice_date_due', 'state']
        widgets = {
            'contract': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nro de Factura'}),
            'invoice_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'placeholder': 'Fecha de emisión'}),
            'invoice_date_due': forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'placeholder': 'Fecha de vencimiento'}),
            'state': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': 'Nro de Factura',
            'invoice_date': 'Fecha de emisión',
            'invoice_date_due': 'Fecha de vencimiento',
            'state': 'Estado',
        }

class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        fields = ['name', 'quantity', 'price_unit']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Descripción'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'price_unit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Precio Unitario'}),
        }
        labels = {
            'name': 'Descripción',
            'quantity': 'Cantidad',
            'price_unit': 'Precio Unitario',
        }

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['invoice', 'payment_date', 'amount', 'method', 'notes']
        widgets = {
            'invoice': forms.Select(attrs={'class': 'form-control'}),
            'payment_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'method': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
