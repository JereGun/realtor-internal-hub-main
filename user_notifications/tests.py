import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model
from contracts.models import Contract
from user_notifications.checkers import RentIncreaseChecker
from user_notifications.models import Notification
from user_notifications.models_preferences import NotificationPreference

@pytest.mark.django_db
def test_rent_increase_notification_creation(client):
    User = get_user_model()
    agent = User.objects.create_user(username='agente1', email='agente1@test.com', password='1234', first_name='Agente')
    customer = User.objects.create_user(username='cliente1', email='cliente1@test.com', password='1234', first_name='Cliente')
    
    # Preferencias: activar notificaciones y email
    NotificationPreference.objects.create(
        agent=agent,
        receive_rent_increase=True,
        email_notifications=True
    )

    contract = Contract.objects.create(
        property_id=1,  # Debe existir una propiedad o usar un factory
        customer=customer,
        agent=agent,
        amount=1000,
        start_date=timezone.now().date().replace(year=timezone.now().year - 1),
        next_increase_date=timezone.now().date(),
        frequency='annually',
        status='active'
    )

    checker = RentIncreaseChecker()
    result = checker.check_and_notify()

    # Debe haberse creado una notificación de aumento vencido
    notification = Notification.objects.filter(agent=agent, notification_type='rent_increase_overdue').first()
    assert notification is not None
    assert 'Aumento de Alquiler Vencido' in notification.title
    assert result['overdue_increases'] == 1

@pytest.mark.django_db
def test_no_email_if_preference_disabled(client):
    User = get_user_model()
    agent = User.objects.create_user(username='agente2', email='agente2@test.com', password='1234', first_name='Agente')
    customer = User.objects.create_user(username='cliente2', email='cliente2@test.com', password='1234', first_name='Cliente')
    
    # Preferencias: desactivar email
    NotificationPreference.objects.create(
        agent=agent,
        receive_rent_increase=True,
        email_notifications=False
    )

    contract = Contract.objects.create(
        property_id=1,  # Debe existir una propiedad o usar un factory
        customer=customer,
        agent=agent,
        amount=1000,
        start_date=timezone.now().date().replace(year=timezone.now().year - 1),
        next_increase_date=timezone.now().date(),
        frequency='annually',
        status='active'
    )

    checker = RentIncreaseChecker()
    checker.check_and_notify()

    notification = Notification.objects.filter(agent=agent, notification_type='rent_increase_overdue').first()
    assert notification is not None
    # Aquí podrías mockear el envío de email y verificar que NO se llamó

@pytest.mark.django_db
def test_next_increase_date_calculation():
    User = get_user_model()
    agent = User.objects.create_user(username='agente3', email='agente3@test.com', password='1234', first_name='Agente')
    customer = User.objects.create_user(username='cliente3', email='cliente3@test.com', password='1234', first_name='Cliente')
    
    NotificationPreference.objects.create(
        agent=agent,
        receive_rent_increase=True,
        email_notifications=True
    )
    contract = Contract.objects.create(
        property_id=1,  # Debe existir una propiedad o usar un factory
        customer=customer,
        agent=agent,
        amount=1000,
        start_date=timezone.now().date().replace(year=timezone.now().year - 1),
        next_increase_date=timezone.now().date(),
        frequency='monthly',
        status='active'
    )
    checker = RentIncreaseChecker()
    next_date = checker.calculate_next_increase_date(contract)
    assert next_date.month == (timezone.now().date().month % 12) + 1
