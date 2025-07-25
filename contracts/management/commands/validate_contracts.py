from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from contracts.models import Contract, ContractIncrease
from django.db import transaction


class Command(BaseCommand):
    help = (
        "Valida todos los contratos existentes contra las nuevas reglas de validación"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--fix-errors",
            action="store_true",
            help="Intenta corregir automáticamente algunos errores de validación",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Muestra información detallada de cada validación",
        )

    def handle(self, *args, **options):
        fix_errors = options["fix_errors"]
        verbose = options["verbose"]

        self.stdout.write(self.style.SUCCESS("=== VALIDACIÓN DE CONTRATOS ===\n"))

        # Validar contratos
        self.validate_contracts(fix_errors, verbose)

        # Validar aumentos
        self.validate_contract_increases(fix_errors, verbose)

        self.stdout.write(self.style.SUCCESS("\n=== VALIDACIÓN COMPLETADA ==="))

    def validate_contracts(self, fix_errors, verbose):
        """Valida todos los contratos"""
        self.stdout.write("Validando contratos...\n")

        contracts = Contract.objects.all()
        valid_count = 0
        error_count = 0
        fixed_count = 0

        for contract in contracts:
            try:
                contract.full_clean()
                valid_count += 1
                if verbose:
                    self.stdout.write(f"✓ Contrato {contract.id}: Válido")

            except ValidationError as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f"✗ Contrato {contract.id}: {e}"))

                # Intentar corregir algunos errores automáticamente
                if fix_errors:
                    fixed = self.try_fix_contract_errors(contract, e)
                    if fixed:
                        fixed_count += 1
                        self.stdout.write(
                            self.style.WARNING(f"  → Corregido automáticamente")
                        )

        # Resumen de contratos
        self.stdout.write(f"\nRESUMEN CONTRATOS:")
        self.stdout.write(f"  Válidos: {valid_count}")
        self.stdout.write(f"  Con errores: {error_count}")
        if fix_errors:
            self.stdout.write(f"  Corregidos: {fixed_count}")

    def validate_contract_increases(self, fix_errors, verbose):
        """Valida todos los aumentos de contratos"""
        self.stdout.write("\nValidando aumentos de contratos...\n")

        increases = ContractIncrease.objects.all()
        valid_count = 0
        error_count = 0
        fixed_count = 0

        for increase in increases:
            try:
                increase.full_clean()
                valid_count += 1
                if verbose:
                    self.stdout.write(f"✓ Aumento {increase.id}: Válido")

            except ValidationError as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f"✗ Aumento {increase.id}: {e}"))

                # Intentar corregir algunos errores automáticamente
                if fix_errors:
                    fixed = self.try_fix_increase_errors(increase, e)
                    if fixed:
                        fixed_count += 1
                        self.stdout.write(
                            self.style.WARNING(f"  → Corregido automáticamente")
                        )

        # Resumen de aumentos
        self.stdout.write(f"\nRESUMEN AUMENTOS:")
        self.stdout.write(f"  Válidos: {valid_count}")
        self.stdout.write(f"  Con errores: {error_count}")
        if fix_errors:
            self.stdout.write(f"  Corregidos: {fixed_count}")

    def try_fix_contract_errors(self, contract, validation_error):
        """
        Intenta corregir automáticamente algunos errores comunes en contratos

        Returns:
            bool: True si se pudo corregir el error
        """
        try:
            with transaction.atomic():
                fixed = False

                # Corregir montos negativos o cero
                if contract.amount <= 0:
                    # No podemos asumir un monto, solo reportar
                    self.stdout.write(
                        self.style.WARNING(
                            f"    Monto inválido ({contract.amount}) - requiere corrección manual"
                        )
                    )
                    return False

                # Corregir fechas de próximo aumento inválidas
                if contract.next_increase_date:
                    if (
                        contract.start_date
                        and contract.next_increase_date < contract.start_date
                    ):
                        contract.next_increase_date = contract.start_date
                        fixed = True

                    if (
                        contract.end_date
                        and contract.next_increase_date > contract.end_date
                    ):
                        contract.next_increase_date = None
                        fixed = True

                # Corregir porcentajes de aumento extremos
                if contract.increase_percentage:
                    if contract.increase_percentage < -100:
                        contract.increase_percentage = -100
                        fixed = True
                    elif contract.increase_percentage > 1000:
                        contract.increase_percentage = 1000
                        fixed = True

                if fixed:
                    contract.save()
                    return True

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"    Error al intentar corregir: {e}"))

        return False

    def try_fix_increase_errors(self, increase, validation_error):
        """
        Intenta corregir automáticamente algunos errores comunes en aumentos

        Returns:
            bool: True si se pudo corregir el error
        """
        try:
            with transaction.atomic():
                fixed = False

                # Corregir porcentajes extremos
                if increase.increase_percentage < -100:
                    increase.increase_percentage = -100
                    fixed = True
                elif increase.increase_percentage > 1000:
                    increase.increase_percentage = 1000
                    fixed = True

                # Recalcular porcentaje si los montos son válidos
                if (
                    increase.previous_amount > 0
                    and increase.new_amount > 0
                    and (
                        increase.increase_percentage is None
                        or increase.increase_percentage == 0
                    )
                ):
                    increase.increase_percentage = (
                        (increase.new_amount - increase.previous_amount)
                        / increase.previous_amount
                    ) * 100
                    fixed = True

                if fixed:
                    increase.save()
                    return True

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"    Error al intentar corregir: {e}"))

        return False
