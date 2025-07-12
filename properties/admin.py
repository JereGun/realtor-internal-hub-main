
from django.contrib import admin
from .models import Property, PropertyType, PropertyStatus, Feature, Tag, PropertyImage


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 1


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('title', 'property_type', 'property_status', 'agent', 'sale_price', 'rental_price', 'created_at')
    list_filter = ('property_type', 'property_status', 'agent', 'province', 'locality')
    search_fields = ('title', 'description', 'street', 'neighborhood', 'locality')
    filter_horizontal = ('features', 'tags')
    inlines = [PropertyImageInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('title', 'description', 'property_type', 'property_status', 'agent', 'owner')
        }),
        ('Dirección', {
            'fields': ('street', 'number', 'neighborhood', 'locality', 'province', 'country')
        }),
        ('Detalles de la Propiedad', {
            'fields': ('total_surface', 'covered_surface', 'bedrooms', 'bathrooms', 'garage', 'furnished', 'year_built', 'orientation', 'floors')
        }),
        ('Información Financiera', {
            'fields': ('sale_price', 'rental_price', 'expenses')
        }),
        ('Características y Etiquetas', {
            'fields': ('features', 'tags')
        }),
    )


@admin.register(PropertyType)
class PropertyTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(PropertyStatus)
class PropertyStatusAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color')
    search_fields = ('name',)


@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
    list_display = ('property', 'is_cover', 'description')
    list_filter = ('is_cover', 'property__property_type')
    search_fields = ('property__title', 'description')
