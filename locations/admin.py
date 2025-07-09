from django.contrib import admin
from .models import Country, State, City

@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ('name', 'country')
    search_fields = ('name', 'country__name')
    list_filter = ('country',)
    autocomplete_fields = ('country',) 

@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'state', 'get_country')
    search_fields = ('name', 'state__name', 'state__country__name')
    list_filter = ('state__country', 'state')
    autocomplete_fields = ('state',)

    def get_country(self, obj):
        return obj.state.country.name
    get_country.short_description = 'País'
    get_country.admin_order_field = 'state__country__name'
