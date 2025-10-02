# Solución: Error 400 al generar Comprobante de Propietario

## Problema

Al intentar generar un comprobante de propietario, se recibe un error HTTP 400 (Bad Request) en la consola del navegador:

```
POST http://127.0.0.1:8000/contabilidad/invoice/26/generate-owner-receipt/ 400 (Bad Request)
```

## Causa Raíz

El error se produce porque **la factura no tiene un número asignado**, lo cual es un requisito obligatorio para generar comprobantes de propietario.

### Validaciones que fallan

El sistema valida lo siguiente antes de generar un comprobante:

1. ✅ La factura debe existir
2. ❌ **La factura debe tener un número asignado** (este era el problema)
3. ✅ La factura debe estar en estado válido (validated, sent, paid)
4. ✅ La factura debe tener un contrato asociado
5. ✅ El contrato debe tener una propiedad asociada
6. ✅ La propiedad debe tener un propietario asignado
7. ✅ El propietario debe tener email configurado

## Síntomas

En los logs del servidor Django aparecen mensajes como:
```
WARNING accounting.views_web No se puede generar comprobante para factura 26: La factura no tiene número asignado
```

## Solución

### Opción 1: Solución Manual (Inmediata)

Para la factura específica que tiene el problema:

```python
# En Django shell o script
from accounting.models_invoice import Invoice

# Obtener la factura problemática
invoice = Invoice.objects.get(pk=26)  # Cambiar por el ID correcto

# Verificar que no tiene número
print(f"Número actual: '{invoice.number}'")

# Asignar número siguiendo el formato estándar
if not invoice.number:
    invoice.number = f'INV-2024-{invoice.pk:03d}'  # Usar año correcto
    invoice.save()
    print(f'Se asignó el número: {invoice.number}')
```

### Opción 2: Solución Automatizada (Prevención)

Se ha creado un comando de gestión Django para manejar este problema:

```bash
# Ver qué facturas tienen el problema (sin hacer cambios)
python manage.py assign_invoice_numbers --dry-run

# Asignar números automáticamente a todas las facturas sin número
python manage.py assign_invoice_numbers

# Asignar números para un año específico
python manage.py assign_invoice_numbers --year 2024
```

## Prevención

### 1. Validación en el modelo Invoice

Asegurar que el modelo `Invoice` siempre genere un número automáticamente al guardarse:

```python
class Invoice(models.Model):
    # ... otros campos ...
    
    def save(self, *args, **kwargs):
        if not self.number:
            # Generar número automáticamente
            year = self.date.year if self.date else timezone.now().year
            self.number = self._generate_invoice_number(year)
        super().save(*args, **kwargs)
    
    def _generate_invoice_number(self, year):
        # Lógica para generar número único
        # ...
```

### 2. Validación en formularios

Asegurar que los formularios de creación/edición de facturas siempre requieran o generen un número.

### 3. Migración de datos

Ejecutar periódicamente el comando para identificar y corregir facturas sin número:

```bash
# Como tarea de mantenimiento mensual
python manage.py assign_invoice_numbers --dry-run
```

## Verificación

Después de aplicar la solución, verificar que funciona:

```python
from accounting.validators import validate_owner_receipt_generation

# Verificar la factura específica
invoice = Invoice.objects.get(pk=26)
is_valid, error_msg, warnings = validate_owner_receipt_generation(invoice)

print(f'Válida: {is_valid}')
if not is_valid:
    print(f'Error: {error_msg}')
```

## Archivos Relacionados

- **Validador**: `accounting/validators.py` - Función `validate_owner_receipt_generation()`
- **Vista**: `accounting/views_web.py` - Función `generate_owner_receipt()`
- **Comando**: `accounting/management/commands/assign_invoice_numbers.py`
- **URL**: `/contabilidad/invoice/<id>/generate-owner-receipt/`

## Estado de la Solución

✅ **Resuelto**: El problema específico de la factura ID 26 ha sido solucionado asignando el número `INV-2024-026`.

✅ **Prevención**: Se creó el comando de gestión para prevenir futuros casos.

---

**Fecha**: 2025-10-02  
**Responsable**: Sistema de IA  
**Severidad**: Media (funcionalidad bloqueada pero fácil de solucionar)  
**Tiempo de resolución**: ~20 minutos
