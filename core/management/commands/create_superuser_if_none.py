from django.core.management.base import BaseCommand
from agents.models import Agent


class Command(BaseCommand):
    help = 'Create a superuser if none exists'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='admin', help='Username for the superuser')
        parser.add_argument('--email', default='admin@example.com', help='Email for the superuser')
        parser.add_argument('--password', default='admin123', help='Password for the superuser')

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']

        if Agent.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f'Superuser "{username}" already exists')
            )
            return

        try:
            admin_user = Agent.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name='Admin',
                last_name='User'
            )
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'Superuser "{username}" created successfully with password "{password}"')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating superuser: {e}')
            )