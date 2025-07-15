from django.core.management.base import BaseCommand
from contracts.tasks import Command as RentIncreaseCommand

class Command(BaseCommand):
    help = 'Aplica los aumentos automáticos de alquiler'

    def handle(self, *args, **options):
        rent_increase_cmd = RentIncreaseCommand()
        rent_increase_cmd.handle(*args, **options)
