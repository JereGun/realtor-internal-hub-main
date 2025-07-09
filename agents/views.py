
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from .models import Agent
from .forms import AgentLoginForm, AgentForm


def agent_login(request):
    if request.method == 'POST':
        form = AgentLoginForm(data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, email=email, password=password)
            if user is not None:
                login(request, user)
                return redirect('properties:property_list')
            else:
                messages.error(request, 'Email o contraseña incorrectos.')
    else:
        form = AgentLoginForm()
    
    return render(request, 'agents/login.html', {'form': form})


def agent_logout(request):
    logout(request)
    messages.info(request, 'Has cerrado sesión correctamente.')
    return redirect('agents:login')


class AgentListView(LoginRequiredMixin, ListView):
    model = Agent
    template_name = 'agents/agent_list.html'
    context_object_name = 'agents'
    paginate_by = 20
    
    def get_queryset(self):
        return Agent.objects.filter(is_active=True).order_by('first_name', 'last_name')


class AgentDetailView(LoginRequiredMixin, DetailView):
    model = Agent
    template_name = 'agents/agent_detail.html'
    context_object_name = 'agent'


class AgentCreateView(LoginRequiredMixin, CreateView):
    model = Agent
    form_class = AgentForm
    template_name = 'agents/agent_form.html'
    success_url = reverse_lazy('agents:agent_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Agente creado correctamente.')
        return super().form_valid(form)


class AgentUpdateView(LoginRequiredMixin, UpdateView):
    model = Agent
    form_class = AgentForm
    template_name = 'agents/agent_form.html'
    success_url = reverse_lazy('agents:agent_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Agente actualizado correctamente.')
        return super().form_valid(form)


@login_required
def profile_view(request):
    return render(request, 'agents/profile.html', {'agent': request.user})
