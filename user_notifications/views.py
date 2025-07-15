from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, View
from django.urls import reverse_lazy
from .models import Notification

class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = 'user_notifications/notification_list.html'
    context_object_name = 'notifications'
    paginate_by = 20

    def get_queryset(self):
        return Notification.objects.filter(agent=self.request.user).order_by('-created_at')

class MarkAsReadView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notification = Notification.objects.get(pk=pk)
        notification.is_read = True
        notification.save()
        return redirect('user_notifications:notification_list')

class MarkAllAsReadView(LoginRequiredMixin, View):
    def post(self, request):
        Notification.objects.filter(agent=request.user, is_read=False).update(is_read=True)
        return redirect('user_notifications:notification_list')
