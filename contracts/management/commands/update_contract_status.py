from django.core.management.base import BaseCommand
from django.utils import timezone
from contracts.models import Contract
from django.db import transaction


class Command(BaseCommand):
    help = (
        "Actualiza automáticamente el estado de los contratos basándose en las fechas"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Ejecuta el comando sin hacer cambios reales en la base de datos",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        today = timezone.now().date()

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "MODO DRY-RUN: No se realizarán cambios en la base de datos"
                )
            )

        # Obtener todos los contratos que no están cancelados o ya finalizados
        contracts = Contract.objects.exclude(
            status__in=[Contract.STATUS_CANCELLED, Contract.STATUS_FINISHED]
        )

        updated_count = 0
        finished_count = 0

        for contract in contracts:
            old_status = contract.status
            old_is_active = contract.is_active

            # Actualizar el estado del contrato
            contract.update_status()

            # Verificar si hubo cambios
            if contract.status != old_status or contract.is_active != old_is_active:
                if not dry_run:
                    try:
                        with transaction.atomic():
                            contract.save(update_fields=["status", "is_active"])
                            updated_count += 1

                            if contract.status == Contract.STATUS_FINISHED:
                                finished_count += 1

                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"Contrato {contract.id} actualizado: "
                                    f"{old_status} → {contract.status} "
                                    f"(Activo: {old_is_active} → {contract.is_active})"
                                )
                            )
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(
                                f"Error al actualizar contrato {contract.id}: {str(e)}"
                            )
                        )
                else:
                    # Modo dry-run: solo mostrar lo que se haría
                    updated_count += 1
                    if contract.status == Contract.STATUS_FINISHED:
                        finished_count += 1

                    self.stdout.write(
                        self.style.WARNING(
                            f"[DRY-RUN] Contrato {contract.id} se actualizaría: "
                            f"{old_status} → {contract.status} "
                            f"(Activo: {old_is_active} → {contract.is_active})"
                        )
                    )

        # Resumen de la ejecución
        if updated_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n=== RESUMEN ==="
                    f"\nContratos actualizados: {updated_count}"
                    f"\nContratos finalizados automáticamente: {finished_count}"
                    f"\nFecha de ejecución: {today}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"No se encontraron contratos que requieran actualización de estado."
                )
            )
