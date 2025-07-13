
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.urls import reverse_lazy
from django.db.models import Q
from django.utils import timezone
from .models import TaskNotification
from .forms import TaskNotificationForm, TaskSearchForm
from agents.models import Agent


class TaskNotificationListView(LoginRequiredMixin, ListView):
    model = TaskNotification
    template_name = 'notifications/task_list.html'
    context_object_name = 'tasks'
    paginate_by = 20
    
    def get_queryset(self):
        # LoginRequiredMixin asegura que request.user es un usuario autenticado (un Agent).
        queryset = TaskNotification.objects.filter(agent=self.request.user).select_related('property', 'customer', 'contract')
        
        form = TaskSearchForm(self.request.GET)
        if form.is_valid():
            search = form.cleaned_data.get('search')
            status = form.cleaned_data.get('status')
            priority = form.cleaned_data.get('priority')
            
            if search:
                queryset = queryset.filter(
                    Q(title__icontains=search) |
                    Q(description__icontains=search)
                )
            
            if status:
                queryset = queryset.filter(status=status)
            
            if priority:
                queryset = queryset.filter(priority=priority)
        
        return queryset.order_by('due_date', '-priority')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = TaskSearchForm(self.request.GET)
        
        # Add summary statistics
        now = timezone.now()
        context['overdue_count'] = TaskNotification.objects.filter(
            status='pending',
            due_date__lt=now
        ).count()
        context['pending_count'] = TaskNotification.objects.filter(status='pending').count()
        context['urgent_count'] = TaskNotification.objects.filter(
            status='pending',
            priority='urgent'
        ).count()
        
        return context


class TaskNotificationDetailView(LoginRequiredMixin, DetailView):
    model = TaskNotification
    template_name = 'notifications/task_detail.html'
    context_object_name = 'task'


class TaskNotificationCreateView(LoginRequiredMixin, CreateView):
    model = TaskNotification
    form_class = TaskNotificationForm
    template_name = 'notifications/task_form.html'
    success_url = reverse_lazy('notifications:task_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Tarea creada correctamente.')
        return super().form_valid(form)


class TaskNotificationUpdateView(LoginRequiredMixin, UpdateView):
    model = TaskNotification
    form_class = TaskNotificationForm
    template_name = 'notifications/task_form.html'
    success_url = reverse_lazy('notifications:task_list')
    
    def form_valid(self, form):
        # Set completed_at when marking as completed
        if form.cleaned_data['status'] == 'completed' and not self.object.completed_at:
            form.instance.completed_at = timezone.now()
        
        messages.success(self.request, 'Tarea actualizada correctamente.')
        return super().form_valid(form)


class TaskNotificationDeleteView(LoginRequiredMixin, DeleteView):
    model = TaskNotification
    template_name = 'notifications/task_confirm_delete.html'
    success_url = reverse_lazy('notifications:task_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Tarea eliminada correctamente.')
        return super().delete(request, *args, **kwargs)

class MarkNotificationAsReadView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notification = TaskNotification.objects.get(pk=pk)
        notification.status = 'completed'
        notification.save()
        return redirect('notifications:task_list')
