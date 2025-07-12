
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q
from django.http import JsonResponse
from .models import Property, PropertyImage, Feature, Tag, PropertyType, PropertyStatus
from .forms import PropertyForm, PropertyImageForm, PropertySearchForm, PropertyImageFormSet
import json


class PropertyListView(LoginRequiredMixin, ListView):
    model = Property
    template_name = 'properties/property_list.html'
    context_object_name = 'properties'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Property.objects.all().select_related('property_type', 'property_status', 'agent')
        
        form = PropertySearchForm(self.request.GET)
        if form.is_valid():
            search = form.cleaned_data.get('search')
            property_type = form.cleaned_data.get('property_type')
            property_status = form.cleaned_data.get('property_status')
            locality = form.cleaned_data.get('locality')
            
            if search:
                queryset = queryset.filter(
                    Q(title__icontains=search) |
                    Q(description__icontains=search) |
                    Q(street__icontains=search) |
                    Q(neighborhood__icontains=search)
                )
            
            if property_type:
                queryset = queryset.filter(property_type=property_type)
            
            if property_status:
                queryset = queryset.filter(property_status=property_status)
            
            if locality:
                queryset = queryset.filter(locality__icontains=locality)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = PropertySearchForm(self.request.GET)
        return context


class PropertyDetailView(LoginRequiredMixin, DetailView):
    model = Property
    template_name = 'properties/property_detail.html'
    context_object_name = 'property'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['images'] = self.object.images.all()
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
            return self.render_to_response(self.get_context_data(form=form))
    
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
            images_saved = image_formset.save()
            
            messages.success(self.request, 'Propiedad actualizada correctamente.')
            return redirect(self.get_success_url())
        else:
            return self.render_to_response(self.get_context_data(form=form))
    
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
def add_property_image(request, pk):
    property_obj = get_object_or_404(Property, pk=pk)
    
    if request.method == 'POST':
        form = PropertyImageForm(request.POST, request.FILES)
        if form.is_valid():
            image = form.save(commit=False)
            image.property = property_obj
            image.save()
            messages.success(request, 'Imagen agregada correctamente.')
            return redirect('properties:property_detail', pk=pk)
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
