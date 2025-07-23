from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from properties.models import Property, PropertyType, PropertyStatus
from locations.models import City, State
from agents.models import Agent


def home(request):
    # Propiedades destacadas (últimas 6)
    featured_properties = (
        Property.objects.filter(property_status__name__in=["Disponible", "Available"])
        .select_related("property_type", "locality", "province")
        .prefetch_related("images")[:6]
    )

    # Estadísticas básicas
    total_properties = Property.objects.filter(
        property_status__name__in=["Disponible", "Available"]
    ).count()
    property_types = PropertyType.objects.all()

    context = {
        "featured_properties": featured_properties,
        "total_properties": total_properties,
        "property_types": property_types,
    }
    return render(request, "public/home.html", context)


def about(request):
    # Agentes para mostrar en la página
    agents = Agent.objects.filter(is_active=True)[:4]
    context = {
        "agents": agents,
    }
    return render(request, "public/about.html", context)


def properties(request):
    # Filtros
    property_type = request.GET.get("property_type")
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")
    location_search = request.GET.get("location_search")
    bedrooms = request.GET.get("bedrooms")
    bathrooms = request.GET.get("bathrooms")
    garage = request.GET.get("garage")
    furnished = request.GET.get("furnished")
    min_surface = request.GET.get("min_surface")
    max_surface = request.GET.get("max_surface")
    search = request.GET.get("search")
    sort_by = request.GET.get("sort")
    listing_type = request.GET.get("listing_type")  # Nuevo filtro para tipo de listado

    # Query base - solo propiedades disponibles
    properties = (
        Property.objects.filter(property_status__name__in=["Disponible", "Available"])
        .select_related("property_type", "locality", "province", "agent")
        .prefetch_related("images", "features")
    )

    # Aplicar filtros
    if property_type:
        properties = properties.filter(property_type_id=property_type)

    if min_price:
        properties = properties.filter(
            Q(sale_price__gte=min_price) | Q(rental_price__gte=min_price)
        )

    if max_price:
        properties = properties.filter(
            Q(sale_price__lte=max_price) | Q(rental_price__lte=max_price)
        )

    # Filtro de ubicación mejorado - busca en múltiples campos
    if location_search:
        properties = properties.filter(
            Q(locality__name__icontains=location_search)
            | Q(province__name__icontains=location_search)
            | Q(neighborhood__icontains=location_search)
            | Q(street__icontains=location_search)
        )

    # Filtros adicionales
    if bedrooms:
        if bedrooms == "4+":
            properties = properties.filter(bedrooms__gte=4)
        else:
            properties = properties.filter(bedrooms=int(bedrooms))

    if bathrooms:
        if bathrooms == "3+":
            properties = properties.filter(bathrooms__gte=3)
        else:
            properties = properties.filter(bathrooms=int(bathrooms))

    if garage == "true":
        properties = properties.filter(garage=True)
    elif garage == "false":
        properties = properties.filter(garage=False)

    if furnished == "true":
        properties = properties.filter(furnished=True)
    elif furnished == "false":
        properties = properties.filter(furnished=False)

    if min_surface:
        properties = properties.filter(total_surface__gte=min_surface)

    if max_surface:
        properties = properties.filter(total_surface__lte=max_surface)

    if search:
        properties = properties.filter(
            Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(neighborhood__icontains=search)
        )
        
    # Filtro por tipo de listado
    if listing_type:
        if listing_type == 'sale':
            properties = properties.filter(listing_type='sale')
        elif listing_type == 'rent':
            properties = properties.filter(listing_type='rent')
        elif listing_type == 'both':
            properties = properties.filter(listing_type='both')
    
    # Ya no necesitamos la información de depuración

    # Aplicar ordenamiento
    if sort_by == "price_asc":
        # Ordenar por precio ascendente (considerando tanto venta como alquiler)
        properties = properties.extra(
            select={"price": "COALESCE(sale_price, rental_price)"}
        ).order_by("price")
    elif sort_by == "price_desc":
        # Ordenar por precio descendente
        properties = properties.extra(
            select={"price": "COALESCE(sale_price, rental_price)"}
        ).order_by("-price")
    elif sort_by == "newest":
        properties = properties.order_by("-created_at")
    elif sort_by == "surface_desc":
        properties = properties.order_by("-total_surface")
    else:
        # Orden por defecto: más recientes
        properties = properties.order_by("-created_at")

    # Paginación
    paginator = Paginator(properties, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Datos para filtros
    property_types = PropertyType.objects.all()

    # Obtener rangos de precios para sugerencias
    price_ranges = [
        {"value": 50000, "label": "$50,000"},
        {"value": 100000, "label": "$100,000"},
        {"value": 200000, "label": "$200,000"},
        {"value": 500000, "label": "$500,000"},
        {"value": 1000000, "label": "$1,000,000"},
    ]

    context = {
        "properties": page_obj,
        "property_types": property_types,
        "price_ranges": price_ranges,
        "is_paginated": page_obj.has_other_pages(),
        "page_obj": page_obj,
        # Mantener valores de filtros para el formulario
        "current_filters": {
            "property_type": property_type,
            "min_price": min_price,
            "max_price": max_price,
            "location_search": location_search,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "garage": garage,
            "furnished": furnished,
            "min_surface": min_surface,
            "max_surface": max_surface,
            "search": search,
            "listing_type": listing_type,
        },
    }
    return render(request, "public/properties.html", context)


def property_detail(request, property_id):
    property = get_object_or_404(
        Property.objects.select_related(
            "property_type", "locality", "province", "agent"
        ).prefetch_related("images", "features", "tags"),
        id=property_id,
        property_status__name__in=["Disponible", "Available"],
    )

    # Propiedades similares
    similar_properties = (
        Property.objects.filter(
            property_type=property.property_type,
            property_status__name__in=["Disponible", "Available"],
        )
        .exclude(id=property.id)
        .select_related("property_type", "locality")
        .prefetch_related("images")[:4]
    )

    context = {
        "property": property,
        "similar_properties": similar_properties,
    }
    return render(request, "public/property_detail.html", context)


def agents(request):
    agents = Agent.objects.filter(is_active=True).prefetch_related("property_set")

    context = {
        "agents": agents,
    }
    return render(request, "public/agents.html", context)


def location_autocomplete(request):
    """API endpoint para autocompletado de ubicaciones"""
    query = request.GET.get("q", "").strip()

    if len(query) < 2:
        return JsonResponse({"results": []})

    # Buscar en ciudades, provincias y barrios de propiedades
    locations = []

    # Ciudades
    cities = City.objects.filter(name__icontains=query)[:5]
    for city in cities:
        locations.append(
            {
                "id": f"city_{city.id}",
                "text": f"{city.name}, {city.state.name if city.state else ''}",
                "type": "city",
            }
        )

    # Provincias/Estados
    states = State.objects.filter(name__icontains=query)[:3]
    for state in states:
        locations.append(
            {"id": f"state_{state.id}", "text": f"{state.name}", "type": "state"}
        )

    # Barrios únicos de propiedades
    neighborhoods = (
        Property.objects.filter(
            neighborhood__icontains=query,
            property_status__name__in=["Disponible", "Available"],
        )
        .values_list("neighborhood", flat=True)
        .distinct()[:5]
    )

    for neighborhood in neighborhoods:
        if neighborhood:
            locations.append(
                {
                    "id": f"neighborhood_{neighborhood}",
                    "text": neighborhood,
                    "type": "neighborhood",
                }
            )

    return JsonResponse({"results": locations})


def sitemap_xml(request):
    """Generate XML sitemap for SEO"""
    from django.http import HttpResponse
    from django.urls import reverse
    from datetime import datetime

    # URLs estáticas
    static_urls = [
        {
            "loc": request.build_absolute_uri(reverse("public:home")),
            "lastmod": datetime.now().strftime("%Y-%m-%d"),
            "changefreq": "daily",
            "priority": "1.0",
        },
        {
            "loc": request.build_absolute_uri(reverse("public:properties")),
            "lastmod": datetime.now().strftime("%Y-%m-%d"),
            "changefreq": "daily",
            "priority": "0.9",
        },
        {
            "loc": request.build_absolute_uri(reverse("public:agents")),
            "lastmod": datetime.now().strftime("%Y-%m-%d"),
            "changefreq": "weekly",
            "priority": "0.8",
        },
        {
            "loc": request.build_absolute_uri(reverse("public:about")),
            "lastmod": datetime.now().strftime("%Y-%m-%d"),
            "changefreq": "monthly",
            "priority": "0.7",
        },
    ]

    # URLs dinámicas de propiedades
    properties = Property.objects.filter(
        property_status__name__in=["Disponible", "Available"]
    ).select_related("property_type", "locality", "province")

    property_urls = []
    for property in properties:
        property_urls.append(
            {
                "loc": request.build_absolute_uri(
                    reverse("public:property_detail", args=[property.id])
                ),
                "lastmod": property.updated_at.strftime("%Y-%m-%d"),
                "changefreq": "weekly",
                "priority": "0.8",
            }
        )

    # Generar XML
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">"""

    # Agregar URLs estáticas
    for url in static_urls:
        xml_content += f"""
    <url>
        <loc>{url['loc']}</loc>
        <lastmod>{url['lastmod']}</lastmod>
        <changefreq>{url['changefreq']}</changefreq>
        <priority>{url['priority']}</priority>
    </url>"""

    # Agregar URLs de propiedades
    for url in property_urls:
        xml_content += f"""
    <url>
        <loc>{url['loc']}</loc>
        <lastmod>{url['lastmod']}</lastmod>
        <changefreq>{url['changefreq']}</changefreq>
        <priority>{url['priority']}</priority>
    </url>"""

    xml_content += """
</urlset>"""

    return HttpResponse(xml_content, content_type="application/xml")


def robots_txt(request):
    """Generate robots.txt for SEO"""
    from django.http import HttpResponse

    content = f"""User-agent: *
Allow: /

# Sitemap
Sitemap: {request.build_absolute_uri('/sitemap.xml')}

# Disallow admin and private areas
Disallow: /admin/
Disallow: /app/
"""

    return HttpResponse(content, content_type="text/plain")
