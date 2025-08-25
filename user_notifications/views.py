from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from django.urls import reverse
from .models import Notification
from .models_preferences import NotificationPreference
from .forms import NotificationPreferenceForm

@login_required
def notification_list(request):
    """Enhanced notification list view with pagination, filtering, and improved styling"""
    
    # Get all notifications for the current user
    notifications = Notification.objects.filter(agent=request.user)
    
    # Apply filters
    notification_type = request.GET.get('type')
    read_status = request.GET.get('read_status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if notification_type and notification_type != 'all':
        notifications = notifications.filter(notification_type=notification_type)
    
    if read_status:
        if read_status == 'read':
            notifications = notifications.filter(is_read=True)
        elif read_status == 'unread':
            notifications = notifications.filter(is_read=False)
    
    if date_from:
        try:
            date_from_parsed = timezone.datetime.strptime(date_from, '%Y-%m-%d').date()
            notifications = notifications.filter(created_at__date__gte=date_from_parsed)
        except ValueError:
            messages.warning(request, 'Formato de fecha inválido para "Fecha desde"')
    
    if date_to:
        try:
            date_to_parsed = timezone.datetime.strptime(date_to, '%Y-%m-%d').date()
            notifications = notifications.filter(created_at__date__lte=date_to_parsed)
        except ValueError:
            messages.warning(request, 'Formato de fecha inválido para "Fecha hasta"')
    
    # Order by creation date (most recent first)
    notifications = notifications.order_by('-created_at')
    
    # Get notification counts for filters
    all_notifications = Notification.objects.filter(agent=request.user)
    notification_counts = {
        'all': all_notifications.count(),
        'unread': all_notifications.filter(is_read=False).count(),
        'read': all_notifications.filter(is_read=True).count(),
    }
    
    # Get counts by type
    for choice_value, choice_label in Notification.TYPE_CHOICES:
        notification_counts[choice_value] = all_notifications.filter(
            notification_type=choice_value
        ).count()
    
    # Pagination
    paginator = Paginator(notifications, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Prepare filter choices
    notification_type_choices = [('all', 'Todas')] + list(Notification.TYPE_CHOICES)
    read_status_choices = [
        ('all', 'Todas'),
        ('unread', 'No leídas'),
        ('read', 'Leídas'),
    ]
    
    context = {
        'notifications': page_obj,
        'notification_counts': notification_counts,
        'notification_type_choices': notification_type_choices,
        'read_status_choices': read_status_choices,
        'selected_type': notification_type or 'all',
        'selected_read_status': read_status or 'all',
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'user_notifications/notification_list.html', context)


@login_required
def notification_detail(request, pk):
    """Detailed notification view that shows full context and related object information"""
    
    notification = get_object_or_404(Notification, pk=pk, agent=request.user)
    
    # Mark as read when viewed
    if not notification.is_read:
        notification.mark_as_read()
    
    # Get related object URL if available
    related_object_url = notification.get_related_object_url()
    
    # Get related object details for display
    related_object_info = None
    if notification.related_object:
        related_object_info = {
            'object': notification.related_object,
            'type': notification.content_type.model,
            'url': related_object_url,
        }
    
    context = {
        'notification': notification,
        'related_object_info': related_object_info,
    }
    
    return render(request, 'user_notifications/notification_detail.html', context)


@login_required
def mark_notification_read(request, pk):
    """AJAX endpoint for marking notifications as read without page refresh"""
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        notification = get_object_or_404(Notification, pk=pk, agent=request.user)
        notification.mark_as_read()
        
        # Get updated unread count
        unread_count = Notification.objects.filter(agent=request.user, is_read=False).count()
        
        return JsonResponse({
            'success': True,
            'unread_count': unread_count,
            'message': 'Notificación marcada como leída'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def mark_all_notifications_read(request):
    """AJAX endpoint for marking all notifications as read"""
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        # Update all unread notifications for the user
        updated_count = Notification.objects.filter(
            agent=request.user,
            is_read=False
        ).update(is_read=True)
        
        return JsonResponse({
            'success': True,
            'updated_count': updated_count,
            'message': f'{updated_count} notificaciones marcadas como leídas'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def notification_count(request):
    """AJAX endpoint to get current notification count"""
    
    try:
        unread_count = Notification.objects.filter(
            agent=request.user,
            is_read=False
        ).count()
        
        total_count = Notification.objects.filter(
            agent=request.user
        ).count()
        
        return JsonResponse({
            'success': True,
            'unread_count': unread_count,
            'total_count': total_count
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def notification_preferences(request):
    """Vista para configurar las preferencias de notificaciones"""
    
    # Obtener o crear las preferencias del usuario
    preferences, created = NotificationPreference.objects.get_or_create(
        agent=request.user,
        defaults={
            'receive_invoice_due_soon': True,
            'receive_invoice_overdue': True,
            'receive_invoice_payment': True,
            'receive_invoice_status_change': True,
            'notification_frequency': 'immediately',
            'days_before_due_date': 7,
            'email_notifications': False,
        }
    )
    
    if request.method == 'POST':
        form = NotificationPreferenceForm(request.POST, instance=preferences)
        if form.is_valid():
            form.save()
            messages.success(request, "Preferencias de notificaciones actualizadas correctamente")
            return redirect('user_notifications:notification_preferences')
    else:
        form = NotificationPreferenceForm(instance=preferences)
    
    return render(request, 'user_notifications/notification_preferences.html', {
        'form': form,
        'preferences': preferences,
    })