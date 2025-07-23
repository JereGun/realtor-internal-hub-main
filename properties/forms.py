from django import forms
from django.forms import inlineformset_factory
from .models import Property, PropertyImage, Feature, Tag, PropertyType, PropertyStatus
from customers.models import Customer
import json


class PropertyForm(forms.ModelForm):
    # Campos adicionales para gestión inline
    new_features = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Agregar nuevas características (separadas por coma)',
            'data-toggle': 'tooltip',
            'title': 'Ej: Piscina, Quincho, Parrilla'
        }),
        label="Nuevas Características",
        help_text="Separa múltiples características con comas"
    )
    
    new_tags = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Agregar nuevas etiquetas (separadas por coma)',
            'data-toggle': 'tooltip',
            'title': 'Ej: Oportunidad, Financiación, Urgente'
        }),
        label="Nuevas Etiquetas",
        help_text="Separa múltiples etiquetas con comas"
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Configurar el campo agente según el contexto
        # Importar aquí para evitar dependencias circulares
        if self.user:
            from agents.models import Agent
            
            # Filtrar solo agentes activos
            active_agents = Agent.objects.filter(is_active=True).order_by('first_name', 'last_name')
            self.fields['agent'].queryset = active_agents
            
            # Si es creación, pre-seleccionar el usuario actual
            if not self.instance.pk:
                self.fields['agent'].initial = self.user
                # Personalizar el label para mostrar mejor información
                if self.user in active_agents:
                    self.fields['agent'].empty_label = None  # No mostrar empty label si hay un inicial
        
        # Poblar el queryset de dueños y hacerlo opcional
        self.fields['owner'].queryset = Customer.objects.all().order_by('first_name', 'last_name')
        self.fields['owner'].required = False
        self.fields['owner'].empty_label = "Seleccionar Dueño (Opcional)"
    
    class Meta:
        model = Property
        exclude = ['created_at', 'updated_at']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'property_type': forms.Select(attrs={
                'class': 'form-control property-type-select',
                'data-create-url': '#',
                'data-field': 'property_type'
            }),
            'property_status': forms.Select(attrs={
                'class': 'form-control property-status-select',
                'data-create-url': '#',
                'data-field': 'property_status'
            }),
            'owner': forms.TextInput(attrs={ # Changed to TextInput
                'class': 'form-control owner-autocomplete', # Added class for JS targeting
                'placeholder': 'Buscar dueño...',
                'data-toggle': 'tooltip',
                'title': 'Dueño de la propiedad (opcional)'
            }),
            'street': forms.TextInput(attrs={'class': 'form-control'}),
            'number': forms.TextInput(attrs={'class': 'form-control'}),
            'neighborhood': forms.TextInput(attrs={'class': 'form-control'}),
            'locality': forms.TextInput(attrs={ # Changed to TextInput
                'class': 'form-control locality-autocomplete', # Added class for JS targeting
                'placeholder': 'Buscar localidad...'
            }),
            'province': forms.TextInput(attrs={ # Changed to TextInput
                'class': 'form-control province-autocomplete', # Added class for JS targeting
                'placeholder': 'Buscar provincia...'
            }),
            'country': forms.TextInput(attrs={ # Changed to TextInput
                'class': 'form-control country-autocomplete', # Added class for JS targeting
                'placeholder': 'Buscar país...'
            }),
            'total_surface': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'covered_surface': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'bedrooms': forms.NumberInput(attrs={'class': 'form-control'}),
            'bathrooms': forms.NumberInput(attrs={'class': 'form-control'}),
            'garage': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'furnished': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'listing_type': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_listing_type',
                'onchange': 'togglePriceFields()'
            }),
            'sale_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'id': 'id_sale_price'}),
            'rental_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'id': 'id_rental_price'}),
            'expenses': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'year_built': forms.NumberInput(attrs={'class': 'form-control'}),
            'orientation': forms.TextInput(attrs={'class': 'form-control'}),
            'floors': forms.NumberInput(attrs={'class': 'form-control'}),
            'agent': forms.Select(attrs={
                'class': 'form-control',
                'data-toggle': 'tooltip',
                'title': 'Agente responsable de esta propiedad'
            }),
            'features': forms.CheckboxSelectMultiple(attrs={'class': 'features-checkbox-list'}),
            'tags': forms.CheckboxSelectMultiple(attrs={'class': 'tags-checkbox-list'}),
        }
    
    def save(self, commit=True):
        instance = super().save(commit=commit)
        
        if commit:
            self._save_many_to_many_features_and_tags(instance)
        else:
            # Si no se guarda inmediatamente, guardamos el método para después
            self._save_m2m = lambda: self._save_many_to_many_features_and_tags(instance)
        
        return instance
    
    def _save_many_to_many_features_and_tags(self, instance):
        """Guardar features y tags nuevos después de que la instancia esté guardada"""
        # Procesar nuevas features
        new_features_text = self.cleaned_data.get('new_features', '')
        if new_features_text:
            feature_names = [name.strip() for name in new_features_text.split(',') if name.strip()]
            for feature_name in feature_names:
                feature, created = Feature.objects.get_or_create(
                    name__iexact=feature_name,
                    defaults={'name': feature_name.title()}
                )
                instance.features.add(feature)
        
        # Procesar nuevos tags
        new_tags_text = self.cleaned_data.get('new_tags', '')
        if new_tags_text:
            tag_names = [name.strip() for name in new_tags_text.split(',') if name.strip()]
            colors = ['#007bff', '#28a745', '#dc3545', '#ffc107', '#6f42c1', '#fd7e14', '#20c997']
            
            for i, tag_name in enumerate(tag_names):
                color = colors[i % len(colors)]  # Ciclar por colores
                tag, created = Tag.objects.get_or_create(
                    name__iexact=tag_name,
                    defaults={'name': tag_name.title(), 'color': color}
                )
                instance.tags.add(tag)


class PropertyImageForm(forms.ModelForm):
    class Meta:
        model = PropertyImage
        fields = ['image', 'is_cover', 'description']
        widgets = {
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
                'onchange': 'previewImage(this)'
            }),
            'is_cover': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descripción de la imagen (opcional)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['image'].required = False
        self.fields['description'].required = False


class PropertySearchForm(forms.Form):
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Buscar propiedades...'})
    )
    property_type = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="Todos los tipos",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    property_status = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="Todos los estados",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    locality = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Localidad'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import PropertyType, PropertyStatus
        self.fields['property_type'].queryset = PropertyType.objects.all()
        self.fields['property_status'].queryset = PropertyStatus.objects.all()


# Formset para manejar múltiples imágenes
PropertyImageFormSet = inlineformset_factory(
    Property,
    PropertyImage,
    form=PropertyImageForm,
    extra=3,  # Número de formularios vacíos a mostrar
    can_delete=True,
    min_num=0,
    validate_min=False,
    max_num=10,  # Máximo 10 imágenes por propiedad
    validate_max=True,
)