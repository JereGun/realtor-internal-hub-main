
from django import forms
from .models import Customer


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        exclude = ['created_at', 'updated_at']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'document': forms.TextInput(attrs={'class': 'form-control'}),
            'street': forms.TextInput(attrs={'class': 'form-control'}),
            'number': forms.TextInput(attrs={'class': 'form-control'}),
            'neighborhood': forms.TextInput(attrs={'class': 'form-control'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'profession': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            # Los campos ForeignKey (country, province, locality) usarán los widgets por defecto (Select)
            # o se pueden personalizar aquí si es necesario, aunque la carga dinámica se hará con JS.
            'country': forms.Select(attrs={'class': 'form-select'}),
            'province': forms.Select(attrs={'class': 'form-select'}),
            'locality': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Inicialmente, provincia y localidad no tienen opciones o solo una opción vacía
        # Se poblarán dinámicamente con JavaScript
        if not self.instance or not self.instance.pk: # Solo para creación o si no hay instancia
            self.fields['province'].queryset = self.fields['province'].queryset.none()
            self.fields['locality'].queryset = self.fields['locality'].queryset.none()
        elif self.instance.pk:
            # Si hay una instancia (edición), ajustar los querysets para permitir la selección actual
            # y que JavaScript pueda cargar las opciones correctas basadas en la selección guardada.
            if self.instance.country:
                self.fields['province'].queryset = self.instance.country.states.all().order_by('name')
            else:
                self.fields['province'].queryset = self.fields['province'].queryset.none()

            if self.instance.province:
                self.fields['locality'].queryset = self.instance.province.cities.all().order_by('name')
            else:
                self.fields['locality'].queryset = self.fields['locality'].queryset.none()


class CustomerSearchForm(forms.Form):
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Buscar clientes...'})
    )
    locality = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Localidad'})
    )
