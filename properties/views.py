
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q
from django.http import JsonResponse
from .models import Property, PropertyImage, Feature, Tag, PropertyType, PropertyStatus
from locations.models import Country, State, City # Added for autocompletion
from customers.models import Customer # Added for owner autocompletion
from agents.models import Agent # Added for agent reference
from .forms import PropertyForm, PropertyImageForm, PropertySearchForm, PropertyImageFormSet
import json

# Vista pública para mostrar propiedades
class PublicPropertyListView(ListView):
    model = Property
    template_name = 'public/properties.html'
    context_object_name = 'properties'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Property.objects.filter(property_status__name='Disponible')
        
        # Obtener parámetros de búsqueda
        property_type = self.request.GET.get('property_type')
        min_price = self.request.GET.get('min_price')
        max_price = self.request.GET.get('max_price')
        location = self.request.GET.get('location')
        
        # Aplicar filtros
        if property_type:
            queryset = queryset.filter(property_type_id=property_type)
        
        if min_price:
            queryset = queryset.filter(sale_price__gte=min_price)
        
        if max_price:
            queryset = queryset.filter(sale_price__lte=max_price)
        
        if location:
            queryset = queryset.filter(locality_id=location)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['property_types'] = PropertyType.objects.all()
        context['locations'] = City.objects.all()
        return context


class PropertyListView(LoginRequiredMixin, ListView):
    model = Property
    template_name = 'properties/property_list.html'
    context_object_name = 'properties'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Property.objects.select_related('property_type', 'property_status', 'agent').prefetch_related('images')
        
        # Filtros de búsqueda
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | 
                Q(description__icontains=search) |
                Q(street__icontains=search) |
                Q(neighborhood__icontains=search)
            )
        
        property_type = self.request.GET.get('property_type')
        if property_type:
            queryset = queryset.filter(property_type_id=property_type)
        
        property_status = self.request.GET.get('property_status')
        if property_status:
            queryset = queryset.filter(property_status_id=property_status)
        
        agent = self.request.GET.get('agent')
        if agent:
            queryset = queryset.filter(agent_id=agent)
        
        # Filtros de precio
        min_sale_price = self.request.GET.get('min_sale_price')
        if min_sale_price:
            queryset = queryset.filter(sale_price__gte=min_sale_price)
        
        max_sale_price = self.request.GET.get('max_sale_price')
        if max_sale_price:
            queryset = queryset.filter(sale_price__lte=max_sale_price)
        
        min_rental_price = self.request.GET.get('min_rental_price')
        if min_rental_price:
            queryset = queryset.filter(rental_price__gte=min_rental_price)
        
        max_rental_price = self.request.GET.get('max_rental_price')
        if max_rental_price:
            queryset = queryset.filter(rental_price__lte=max_rental_price)
        
        # Filtros de características
        bedrooms = self.request.GET.get('bedrooms')
        if bedrooms:
            if bedrooms == '4':
                queryset = queryset.filter(bedrooms__gte=4)
            else:
                queryset = queryset.filter(bedrooms=bedrooms)
        
        bathrooms = self.request.GET.get('bathrooms')
        if bathrooms:
            if bathrooms == '3':
                queryset = queryset.filter(bathrooms__gte=3)
            else:
                queryset = queryset.filter(bathrooms=bathrooms)
        
        # Filtros adicionales
        garage = self.request.GET.get('garage')
        if garage:
            if garage == 'true':
                queryset = queryset.filter(garage=True)
            elif garage == 'false':
                queryset = queryset.filter(garage=False)
        
        furnished = self.request.GET.get('furnished')
        if furnished:
            if furnished == 'true':
                queryset = queryset.filter(furnished=True)
            elif furnished == 'false':
                queryset = queryset.filter(furnished=False)
        
        year_built = self.request.GET.get('year_built')
        if year_built:
            if year_built == '2020-':
                queryset = queryset.filter(year_built__gte=2020)
            elif year_built == '2010-2019':
                queryset = queryset.filter(year_built__gte=2010, year_built__lte=2019)
            elif year_built == '2000-2009':
                queryset = queryset.filter(year_built__gte=2000, year_built__lte=2009)
            elif year_built == '-1999':
                queryset = queryset.filter(year_built__lt=2000)
        
        # Ordenamiento
        sort = self.request.GET.get('sort', '-created_at')
        queryset = queryset.order_by(sort)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['property_types'] = PropertyType.objects.all()
        context['property_statuses'] = PropertyStatus.objects.all()
        context['agents'] = Agent.objects.filter(is_active=True)
        
        # Calcular estadísticas para las tarjetas
        all_properties = Property.objects.all()
        context['total_properties_count'] = all_properties.count()
        
        # Buscar estados específicos por nombre (ajustar según los nombres reales en tu BD)
        try:
            available_status = PropertyStatus.objects.get(name__icontains='disponible')
            context['available_properties_count'] = all_properties.filter(property_status=available_status).count()
        except PropertyStatus.DoesNotExist:
            context['available_properties_count'] = 0
        
        try:
            rented_status = PropertyStatus.objects.get(name__icontains='alquilada')
            context['rented_properties_count'] = all_properties.filter(property_status=rented_status).count()
        except PropertyStatus.DoesNotExist:
            context['rented_properties_count'] = 0
        
        # Propiedades con etiquetas (como alternativa a "destacadas")
        context['featured_properties_count'] = all_properties.filter(tags__isnull=False).distinct().count()
        
        return context


class PropertyDetailView(LoginRequiredMixin, DetailView):
    model = Property
    template_name = 'properties/property_detail.html'
    context_object_name = 'property'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['images'] = self.object.images.all()
        # Agregar contratos relacionados con esta propiedad
        from contracts.models import Contract
        context['contracts'] = Contract.objects.filter(property=self.object).select_related('customer', 'agent')[:5]
        return context


class PropertyCreateView(LoginRequiredMixin, CreateView):
    model = Property
    form_class = PropertyForm
    template_name = 'properties/property_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['image_formset'] = PropertyImageFormSet(self.request.POST, self.request.FILES)
        else:
            context['image_formset'] = PropertyImageFormSet()
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        image_formset = context['image_formset']
        
        if form.is_valid() and image_formset.is_valid():
            # El método save del formulario está sobreescrito para manejar
            # la creación de nuevas features y tags.
            self.object = form.save()
            
            # El formset necesita la instancia de la propiedad antes de poder guardarse.
            image_formset.instance = self.object
            image_formset.save()
            
            messages.success(self.request, 'Propiedad creada correctamente.')
            
            return redirect(self.get_success_url())
        else:
            # Si hay errores, renderizar con el contexto adecuado
            return self.form_invalid(form)
    
    def get_success_url(self):
        return reverse_lazy('properties:property_detail', kwargs={'pk': self.object.pk})


class PropertyUpdateView(LoginRequiredMixin, UpdateView):
    model = Property
    form_class = PropertyForm
    template_name = 'properties/property_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['image_formset'] = PropertyImageFormSet(self.request.POST, self.request.FILES, instance=self.object)
        else:
            context['image_formset'] = PropertyImageFormSet(instance=self.object)
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        image_formset = context['image_formset']
        
        if form.is_valid() and image_formset.is_valid():
            # Guardar la propiedad
            self.object = form.save()
            
            # Si el formulario tiene el método _save_m2m, llamarlo para guardar ManyToMany
            if hasattr(form, '_save_m2m'):
                form._save_m2m()
            
            # Guardar las imágenes
            image_formset.instance = self.object
            image_formset.save()
            
            messages.success(self.request, 'Propiedad actualizada correctamente.')
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)
    
    def get_success_url(self):
        return reverse_lazy('properties:property_detail', kwargs={'pk': self.object.pk})


class PropertyDeleteView(LoginRequiredMixin, DeleteView):
    model = Property
    template_name = 'properties/property_confirm_delete.html'
    success_url = reverse_lazy('properties:property_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Propiedad eliminada correctamente.')
        return super().delete(request, *args, **kwargs)


@login_required
def add_property_image(request, pk=None):
    """Vista para agregar imagen a una propiedad"""
    property_obj = None
    if pk:
        property_obj = get_object_or_404(Property, pk=pk)
    
    if request.method == 'POST':
        form = PropertyImageForm(request.POST, request.FILES)
        
        # Si no hay propiedad preseleccionada, obtenerla del POST
        if not property_obj:
            property_id = request.POST.get('property')
            if property_id:
                try:
                    property_obj = Property.objects.get(pk=property_id)
                except Property.DoesNotExist:
                    messages.error(request, 'Propiedad no encontrada.')
                    return render(request, 'properties/add_image.html', {
                        'form': form,
                        'property': None
                    })
            else:
                messages.error(request, 'Debe seleccionar una propiedad.')
                return render(request, 'properties/add_image.html', {
                    'form': form,
                    'property': None
                })
        
        if form.is_valid():
            image = form.save(commit=False)
            image.property = property_obj
            image.save()
            messages.success(request, f'Imagen agregada correctamente a {property_obj.title}.')
            return redirect('properties:property_detail', pk=property_obj.pk)
    else:
        form = PropertyImageForm()
    
    return render(request, 'properties/add_image.html', {
        'form': form,
        'property': property_obj
    })


@login_required
def delete_property_image(request, pk, image_pk):
    property_obj = get_object_or_404(Property, pk=pk)
    image = get_object_or_404(PropertyImage, pk=image_pk, property=property_obj)
    
    image.delete()
    messages.success(request, 'Imagen eliminada correctamente.')
    return redirect('properties:property_detail', pk=pk)


# Vistas AJAX para gestión de Features y Tags
@login_required
def autocomplete_features(request):
    """Autocompletado de características"""
    term = request.GET.get('term', '')
    features = Feature.objects.filter(name__icontains=term)[:10]
    
    results = [{
        'id': feature.id,
        'text': feature.name,
        'name': feature.name
    } for feature in features]
    
    return JsonResponse({'results': results})


@login_required
def autocomplete_tags(request):
    """Autocompletado de etiquetas"""
    term = request.GET.get('term', '')
    tags = Tag.objects.filter(name__icontains=term)[:10]
    
    results = [{
        'id': tag.id,
        'text': tag.name,
        'name': tag.name,
        'color': tag.color
    } for tag in tags]
    
    return JsonResponse({'results': results})


@login_required
def create_feature_ajax(request):
    """Crear feature via AJAX"""
    if request.method == 'POST':
        data = json.loads(request.body)
        feature_name = data.get('name', '').strip()
        
        if feature_name:
            feature, created = Feature.objects.get_or_create(
                name__iexact=feature_name,
                defaults={'name': feature_name.title()}
            )
            
            return JsonResponse({
                'success': True,
                'item': {
                    'id': feature.id,
                    'name': feature.name,
                },
                'created': created
            })
        
    return JsonResponse({'success': False, 'error': 'Nombre requerido'})


@login_required
def create_tag_ajax(request):
    """Crear tag via AJAX"""
    if request.method == 'POST':
        data = json.loads(request.body)
        tag_name = data.get('name', '').strip()
        tag_color = data.get('color', '#007bff')
        
        if tag_name:
            tag, created = Tag.objects.get_or_create(
                name__iexact=tag_name,
                defaults={'name': tag_name.title(), 'color': tag_color}
            )
            
            return JsonResponse({
                'success': True,
                'item': {
                    'id': tag.id,
                    'name': tag.name,
                    'color': tag.color
                },
                'created': created
            })
        
    return JsonResponse({'success': False, 'error': 'Nombre requerido'})


@login_required
def create_property_type_ajax(request):
    """Crear tipo de propiedad via AJAX"""
    if request.method == 'POST':
        data = json.loads(request.body)
        type_name = data.get('name', '').strip()
        type_description = data.get('description', '').strip()
        
        if type_name:
            property_type, created = PropertyType.objects.get_or_create(
                name__iexact=type_name,
                defaults={
                    'name': type_name.title(),
                    'description': type_description
                }
            )
            
            return JsonResponse({
                'success': True,
                'item': {
                    'id': property_type.id,
                    'name': property_type.name,
                    'description': property_type.description
                },
                'created': created
            })
        
    return JsonResponse({'success': False, 'error': 'Nombre requerido'})


@login_required
def create_property_status_ajax(request):
    """Crear estado de propiedad via AJAX"""
    if request.method == 'POST':
        data = json.loads(request.body)
        status_name = data.get('name', '').strip()
        status_description = data.get('description', '').strip()
        
        if status_name:
            property_status, created = PropertyStatus.objects.get_or_create(
                name__iexact=status_name,
                defaults={
                    'name': status_name.title(),
                    'description': status_description
                }
            )
            
            return JsonResponse({
                'success': True,
                'item': {
                    'id': property_status.id,
                    'name': property_status.name,
                    'description': property_status.description
                },
                'created': created
            })
        
    return JsonResponse({'success': False, 'error': 'Nombre requerido'})


@login_required
def get_property_types_ajax(request):
    """Obtener lista de tipos de propiedades"""
    property_types = PropertyType.objects.all().order_by('name')
    
    types_data = [{
        'id': pt.id,
        'name': pt.name,
        'description': pt.description
    } for pt in property_types]
    
    return JsonResponse({'property_types': types_data})


@login_required
def get_property_statuses_ajax(request):
    """Obtener lista de estados de propiedades"""
    property_statuses = PropertyStatus.objects.all().order_by('name')
    
    statuses_data = [{
        'id': ps.id,
        'name': ps.name,
        'description': ps.description
    } for ps in property_statuses]
    
    return JsonResponse({'property_statuses': statuses_data})


@login_required
def autocomplete_owners(request):
    term = request.GET.get('term', '')
    owners = Customer.objects.filter(
        Q(first_name__icontains=term) | Q(last_name__icontains=term) | Q(email__icontains=term)
    )[:10]
    results = [{'id': owner.id, 'text': f"{owner.first_name} {owner.last_name} ({owner.email})"} for owner in owners]
    return JsonResponse({'results': results})

@login_required
def autocomplete_countries(request):
    term = request.GET.get('term', '')
    countries = Country.objects.filter(name__icontains=term)[:10]
    results = [{'id': country.id, 'text': country.name} for country in countries]
    return JsonResponse({'results': results})

@login_required
def autocomplete_provinces(request):
    term = request.GET.get('term', '')
    country_id = request.GET.get('country_id')
    provinces = State.objects.filter(name__icontains=term)
    if country_id:
        provinces = provinces.filter(country_id=country_id)
    results = [{'id': province.id, 'text': province.name} for province in provinces[:10]]
    return JsonResponse({'results': results})

@login_required
def autocomplete_localities(request):
    term = request.GET.get('term', '')
    province_id = request.GET.get('province_id')
    localities = City.objects.filter(name__icontains=term)
    if province_id:
        localities = localities.filter(state_id=province_id)
    results = [{'id': locality.id, 'text': locality.name} for locality in localities[:10]]
    return JsonResponse({'results': results})

@login_required
def autocomplete_properties(request):
    """Autocompletado de propiedades"""
    term = request.GET.get('term', '')
    property_id = request.GET.get('id')  # Para cargar una propiedad específica por ID
    
    if property_id:
        # Cargar propiedad específica por ID
        try:
            property_obj = Property.objects.get(id=property_id)
            results = [{
                'id': property_obj.id,
                'title': property_obj.title,
                'address': property_obj.full_address,
                'property_type': property_obj.property_type.name if property_obj.property_type else None,
                'status': property_obj.property_status.name if property_obj.property_status else None,
                'surface': str(property_obj.total_surface) if property_obj.total_surface else None
            }]
            return JsonResponse({'results': results})
        except Property.DoesNotExist:
            return JsonResponse({'results': []})
    
    # Búsqueda por término
    if len(term) < 2:
        return JsonResponse({'results': []})
    
    properties = Property.objects.filter(
        Q(title__icontains=term) |
        Q(street__icontains=term) |
        Q(neighborhood__icontains=term) |
        Q(locality__name__icontains=term) |
        Q(property_code__icontains=term)
    ).select_related('property_type', 'property_status', 'locality')[:10]
    
    results = []
    for prop in properties:
        results.append({
            'id': prop.id,
            'title': prop.title,
            'address': prop.full_address,
            'property_type': prop.property_type.name if prop.property_type else 'N/A',
            'status': prop.property_status.name if prop.property_status else 'N/A',
            'surface': str(prop.total_surface) if prop.total_surface else 'N/A'
        })
    
    return JsonResponse({'results': results})


@login_required
def create_property_ajax(request):
    """Crear propiedad via AJAX"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Validaciones básicas
            title = data.get('title', '').strip()
            property_type_name = data.get('property_type', '').strip()
            property_status_name = data.get('property_status', '').strip()
            
            if not title or not property_type_name or not property_status_name:
                return JsonResponse({
                    'success': False, 
                    'error': 'Título, tipo y estado son obligatorios'
                })
            
            # Obtener o crear tipo de propiedad
            property_type, created = PropertyType.objects.get_or_create(
                name=property_type_name,
                defaults={'description': f'Tipo {property_type_name}'}
            )
            
            # Obtener o crear estado de propiedad
            property_status, created = PropertyStatus.objects.get_or_create(
                name=property_status_name,
                defaults={'description': f'Estado {property_status_name}'}
            )
            
            # Crear la propiedad
            property_obj = Property.objects.create(
                title=title,
                description=data.get('description', ''),
                property_type=property_type,
                property_status=property_status,
                street=data.get('street', ''),
                number=data.get('number', ''),
                total_surface=data.get('total_surface') or None,
                listing_type=data.get('listing_type', ''),
                agent=request.user.agent if hasattr(request.user, 'agent') else None
            )
            
            return JsonResponse({
                'success': True,
                'property': {
                    'id': property_obj.id,
                    'title': property_obj.title,
                    'address': property_obj.full_address,
                    'property_type': property_obj.property_type.name,
                    'status': property_obj.property_status.name,
                    'surface': str(property_obj.total_surface) if property_obj.total_surface else 'N/A'
                }
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Datos JSON inválidos'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})


@login_required
def image_upload_demo(request):
    """Vista de demostración del formulario mejorado de subida de imágenes"""
    return render(request, 'properties/image_upload_demo.html')