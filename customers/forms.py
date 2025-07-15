
from django import forms
from django.utils import formats
from .models import Customer
from locations.models import State, City # Import State and City


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
            'birth_date': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'},
                format='%Y-%m-%d'
            ),
            'profession': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            # Los campos ForeignKey (country, province, locality) usarán los widgets por defecto (Select)
            # o se pueden personalizar aquí si es necesario, aunque la carga dinámica se hará con JS.
            'country': forms.Select(attrs={'class': 'form-select country-select'}), # Use Select for initial data
            'province': forms.Select(attrs={'class': 'form-select province-select'}),
            'locality': forms.Select(attrs={'class': 'form-select locality-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # La lógica de queryset dinámico se manejará principalmente en el frontend con AJAX.
        # Aquí, simplemente nos aseguramos de que los campos existan y
        # de que los valores iniciales se carguen correctamente en el modo de edición.

        # Si el formulario se está enviando (hay datos en self.data),
        # ajustamos los querysets para incluir las opciones seleccionadas.
        if self.data:
            try:
                country_id = int(self.data.get('country'))
                self.fields['province'].queryset = State.objects.filter(country_id=country_id).order_by('name')
            except (ValueError, TypeError):
                self.fields['province'].queryset = State.objects.none()
            
            try:
                province_id = int(self.data.get('province'))
                self.fields['locality'].queryset = City.objects.filter(state_id=province_id).order_by('name')
            except (ValueError, TypeError):
                self.fields['locality'].queryset = City.objects.none()
        # Si es una instancia existente (edición), poblamos los querysets basados en la instancia.
        elif self.instance and self.instance.pk:
            if self.instance.country:
                self.fields['province'].queryset = self.instance.country.states.all().order_by('name')
            else:
                self.fields['province'].queryset = State.objects.none()

            if self.instance.province:
                self.fields['locality'].queryset = self.instance.province.cities.all().order_by('name')
            else:
                self.fields['locality'].queryset = City.objects.none()
        # Para un formulario nuevo (no enviado y sin instancia), los querysets dependientes están vacíos.
        else:
            self.fields['province'].queryset = State.objects.none()
            self.fields['locality'].queryset = City.objects.none()


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
