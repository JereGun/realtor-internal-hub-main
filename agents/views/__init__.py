from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.db.models import Count, Sum, Avg, F, ExpressionWrapper, DecimalField, Q
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta, datetime
from ..models import Agent
from ..forms import AgentLoginForm, AgentForm
from properties.models import Property
from contracts.models import Contract
from customers.models import Customer
from payments.models import ContractPayment


def agent_login(request):
    if request.method == "POST":
        form = AgentLoginForm(data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(request, email=email, password=password)
            if user is not None:
                login(request, user)
                return redirect("agents:dashboard")
            else:
                messages.error(request, "Email o contraseña incorrectos.")
    else:
        form = AgentLoginForm()

    return render(request, "agents/login.html", {"form": form})


def agent_logout(request):
    logout(request)
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect("agents:login")


def agent_register(request):
    """Vista para registro de nuevos agentes."""
    if request.method == "POST":
        form = AgentForm(request.POST, request.FILES)
        if form.is_valid():
            # Crear el usuario pero no guardarlo aún
            agent = form.save(commit=False)
            # Establecer la contraseña
            password = request.POST.get("password")
            agent.set_password(password)
            agent.save()

            # Autenticar y hacer login
            user = authenticate(request, email=agent.email, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, "¡Registro exitoso! Bienvenido al sistema.")
                return redirect("agents:dashboard")
    else:
        form = AgentForm()

    return render(request, "agents/register.html", {"form": form})


@login_required
def dashboard(request):
    """Vista del panel de control para agentes."""
    # Obtener parámetros de filtro
    time_filter = request.GET.get("time_filter", "30")  # Por defecto, 30 días

    try:
        days = int(time_filter)
    except ValueError:
        days = 30  # Valor por defecto si hay un error

    today = timezone.now().date()
    filter_date = today - timedelta(days=days)

    # Estadísticas generales
    properties_count = Property.objects.filter(agent=request.user).count()
    active_properties = Property.objects.filter(
        agent=request.user, property_status__name__in=["Disponible", "Available"]
    ).count()
    customers_count = Customer.objects.filter(agent=request.user).count()
    contracts_count = Contract.objects.filter(agent=request.user).count()

    # Porcentaje de propiedades activas
    active_percentage = (
        (active_properties / properties_count * 100) if properties_count > 0 else 0
    )

    # Estadísticas de propiedades
    property_types = (
        Property.objects.filter(agent=request.user)
        .values("property_type__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    property_status = (
        Property.objects.filter(agent=request.user)
        .values("property_status__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    # Estadísticas de contratos
    active_contracts = Contract.objects.filter(
        agent=request.user, status=Contract.STATUS_ACTIVE
    ).count()

    expiring_contracts = Contract.objects.filter(
        agent=request.user,
        status=Contract.STATUS_ACTIVE,
        end_date__range=[today, today + timedelta(days=30)],
    ).count()

    # Tasa de renovación de contratos (últimos X días)
    expired_contracts = Contract.objects.filter(
        agent=request.user,
        end_date__range=[filter_date, today],
        status=Contract.STATUS_EXPIRED,
    ).count()

    renewed_contracts = Contract.objects.filter(
        agent=request.user, created_at__gte=filter_date, previous_contract__isnull=False
    ).count()

    renewal_rate = (
        (renewed_contracts / expired_contracts * 100) if expired_contracts > 0 else 0
    )

    # Estadísticas de ingresos (período filtrado)
    period_payments = ContractPayment.objects.filter(
        contract__agent=request.user, payment_date__gte=filter_date
    ).aggregate(total=Sum("amount"), avg_per_day=Avg("amount"))

    period_income = period_payments["total"] if period_payments["total"] else 0
    avg_daily_income = (
        period_payments["avg_per_day"] if period_payments["avg_per_day"] else 0
    )

    # Calcular comisiones estimadas
    commission_rate = (
        request.user.commission_rate / 100
    )  # Convertir porcentaje a decimal
    estimated_commission = period_income * commission_rate

    # Tendencia de ingresos (comparación con período anterior)
    previous_period_start = filter_date - timedelta(days=days)
    previous_period_payments = ContractPayment.objects.filter(
        contract__agent=request.user,
        payment_date__range=[previous_period_start, filter_date],
    ).aggregate(total=Sum("amount"))

    previous_income = (
        previous_period_payments["total"] if previous_period_payments["total"] else 0
    )
    income_trend = (
        ((period_income - previous_income) / previous_income * 100)
        if previous_income > 0
        else 0
    )

    # Propiedades recientes
    recent_properties = (
        Property.objects.filter(agent=request.user)
        .select_related("property_type", "property_status")
        .order_by("-created_at")[:5]
    )

    # Contratos recientes
    recent_contracts = (
        Contract.objects.filter(agent=request.user)
        .select_related("property", "customer")
        .order_by("-created_at")[:5]
    )

    # Clientes recientes
    recent_customers = Customer.objects.filter(agent=request.user).order_by(
        "-created_at"
    )[:5]

    # Contratos próximos a vencer
    expiring_soon_contracts = (
        Contract.objects.filter(
            agent=request.user,
            status=Contract.STATUS_ACTIVE,
            end_date__range=[today, today + timedelta(days=30)],
        )
        .select_related("property", "customer")
        .order_by("end_date")[:5]
    )

    # Datos para gráficos
    # Ingresos por mes (últimos 6 meses)
    months_data = []
    for i in range(5, -1, -1):
        month_start = (today.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
        month_end = month_start.replace(
            month=month_start.month + 1 if month_start.month < 12 else 1,
            year=month_start.year if month_start.month < 12 else month_start.year + 1,
        ) - timedelta(days=1)

        month_payments = ContractPayment.objects.filter(
            contract__agent=request.user, payment_date__range=[month_start, month_end]
        ).aggregate(total=Sum("amount"))

        month_total = month_payments["total"] if month_payments["total"] else 0

        months_data.append(
            {"month": month_start.strftime("%b %Y"), "income": float(month_total)}
        )

    # Propiedades por tipo (para gráfico de pastel)
    property_types_chart = list(property_types)

    # Actividad de contratos (nuevos vs expirados por mes)
    contract_activity = []
    for i in range(5, -1, -1):
        month_start = (today.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
        month_end = month_start.replace(
            month=month_start.month + 1 if month_start.month < 12 else 1,
            year=month_start.year if month_start.month < 12 else month_start.year + 1,
        ) - timedelta(days=1)

        new_contracts = Contract.objects.filter(
            agent=request.user, created_at__range=[month_start, month_end]
        ).count()

        expired_contracts = Contract.objects.filter(
            agent=request.user,
            end_date__range=[month_start, month_end],
            status=Contract.STATUS_EXPIRED,
        ).count()

        contract_activity.append(
            {
                "month": month_start.strftime("%b %Y"),
                "new": new_contracts,
                "expired": expired_contracts,
            }
        )

    context = {
        # Filtros
        "time_filter": time_filter,
        "filter_date": filter_date,
        # Estadísticas generales
        "properties_count": properties_count,
        "active_properties": active_properties,
        "active_percentage": active_percentage,
        "customers_count": customers_count,
        "contracts_count": contracts_count,
        # Estadísticas detalladas
        "property_types": property_types,
        "property_status": property_status,
        "active_contracts": active_contracts,
        "expiring_contracts": expiring_contracts,
        "renewal_rate": renewal_rate,
        "period_income": period_income,
        "avg_daily_income": avg_daily_income,
        "estimated_commission": estimated_commission,
        "income_trend": income_trend,
        # Datos para gráficos
        "months_data": months_data,
        "property_types_chart": property_types_chart,
        "contract_activity": contract_activity,
        # Listados recientes
        "recent_properties": recent_properties,
        "recent_contracts": recent_contracts,
        "recent_customers": recent_customers,
        "expiring_soon_contracts": expiring_soon_contracts,
    }

    return render(request, "agents/dashboard.html", context)


class AgentListView(LoginRequiredMixin, ListView):
    model = Agent
    template_name = "agents/agent_list.html"
    context_object_name = "agents"
    paginate_by = 20

    def get_queryset(self):
        return Agent.objects.filter(is_active=True).order_by("first_name", "last_name")


class AgentDetailView(LoginRequiredMixin, DetailView):
    model = Agent
    template_name = "agents/agent_detail.html"
    context_object_name = "agent"


class AgentCreateView(LoginRequiredMixin, CreateView):
    model = Agent
    form_class = AgentForm
    template_name = "agents/agent_form.html"
    success_url = reverse_lazy("agents:agent_list")

    def form_valid(self, form):
        messages.success(self.request, "Agente creado correctamente.")
        return super().form_valid(form)


class AgentUpdateView(LoginRequiredMixin, UpdateView):
    model = Agent
    form_class = AgentForm
    template_name = "agents/agent_form.html"
    success_url = reverse_lazy("agents:agent_list")

    def form_valid(self, form):
        messages.success(self.request, "Agente actualizado correctamente.")
        return super().form_valid(form)


@login_required
def profile_view(request):
    """Vista de perfil legacy - redirige a la nueva vista de perfil."""
    return redirect('agents:profile_view')


@login_required
def dashboard_data(request):
    """API para obtener datos del dashboard vía AJAX."""
    time_filter = request.GET.get("time_filter", "30")

    try:
        days = int(time_filter)
    except ValueError:
        days = 30

    today = timezone.now().date()
    filter_date = today - timedelta(days=days)

    # Estadísticas de ingresos (período filtrado)
    period_payments = ContractPayment.objects.filter(
        contract__agent=request.user, payment_date__gte=filter_date
    ).aggregate(total=Sum("amount"))

    period_income = period_payments["total"] if period_payments["total"] else 0

    # Ingresos por mes (últimos 6 meses)
    months_data = []
    for i in range(5, -1, -1):
        month_start = (today.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
        month_end = month_start.replace(
            month=month_start.month + 1 if month_start.month < 12 else 1,
            year=month_start.year if month_start.month < 12 else month_start.year + 1,
        ) - timedelta(days=1)

        month_payments = ContractPayment.objects.filter(
            contract__agent=request.user, payment_date__range=[month_start, month_end]
        ).aggregate(total=Sum("amount"))

        month_total = month_payments["total"] if month_payments["total"] else 0

        months_data.append(
            {"month": month_start.strftime("%b %Y"), "income": float(month_total)}
        )

    # Actividad de contratos (nuevos vs expirados por mes)
    contract_activity = []
    for i in range(5, -1, -1):
        month_start = (today.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
        month_end = month_start.replace(
            month=month_start.month + 1 if month_start.month < 12 else 1,
            year=month_start.year if month_start.month < 12 else month_start.year + 1,
        ) - timedelta(days=1)

        new_contracts = Contract.objects.filter(
            agent=request.user, created_at__range=[month_start, month_end]
        ).count()

        expired_contracts = Contract.objects.filter(
            agent=request.user,
            end_date__range=[month_start, month_end],
            status=Contract.STATUS_EXPIRED,
        ).count()

        contract_activity.append(
            {
                "month": month_start.strftime("%b %Y"),
                "new": new_contracts,
                "expired": expired_contracts,
            }
        )

    # Estadísticas de propiedades
    property_types = list(
        Property.objects.filter(agent=request.user)
        .values("property_type__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    data = {
        "period_income": float(period_income),
        "months_data": months_data,
        "contract_activity": contract_activity,
        "property_types": property_types,
    }

    return JsonResponse(data)


@login_required
def quick_search(request):
    """Función de búsqueda rápida para el dashboard."""
    query = request.GET.get("q", "")
    results = []

    if query:
        # Buscar propiedades
        properties = Property.objects.filter(
            agent=request.user, title__icontains=query
        ).values("id", "title", "address")[:5]

        for prop in properties:
            results.append(
                {
                    "type": "property",
                    "id": prop["id"],
                    "title": prop["title"],
                    "subtitle": prop["address"],
                    "url": f'/properties/{prop["id"]}/',
                }
            )

        # Buscar clientes
        customers = (
            Customer.objects.filter(agent=request.user)
            .filter(
                Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(email__icontains=query)
            )
            .values("id", "first_name", "last_name", "email")[:5]
        )

        for customer in customers:
            results.append(
                {
                    "type": "customer",
                    "id": customer["id"],
                    "title": f"{customer['first_name']} {customer['last_name']}",
                    "subtitle": customer["email"],
                    "url": f'/customers/{customer["id"]}/',
                }
            )

        # Buscar contratos
        contracts = (
            Contract.objects.filter(
                agent=request.user, contract_number__icontains=query
            )
            .select_related("property", "customer")
            .values(
                "id",
                "contract_number",
                "property__title",
                "customer__first_name",
                "customer__last_name",
            )[:5]
        )

        for contract in contracts:
            results.append(
                {
                    "type": "contract",
                    "id": contract["id"],
                    "title": f"Contrato #{contract['contract_number']}",
                    "subtitle": f"{contract['property__title']} - {contract['customer__first_name']} {contract['customer__last_name']}",
                    "url": f'/contracts/{contract["id"]}/',
                }
            )

    return JsonResponse({"results": results})