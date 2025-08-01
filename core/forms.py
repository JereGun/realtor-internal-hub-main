import re
from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from PIL import Image
from .models import (
    Company,
    CompanyConfiguration,
    DocumentTemplate,
    NotificationSettings,
    SystemConfiguration,
)


class CompanyBasicForm(forms.ModelForm):
    """
    Formulario extendido para datos básicos de la empresa.

    Incluye validaciones específicas para datos corporativos,
    manejo mejorado de carga de logotipos y validaciones de formato.
    """

    # Validador para NIF/CIF español
    tax_id_validator = RegexValidator(
        regex=r"^[A-Z]\d{8}$|^\d{8}[A-Z]$",
        message="Formato de NIF/CIF inválido. Debe ser: A12345678 o 12345678A",
    )

    # Validador para teléfonos españoles
    phone_validator = RegexValidator(
        regex=r"^\+34\s?[6-9]\d{8}$|^[6-9]\d{8}$",
        message="Formato de teléfono inválido. Debe ser: +34 612345678 o 612345678",
    )

    class Meta:
        model = Company
        fields = ["name", "address", "phone", "email", "website", "logo", "tax_id"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nombre de la empresa",
                    "required": True,
                }
            ),
            "address": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Dirección completa de la empresa",
                }
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "+34 612 345 678"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "contacto@empresa.com"}
            ),
            "website": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://www.empresa.com",
                }
            ),
            "logo": forms.FileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/png,image/jpeg,image/svg+xml",
                }
            ),
            "tax_id": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "B12345678"}
            ),
        }
        labels = {
            "name": "Nombre de la empresa *",
            "address": "Dirección",
            "phone": "Teléfono",
            "email": "Email de contacto",
            "website": "Sitio web",
            "logo": "Logotipo",
            "tax_id": "NIF/CIF",
        }
        help_texts = {
            "name": "Nombre oficial de la empresa tal como aparece en documentos legales",
            "address": "Dirección completa incluyendo código postal",
            "phone": "Número de teléfono principal de contacto",
            "email": "Dirección de email principal para comunicaciones",
            "website": "URL completa del sitio web de la empresa",
            "logo": "Imagen del logotipo (PNG, JPG, SVG). Máximo 2MB, se redimensionará automáticamente",
            "tax_id": "Número de identificación fiscal (NIF/CIF)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Aplicar validadores personalizados
        self.fields["tax_id"].validators.append(self.tax_id_validator)
        self.fields["phone"].validators.append(self.phone_validator)

        # Hacer el nombre obligatorio
        self.fields["name"].required = True

    def clean_name(self):
        """Validación personalizada para el nombre de la empresa"""
        name = self.cleaned_data.get("name")
        if name:
            # Verificar que no sea solo espacios
            if not name.strip():
                raise ValidationError("El nombre de la empresa no puede estar vacío.")

            # Verificar longitud mínima
            if len(name.strip()) < 3:
                raise ValidationError(
                    "El nombre de la empresa debe tener al menos 3 caracteres."
                )

            # Verificar caracteres válidos
            if not re.match(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑ0-9\s\.\,\-\_\&]+$", name):
                raise ValidationError("El nombre contiene caracteres no válidos.")

        return name.strip() if name else name

    def clean_email(self):
        """Validación personalizada para el email"""
        email = self.cleaned_data.get("email")
        if email:
            # Verificar formato básico (Django ya hace esto, pero agregamos validaciones extra)
            if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
                raise ValidationError("Formato de email inválido.")

            # Verificar que no sea un email temporal conocido
            temp_domains = ["10minutemail.com", "tempmail.org", "guerrillamail.com"]
            domain = email.split("@")[1].lower()
            if domain in temp_domains:
                raise ValidationError("No se permiten direcciones de email temporales.")

        return email.lower() if email else email

    def clean_website(self):
        """Validación personalizada para el sitio web"""
        website = self.cleaned_data.get("website")
        if website:
            # Agregar protocolo si no lo tiene
            if not website.startswith(("http://", "https://")):
                website = "https://" + website

            # Validar formato URL
            url_pattern = re.compile(
                r"^https?://"  # protocolo
                r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # dominio
                r"localhost|"  # localhost
                r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # IP
                r"(?::\d+)?"  # puerto opcional
                r"(?:/?|[/?]\S+)$",
                re.IGNORECASE,
            )

            if not url_pattern.match(website):
                raise ValidationError("Formato de URL inválido.")

        return website

    def clean_phone(self):
        """Validación personalizada para el teléfono"""
        phone = self.cleaned_data.get("phone")
        if phone:
            # Limpiar espacios y caracteres especiales
            cleaned_phone = re.sub(r"[\s\-\(\)]", "", phone)

            # Agregar prefijo +34 si no lo tiene
            if (
                cleaned_phone.startswith("6")
                or cleaned_phone.startswith("7")
                or cleaned_phone.startswith("8")
                or cleaned_phone.startswith("9")
            ):
                if len(cleaned_phone) == 9:
                    cleaned_phone = "+34" + cleaned_phone

            # Validar formato final
            if not re.match(r"^\+34[6-9]\d{8}$", cleaned_phone):
                raise ValidationError(
                    "Formato de teléfono inválido. Use: +34612345678 o 612345678"
                )

            return cleaned_phone

        return phone

    def clean_logo(self):
        """Validación personalizada para el logotipo"""
        logo = self.cleaned_data.get("logo")
        if logo:
            # Verificar tamaño del archivo (máximo 2MB)
            if logo.size > 2 * 1024 * 1024:
                raise ValidationError("El archivo es demasiado grande. Máximo 2MB.")

            # Verificar tipo de archivo
            allowed_types = ["image/jpeg", "image/png", "image/svg+xml"]
            if logo.content_type not in allowed_types:
                raise ValidationError(
                    "Formato de archivo no válido. Use PNG, JPG o SVG."
                )

            # Para imágenes raster, verificar dimensiones y redimensionar si es necesario
            if logo.content_type in ["image/jpeg", "image/png"]:
                try:
                    image = Image.open(logo)

                    # Verificar dimensiones máximas
                    max_width, max_height = 800, 600
                    if image.width > max_width or image.height > max_height:
                        # Redimensionar manteniendo proporción
                        image.thumbnail(
                            (max_width, max_height), Image.Resampling.LANCZOS
                        )

                        # Guardar imagen redimensionada
                        from io import BytesIO

                        output = BytesIO()
                        format = "PNG" if logo.content_type == "image/png" else "JPEG"
                        image.save(output, format=format, quality=85)
                        output.seek(0)

                        # Crear nuevo archivo con imagen redimensionada
                        from django.core.files.base import ContentFile

                        logo = ContentFile(output.read(), name=logo.name)

                except Exception as e:
                    raise ValidationError(f"Error procesando la imagen: {str(e)}")

        return logo

    def clean_tax_id(self):
        """Validación personalizada para NIF/CIF"""
        tax_id = self.cleaned_data.get("tax_id")
        if tax_id:
            tax_id = tax_id.upper().strip()

            # Validar formato básico
            if not re.match(r"^[A-Z]\d{8}$|^\d{8}[A-Z]$", tax_id):
                raise ValidationError("Formato de NIF/CIF inválido.")

            # Validar dígito de control para NIF
            if re.match(r"^\d{8}[A-Z]$", tax_id):
                letters = "TRWAGMYFPDXBNJZSQVHLCKE"
                number = int(tax_id[:8])
                letter = tax_id[8]
                if letters[number % 23] != letter:
                    raise ValidationError("Dígito de control del NIF incorrecto.")

        return tax_id

    def save(self, commit=True):
        """Guardar con procesamiento adicional"""
        instance = super().save(commit=False)

        # Procesar campos antes de guardar
        if instance.name:
            instance.name = instance.name.strip()

        if commit:
            instance.save()

        return instance


class CompanyForm(CompanyBasicForm):
    """Alias para compatibilidad con código existente"""

    pass


class ContactInfoForm(forms.Form):
    """
    Formulario para información de contacto y ubicación de la empresa.

    Incluye validación de emails, números telefónicos y direcciones completas
    con soporte para múltiples tipos de contacto.
    """

    # Campos de dirección
    street_address = forms.CharField(
        label="Dirección",
        max_length=200,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Calle, número, piso, puerta",
            }
        ),
        help_text="Dirección completa de la calle",
    )

    city = forms.CharField(
        label="Ciudad",
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Madrid"}
        ),
    )

    state_province = forms.CharField(
        label="Provincia/Estado",
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Madrid"}
        ),
    )

    postal_code = forms.CharField(
        label="Código Postal",
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "28001"}),
        validators=[
            RegexValidator(
                regex=r"^\d{5}$", message="Código postal debe tener 5 dígitos"
            )
        ],
    )

    country = forms.CharField(
        label="País",
        max_length=100,
        initial="España",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "España"}
        ),
    )

    # Campos de contacto principal
    primary_email = forms.EmailField(
        label="Email Principal",
        required=False,
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "contacto@empresa.com"}
        ),
        help_text="Email principal para comunicaciones oficiales",
    )

    primary_phone = forms.CharField(
        label="Teléfono Principal",
        max_length=20,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "+34 912 345 678"}
        ),
        help_text="Número de teléfono principal",
    )

    # Campos de contacto secundario
    secondary_email = forms.EmailField(
        label="Email Secundario",
        required=False,
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "info@empresa.com"}
        ),
        help_text="Email alternativo (opcional)",
    )

    secondary_phone = forms.CharField(
        label="Teléfono Secundario",
        max_length=20,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "+34 612 345 678"}
        ),
        help_text="Número de teléfono alternativo",
    )

    # Teléfono móvil
    mobile_phone = forms.CharField(
        label="Teléfono Móvil",
        max_length=20,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "+34 612 345 678"}
        ),
        help_text="Número de móvil de contacto",
    )

    # Fax
    fax_number = forms.CharField(
        label="Fax",
        max_length=20,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "+34 912 345 679"}
        ),
        help_text="Número de fax (opcional)",
    )

    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop("company", None)
        super().__init__(*args, **kwargs)

        # Cargar datos existentes si hay una empresa
        if self.company:
            self._load_existing_data()

    def _load_existing_data(self):
        """Carga datos existentes de la empresa y configuraciones"""
        if not self.company:
            return

        # Cargar datos básicos de la empresa
        if self.company.address:
            # Intentar parsear la dirección existente
            address_parts = self.company.address.split(",")
            if len(address_parts) >= 1:
                self.fields["street_address"].initial = address_parts[0].strip()
            if len(address_parts) >= 2:
                self.fields["city"].initial = address_parts[1].strip()

        self.fields["primary_email"].initial = self.company.email
        self.fields["primary_phone"].initial = self.company.phone

        # Cargar configuraciones adicionales
        try:
            configs = {
                config.config_key: config.config_value
                for config in self.company.configurations.all()
            }

            # Mapear configuraciones a campos del formulario
            field_mapping = {
                "secondary_email": "secondary_email",
                "secondary_phone": "secondary_phone",
                "mobile_phone": "mobile_phone",
                "fax_number": "fax_number",
                "city": "city",
                "state_province": "state_province",
                "postal_code": "postal_code",
                "country": "country",
            }

            for config_key, field_name in field_mapping.items():
                if config_key in configs and field_name in self.fields:
                    self.fields[field_name].initial = configs[config_key]

        except Exception:
            pass  # Si no hay configuraciones, continuar sin error

    def clean_primary_phone(self):
        """Validación para teléfono principal"""
        return self._clean_phone_field("primary_phone")

    def clean_secondary_phone(self):
        """Validación para teléfono secundario"""
        return self._clean_phone_field("secondary_phone")

    def clean_mobile_phone(self):
        """Validación para teléfono móvil"""
        phone = self._clean_phone_field("mobile_phone")
        if phone:
            # Verificar que sea un móvil (empiece por 6, 7, 8 o 9)
            clean_number = re.sub(r"[^\d]", "", phone)
            if len(clean_number) >= 9:
                mobile_digit = clean_number[-9]
                if mobile_digit not in ["6", "7", "8", "9"]:
                    raise ValidationError(
                        "El número móvil debe empezar por 6, 7, 8 o 9"
                    )
        return phone

    def clean_fax_number(self):
        """Validación para número de fax"""
        return self._clean_phone_field("fax_number")

    def _clean_phone_field(self, field_name):
        """Método auxiliar para limpiar campos de teléfono"""
        phone = self.cleaned_data.get(field_name)
        if phone:
            # Limpiar espacios y caracteres especiales
            cleaned_phone = re.sub(r"[\s\-\(\)]", "", phone)

            # Agregar prefijo +34 si no lo tiene y es un número español
            if (
                cleaned_phone.startswith(("6", "7", "8", "9"))
                and len(cleaned_phone) == 9
            ):
                cleaned_phone = "+34" + cleaned_phone
            elif cleaned_phone.startswith("34") and len(cleaned_phone) == 11:
                cleaned_phone = "+" + cleaned_phone

            # Validar formato final
            if not re.match(r"^\+\d{1,3}\d{6,14}$", cleaned_phone):
                raise ValidationError(f"Formato de teléfono inválido en {field_name}")

            return cleaned_phone
        return phone

    def clean_postal_code(self):
        """Validación para código postal"""
        postal_code = self.cleaned_data.get("postal_code")
        if postal_code:
            # Para España, validar formato de 5 dígitos
            country = self.cleaned_data.get("country", "").lower()
            if "españa" in country or "spain" in country:
                if not re.match(r"^\d{5}$", postal_code):
                    raise ValidationError("Código postal español debe tener 5 dígitos")
        return postal_code

    def clean(self):
        """Validación general del formulario"""
        cleaned_data = super().clean()

        # Verificar que al menos un método de contacto esté presente
        contact_fields = [
            "primary_email",
            "primary_phone",
            "secondary_email",
            "secondary_phone",
            "mobile_phone",
        ]
        has_contact = any(cleaned_data.get(field) for field in contact_fields)

        if not has_contact:
            raise ValidationError(
                "Debe proporcionar al menos un método de contacto (email o teléfono)"
            )

        return cleaned_data

    def save(self, company):
        """Guarda la información de contacto en la empresa y configuraciones"""
        if not company:
            raise ValueError("Se requiere una instancia de Company para guardar")

        # Actualizar campos básicos de la empresa
        company.email = self.cleaned_data.get("primary_email") or company.email
        company.phone = self.cleaned_data.get("primary_phone") or company.phone

        # Construir dirección completa
        address_parts = []
        if self.cleaned_data.get("street_address"):
            address_parts.append(self.cleaned_data["street_address"])
        if self.cleaned_data.get("city"):
            address_parts.append(self.cleaned_data["city"])
        if self.cleaned_data.get("postal_code"):
            address_parts.append(self.cleaned_data["postal_code"])

        if address_parts:
            company.address = ", ".join(address_parts)

        company.save()

        # Guardar configuraciones adicionales
        config_mapping = {
            "secondary_email": self.cleaned_data.get("secondary_email"),
            "secondary_phone": self.cleaned_data.get("secondary_phone"),
            "mobile_phone": self.cleaned_data.get("mobile_phone"),
            "fax_number": self.cleaned_data.get("fax_number"),
            "city": self.cleaned_data.get("city"),
            "state_province": self.cleaned_data.get("state_province"),
            "postal_code": self.cleaned_data.get("postal_code"),
            "country": self.cleaned_data.get("country"),
        }

        from .models import CompanyConfiguration

        for config_key, config_value in config_mapping.items():
            if config_value:  # Solo guardar si hay valor
                CompanyConfiguration.objects.update_or_create(
                    company=company,
                    config_key=config_key,
                    defaults={"config_value": config_value, "config_type": "string"},
                )

        return company


# Choices for SystemConfigForm - defined outside class to avoid NameError
CURRENCY_CHOICES = [
    ("EUR", "Euro (€)"),
    ("USD", "Dólar Estadounidense ($)"),
    ("GBP", "Libra Esterlina (£)"),
    ("JPY", "Yen Japonés (¥)"),
    ("CHF", "Franco Suizo (CHF)"),
    ("CAD", "Dólar Canadiense (CAD)"),
    ("AUD", "Dólar Australiano (AUD)"),
]

TIMEZONE_CHOICES = [
    ("Europe/Madrid", "Madrid (UTC+1/+2)"),
    ("Europe/London", "Londres (UTC+0/+1)"),
    ("Europe/Paris", "París (UTC+1/+2)"),
    ("Europe/Berlin", "Berlín (UTC+1/+2)"),
    ("Europe/Rome", "Roma (UTC+1/+2)"),
    ("America/New_York", "Nueva York (UTC-5/-4)"),
    ("America/Los_Angeles", "Los Ángeles (UTC-8/-7)"),
    ("America/Mexico_City", "Ciudad de México (UTC-6/-5)"),
    ("Asia/Tokyo", "Tokio (UTC+9)"),
    ("Asia/Shanghai", "Shanghái (UTC+8)"),
]

DATE_FORMAT_CHOICES = [
    ("DD/MM/YYYY", "DD/MM/YYYY (31/12/2024)"),
    ("MM/DD/YYYY", "MM/DD/YYYY (12/31/2024)"),
    ("YYYY-MM-DD", "YYYY-MM-DD (2024-12-31)"),
    ("DD-MM-YYYY", "DD-MM-YYYY (31-12-2024)"),
    ("DD.MM.YYYY", "DD.MM.YYYY (31.12.2024)"),
]

LANGUAGE_CHOICES = [
    ("es", "Español"),
    ("en", "English"),
    ("fr", "Français"),
    ("de", "Deutsch"),
    ("it", "Italiano"),
    ("pt", "Português"),
]


class SystemConfigForm(forms.ModelForm):
    """
    Formulario para configuraciones operacionales del sistema.

    Incluye configuración de moneda, zona horaria, formatos de fecha
    y validación de valores de configuración del sistema.
    """

    # Campos adicionales para configuraciones específicas
    decimal_places = forms.IntegerField(
        label="Decimales en moneda",
        min_value=0,
        max_value=4,
        initial=2,
        widget=forms.NumberInput(
            attrs={"class": "form-control", "min": "0", "max": "4"}
        ),
        help_text="Número de decimales para mostrar en cantidades monetarias",
    )

    tax_rate = forms.DecimalField(
        label="Tipo de IVA por defecto (%)",
        max_digits=5,
        decimal_places=2,
        initial=21.00,
        widget=forms.NumberInput(
            attrs={"class": "form-control", "step": "0.01", "min": "0", "max": "100"}
        ),
        help_text="Porcentaje de IVA que se aplicará por defecto",
    )

    invoice_prefix = forms.CharField(
        label="Prefijo de facturas",
        max_length=10,
        initial="FAC",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "FAC"}),
        help_text="Prefijo que aparecerá en los números de factura",
    )

    contract_prefix = forms.CharField(
        label="Prefijo de contratos",
        max_length=10,
        initial="CON",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "CON"}),
        help_text="Prefijo que aparecerá en los números de contrato",
    )

    receipt_prefix = forms.CharField(
        label="Prefijo de recibos",
        max_length=10,
        initial="REC",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "REC"}),
        help_text="Prefijo que aparecerá en los números de recibo",
    )

    class Meta:
        model = SystemConfiguration
        fields = ["currency", "timezone", "date_format", "language"]
        widgets = {
            "currency": forms.Select(
                choices=CURRENCY_CHOICES, attrs={"class": "form-control"}
            ),
            "timezone": forms.Select(
                choices=TIMEZONE_CHOICES, attrs={"class": "form-control"}
            ),
            "date_format": forms.Select(
                choices=DATE_FORMAT_CHOICES, attrs={"class": "form-control"}
            ),
            "language": forms.Select(
                choices=LANGUAGE_CHOICES, attrs={"class": "form-control"}
            ),
        }
        labels = {
            "currency": "Moneda por defecto",
            "timezone": "Zona horaria",
            "date_format": "Formato de fecha",
            "language": "Idioma del sistema",
        }
        help_texts = {
            "currency": "Moneda que se usará por defecto en transacciones",
            "timezone": "Zona horaria para mostrar fechas y horas",
            "date_format": "Formato para mostrar fechas en el sistema",
            "language": "Idioma principal del sistema",
        }

    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop("company", None)
        super().__init__(*args, **kwargs)

        # Cargar configuraciones adicionales si existe la empresa
        if self.company:
            self._load_additional_configs()

    def _load_additional_configs(self):
        """Carga configuraciones adicionales desde CompanyConfiguration"""
        try:
            configs = {
                config.config_key: config.config_value
                for config in self.company.configurations.all()
            }

            # Mapear configuraciones a campos del formulario
            if "decimal_places" in configs:
                self.fields["decimal_places"].initial = int(configs["decimal_places"])
            if "tax_rate" in configs:
                self.fields["tax_rate"].initial = float(configs["tax_rate"])
            if "invoice_prefix" in configs:
                self.fields["invoice_prefix"].initial = configs["invoice_prefix"]
            if "contract_prefix" in configs:
                self.fields["contract_prefix"].initial = configs["contract_prefix"]
            if "receipt_prefix" in configs:
                self.fields["receipt_prefix"].initial = configs["receipt_prefix"]

        except Exception:
            pass  # Si hay error cargando configuraciones, usar valores por defecto

    def clean_tax_rate(self):
        """Validación para el tipo de IVA"""
        tax_rate = self.cleaned_data.get("tax_rate")
        if tax_rate is not None:
            if tax_rate < 0 or tax_rate > 100:
                raise ValidationError("El tipo de IVA debe estar entre 0% y 100%")
        return tax_rate

    def clean_invoice_prefix(self):
        """Validación para prefijo de facturas"""
        return self._clean_prefix_field("invoice_prefix")

    def clean_contract_prefix(self):
        """Validación para prefijo de contratos"""
        return self._clean_prefix_field("contract_prefix")

    def clean_receipt_prefix(self):
        """Validación para prefijo de recibos"""
        return self._clean_prefix_field("receipt_prefix")

    def _clean_prefix_field(self, field_name):
        """Método auxiliar para validar prefijos"""
        prefix = self.cleaned_data.get(field_name)
        if prefix:
            prefix = prefix.upper().strip()

            # Verificar que solo contenga letras y números
            if not re.match(r"^[A-Z0-9]+$", prefix):
                raise ValidationError(
                    f"El prefijo solo puede contener letras y números"
                )

            # Verificar longitud
            if len(prefix) < 2 or len(prefix) > 10:
                raise ValidationError(f"El prefijo debe tener entre 2 y 10 caracteres")

        return prefix

    def clean(self):
        """Validación general del formulario"""
        cleaned_data = super().clean()

        # Verificar que los prefijos sean únicos
        prefixes = [
            cleaned_data.get("invoice_prefix"),
            cleaned_data.get("contract_prefix"),
            cleaned_data.get("receipt_prefix"),
        ]

        # Filtrar valores None y vacíos
        prefixes = [p for p in prefixes if p]

        if len(prefixes) != len(set(prefixes)):
            raise ValidationError("Los prefijos de documentos deben ser únicos")

        return cleaned_data

    def save(self, commit=True):
        """Guarda la configuración del sistema y configuraciones adicionales"""
        instance = super().save(commit=False)

        if commit:
            instance.save()

            # Guardar configuraciones adicionales
            if self.company:
                self._save_additional_configs()

        return instance

    def _save_additional_configs(self):
        """Guarda configuraciones adicionales en CompanyConfiguration"""
        from .models import CompanyConfiguration

        additional_configs = {
            "decimal_places": str(self.cleaned_data.get("decimal_places", 2)),
            "tax_rate": str(self.cleaned_data.get("tax_rate", 21.00)),
            "invoice_prefix": self.cleaned_data.get("invoice_prefix", "FAC"),
            "contract_prefix": self.cleaned_data.get("contract_prefix", "CON"),
            "receipt_prefix": self.cleaned_data.get("receipt_prefix", "REC"),
        }

        for config_key, config_value in additional_configs.items():
            if config_value:  # Solo guardar si hay valor
                config_type = "integer" if config_key == "decimal_places" else "string"
                if config_key == "tax_rate":
                    config_type = "decimal"

                CompanyConfiguration.objects.update_or_create(
                    company=self.company,
                    config_key=config_key,
                    defaults={"config_value": config_value, "config_type": config_type},
                )


# Choices for DocumentTemplateForm
TEMPLATE_TYPE_CHOICES = [
    ("invoice", "Factura"),
    ("contract", "Contrato"),
    ("receipt", "Recibo"),
    ("report", "Informe"),
    ("email", "Email"),
    ("letter", "Carta"),
]


class DocumentTemplateForm(forms.ModelForm):
    """
    Formulario para gestión de plantillas de documentos con editor avanzado.

    Incluye editor de plantillas con validación de sintaxis, sistema de preview
    en tiempo real y validación de variables dinámicas.
    """

    # Campo para preview en tiempo real
    preview_data = forms.CharField(
        widget=forms.HiddenInput(),
        required=False,
        help_text="Datos para preview (uso interno)",
    )

    class Meta:
        model = DocumentTemplate
        fields = [
            "template_name",
            "template_type",
            "header_content",
            "footer_content",
            "custom_css",
            "is_active",
        ]
        widgets = {
            "template_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Nombre de la plantilla"}
            ),
            "template_type": forms.Select(
                choices=TEMPLATE_TYPE_CHOICES, attrs={"class": "form-control"}
            ),
            "header_content": forms.Textarea(
                attrs={
                    "class": "form-control template-editor",
                    "rows": 8,
                    "placeholder": "Contenido del encabezado (HTML + variables Django)",
                    "data-editor": "html",
                }
            ),
            "footer_content": forms.Textarea(
                attrs={
                    "class": "form-control template-editor",
                    "rows": 6,
                    "placeholder": "Contenido del pie de página (HTML + variables Django)",
                    "data-editor": "html",
                }
            ),
            "custom_css": forms.Textarea(
                attrs={
                    "class": "form-control css-editor",
                    "rows": 10,
                    "placeholder": "CSS personalizado para la plantilla",
                    "data-editor": "css",
                }
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "template_name": "Nombre de la plantilla *",
            "template_type": "Tipo de documento *",
            "header_content": "Encabezado",
            "footer_content": "Pie de página",
            "custom_css": "CSS personalizado",
            "is_active": "Plantilla activa",
        }
        help_texts = {
            "template_name": "Nombre único para identificar la plantilla",
            "template_type": "Tipo de documento para el que se usará esta plantilla",
            "header_content": "HTML que aparecerá en la parte superior de los documentos",
            "footer_content": "HTML que aparecerá en la parte inferior de los documentos",
            "custom_css": "Estilos CSS personalizados para esta plantilla",
            "is_active": "Desmarcar para desactivar temporalmente la plantilla",
        }

    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop("company", None)
        super().__init__(*args, **kwargs)

        # Hacer campos obligatorios
        self.fields["template_name"].required = True
        self.fields["template_type"].required = True

        # Agregar información de variables disponibles como ayuda
        self._add_variable_help()

    def _add_variable_help(self):
        """Agrega información sobre variables disponibles"""
        from .services.document_template_service import DocumentTemplateService

        if self.company:
            service = DocumentTemplateService(self.company)

            # Variables base disponibles para todos los tipos
            base_vars = ", ".join(
                service.BASE_VARIABLES[:5]
            )  # Mostrar solo las primeras 5

            help_text = f"Variables disponibles: {base_vars}... "
            help_text += "Cambie el tipo de documento para ver variables específicas."

            self.fields["header_content"].help_text += f" {help_text}"
            self.fields["footer_content"].help_text += f" {help_text}"

    def clean_template_name(self):
        """Validación para el nombre de la plantilla"""
        template_name = self.cleaned_data.get("template_name")
        if template_name:
            template_name = template_name.strip()

            # Verificar que no esté vacío
            if not template_name:
                raise ValidationError("El nombre de la plantilla no puede estar vacío")

            # Verificar longitud
            if len(template_name) < 3:
                raise ValidationError("El nombre debe tener al menos 3 caracteres")

            # Verificar caracteres válidos
            if not re.match(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑ0-9\s\-\_]+$", template_name):
                raise ValidationError("El nombre contiene caracteres no válidos")

            # Verificar unicidad dentro de la empresa y tipo
            if self.company:
                template_type = self.cleaned_data.get("template_type")
                existing = DocumentTemplate.objects.filter(
                    company=self.company,
                    template_name=template_name,
                    template_type=template_type,
                    is_active=True,
                )

                # Excluir la instancia actual si estamos editando
                if self.instance and self.instance.pk:
                    existing = existing.exclude(pk=self.instance.pk)

                if existing.exists():
                    raise ValidationError(
                        f"Ya existe una plantilla activa con este nombre para el tipo {template_type}"
                    )

        return template_name

    def clean_header_content(self):
        """Validación para el contenido del encabezado"""
        return self._validate_template_content("header_content")

    def clean_footer_content(self):
        """Validación para el contenido del pie de página"""
        return self._validate_template_content("footer_content")

    def _validate_template_content(self, field_name):
        """Método auxiliar para validar contenido de plantillas"""
        content = self.cleaned_data.get(field_name)
        if content and self.company:
            from .services.document_template_service import DocumentTemplateService

            service = DocumentTemplateService(self.company)
            is_valid, error_msg = service.validate_template_syntax(content)

            if not is_valid:
                raise ValidationError(f"Error de sintaxis: {error_msg}")

        return content

    def clean_custom_css(self):
        """Validación básica para CSS personalizado"""
        css = self.cleaned_data.get("custom_css")
        if css:
            # Verificar que no contenga scripts maliciosos
            dangerous_patterns = [
                r"<script",
                r"javascript:",
                r"expression\s*\(",
                r"@import",
                r'url\s*\(\s*["\']?\s*javascript:',
            ]

            css_lower = css.lower()
            for pattern in dangerous_patterns:
                if re.search(pattern, css_lower):
                    raise ValidationError(
                        "El CSS contiene contenido potencialmente peligroso"
                    )

            # Verificar sintaxis básica de CSS
            if css.count("{") != css.count("}"):
                raise ValidationError("CSS mal formado: llaves no balanceadas")

        return css

    def clean(self):
        """Validación general del formulario"""
        cleaned_data = super().clean()

        # Verificar que al menos header o footer tenga contenido
        header = cleaned_data.get("header_content", "").strip()
        footer = cleaned_data.get("footer_content", "").strip()

        if not header and not footer:
            raise ValidationError(
                "La plantilla debe tener al menos contenido en el encabezado o pie de página"
            )

        return cleaned_data

    def get_available_variables(self):
        """Obtiene las variables disponibles para el tipo de plantilla actual"""
        if not self.company:
            return []

        from .services.document_template_service import DocumentTemplateService

        service = DocumentTemplateService(self.company)
        template_type = self.cleaned_data.get("template_type") or self.initial.get(
            "template_type", "invoice"
        )

        return service.get_available_variables(template_type)

    def generate_preview(self, template_content, template_type):
        """Genera una previsualización de la plantilla"""
        if not self.company:
            return "Preview no disponible sin empresa"

        try:
            from .services.document_template_service import DocumentTemplateService

            service = DocumentTemplateService(self.company)
            return service.preview_template(template_content, template_type)

        except Exception as e:
            return f"Error generando preview: {str(e)}"

    def save(self, commit=True):
        """Guarda la plantilla con validaciones adicionales"""
        instance = super().save(commit=False)

        # Asignar empresa si no está asignada
        if self.company and not instance.company:
            instance.company = self.company

        if commit:
            instance.save()

        return instance


# Choices for NotificationForm
NOTIFICATION_TYPE_CHOICES = [
    ("payment_reminder", "Recordatorio de pago"),
    ("contract_expiry", "Vencimiento de contrato"),
    ("maintenance_due", "Mantenimiento pendiente"),
    ("rent_increase", "Aumento de alquiler"),
    ("inspection_scheduled", "Inspección programada"),
    ("document_pending", "Documento pendiente"),
    ("welcome_tenant", "Bienvenida inquilino"),
    ("lease_renewal", "Renovación de contrato"),
    ("system_alert", "Alerta del sistema"),
    ("custom", "Personalizada"),
]

FREQUENCY_CHOICES = [
    (1, "Diario"),
    (3, "Cada 3 días"),
    (7, "Semanal"),
    (14, "Quincenal"),
    (30, "Mensual"),
    (60, "Cada 2 meses"),
    (90, "Trimestral"),
    (180, "Semestral"),
    (365, "Anual"),
]


class NotificationForm(forms.ModelForm):
    """
    Formulario para configuración de notificaciones y comunicaciones.

    Incluye formularios específicos por tipo de notificación, editor de plantillas
    de email y configuración de frecuencias y habilitación/deshabilitación.
    """

    # Campos adicionales para configuración avanzada
    send_to_tenant = forms.BooleanField(
        label="Enviar al inquilino",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        help_text="Enviar esta notificación directamente al inquilino",
    )

    send_to_owner = forms.BooleanField(
        label="Enviar al propietario",
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        help_text="Enviar esta notificación al propietario de la propiedad",
    )

    send_to_admin = forms.BooleanField(
        label="Enviar al administrador",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        help_text="Enviar copia de la notificación al administrador",
    )

    email_subject = forms.CharField(
        label="Asunto del email",
        max_length=200,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Asunto del email (puede usar variables)",
            }
        ),
        help_text="Asunto que aparecerá en el email. Puede usar variables como {{customer.name}}",
    )

    sms_enabled = forms.BooleanField(
        label="Enviar también por SMS",
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        help_text="Enviar una versión corta por SMS además del email",
    )

    sms_template = forms.CharField(
        label="Plantilla SMS",
        max_length=160,
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "maxlength": "160",
                "placeholder": "Mensaje SMS (máximo 160 caracteres)",
            }
        ),
        help_text="Mensaje corto para SMS. Máximo 160 caracteres.",
    )

    days_before_event = forms.IntegerField(
        label="Días antes del evento",
        min_value=0,
        max_value=365,
        initial=7,
        required=False,
        widget=forms.NumberInput(
            attrs={"class": "form-control", "min": "0", "max": "365"}
        ),
        help_text="Cuántos días antes del evento enviar la notificación",
    )

    class Meta:
        model = NotificationSettings
        fields = ["notification_type", "is_enabled", "email_template", "frequency_days"]
        widgets = {
            "notification_type": forms.Select(attrs={"class": "form-control"}),
            "is_enabled": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "email_template": forms.Textarea(
                attrs={
                    "class": "form-control email-template-editor",
                    "rows": 12,
                    "placeholder": "Plantilla del email (HTML + variables Django)",
                    "data-editor": "html",
                }
            ),
            "frequency_days": forms.Select(attrs={"class": "form-control"}),
        }
        labels = {
            "notification_type": "Tipo de notificación *",
            "is_enabled": "Notificación activa",
            "email_template": "Plantilla del email",
            "frequency_days": "Frecuencia de envío",
        }
        help_texts = {
            "notification_type": "Tipo de evento que activará esta notificación",
            "is_enabled": "Desmarcar para desactivar temporalmente esta notificación",
            "email_template": "Contenido HTML del email. Puede usar variables como {{customer.name}}, {{property.address}}, etc.",
            "frequency_days": "Con qué frecuencia se puede enviar esta notificación",
        }

    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop("company", None)
        super().__init__(*args, **kwargs)

        # Configurar opciones de los campos Select
        self.fields["notification_type"].choices = NOTIFICATION_TYPE_CHOICES
        self.fields["frequency_days"].choices = FREQUENCY_CHOICES

        # Cargar configuraciones adicionales si existe la instancia
        if self.instance and self.instance.pk:
            self._load_additional_configs()

        # Agregar información de variables disponibles
        self._add_variable_help()

    def _load_additional_configs(self):
        """Carga configuraciones adicionales desde CompanyConfiguration"""
        if not self.company:
            return

        try:
            # Buscar configuraciones relacionadas con esta notificación
            config_prefix = f"notification_{self.instance.notification_type}_"
            configs = {
                config.config_key.replace(config_prefix, ""): config.config_value
                for config in self.company.configurations.filter(
                    config_key__startswith=config_prefix
                )
            }

            # Mapear configuraciones a campos del formulario
            field_mapping = {
                "send_to_tenant": "send_to_tenant",
                "send_to_owner": "send_to_owner",
                "send_to_admin": "send_to_admin",
                "email_subject": "email_subject",
                "sms_enabled": "sms_enabled",
                "sms_template": "sms_template",
                "days_before_event": "days_before_event",
            }

            for config_key, field_name in field_mapping.items():
                if config_key in configs and field_name in self.fields:
                    value = configs[config_key]

                    # Convertir valores según el tipo de campo
                    if field_name in [
                        "send_to_tenant",
                        "send_to_owner",
                        "send_to_admin",
                        "sms_enabled",
                    ]:
                        value = value.lower() in ["true", "1", "yes"]
                    elif field_name == "days_before_event":
                        value = int(value) if value.isdigit() else 7

                    self.fields[field_name].initial = value

        except Exception:
            pass  # Si hay error cargando configuraciones, usar valores por defecto

    def _add_variable_help(self):
        """Agrega información sobre variables disponibles para notificaciones"""
        notification_variables = [
            "{{customer.name}}",
            "{{customer.email}}",
            "{{customer.phone}}",
            "{{property.address}}",
            "{{property.type}}",
            "{{contract.start_date}}",
            "{{contract.end_date}}",
            "{{contract.monthly_rent}}",
            "{{agent.name}}",
            "{{company.name}}",
            "{{company.phone}}",
            "{{company.email}}",
            "{{current_date}}",
            "{{due_date}}",
            "{{amount_due}}",
        ]

        vars_text = ", ".join(notification_variables[:8]) + "..."
        help_text = f" Variables disponibles: {vars_text}"

        self.fields["email_template"].help_text += help_text
        if "email_subject" in self.fields:
            self.fields["email_subject"].help_text += help_text

    def clean_notification_type(self):
        """Validación para el tipo de notificación"""
        notification_type = self.cleaned_data.get("notification_type")

        if notification_type and self.company:
            # Verificar unicidad dentro de la empresa
            existing = NotificationSettings.objects.filter(
                company=self.company, notification_type=notification_type
            )

            # Excluir la instancia actual si estamos editando
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)

            if existing.exists():
                raise ValidationError(
                    f"Ya existe una configuración para el tipo de notificación {notification_type}"
                )

        return notification_type

    def clean_email_template(self):
        """Validación para la plantilla de email"""
        template = self.cleaned_data.get("email_template")
        if template and self.company:
            from .services.document_template_service import DocumentTemplateService

            service = DocumentTemplateService(self.company)
            is_valid, error_msg = service.validate_template_syntax(template)

            if not is_valid:
                raise ValidationError(f"Error de sintaxis en plantilla: {error_msg}")

        return template

    def clean_email_subject(self):
        """Validación para el asunto del email"""
        subject = self.cleaned_data.get("email_subject")
        if subject and self.company:
            from .services.document_template_service import DocumentTemplateService

            service = DocumentTemplateService(self.company)
            is_valid, error_msg = service.validate_template_syntax(subject)

            if not is_valid:
                raise ValidationError(f"Error de sintaxis en asunto: {error_msg}")

        return subject

    def clean_sms_template(self):
        """Validación para la plantilla SMS"""
        sms_template = self.cleaned_data.get("sms_template")
        if sms_template:
            # Verificar longitud
            if len(sms_template) > 160:
                raise ValidationError("El mensaje SMS no puede exceder 160 caracteres")

            # Validar sintaxis de variables si las hay
            if "{{" in sms_template and self.company:
                from .services.document_template_service import DocumentTemplateService

                service = DocumentTemplateService(self.company)
                is_valid, error_msg = service.validate_template_syntax(sms_template)

                if not is_valid:
                    raise ValidationError(f"Error de sintaxis en SMS: {error_msg}")

        return sms_template

    def clean(self):
        """Validación general del formulario"""
        cleaned_data = super().clean()

        # Si SMS está habilitado, debe tener plantilla
        sms_enabled = cleaned_data.get("sms_enabled", False)
        sms_template = cleaned_data.get("sms_template", "").strip()

        if sms_enabled and not sms_template:
            raise ValidationError(
                "Debe proporcionar una plantilla SMS si está habilitado"
            )

        # Verificar que al menos un destinatario esté seleccionado
        recipients = [
            cleaned_data.get("send_to_tenant", False),
            cleaned_data.get("send_to_owner", False),
            cleaned_data.get("send_to_admin", False),
        ]

        if not any(recipients):
            raise ValidationError(
                "Debe seleccionar al menos un destinatario para la notificación"
            )

        return cleaned_data

    def save(self, commit=True):
        """Guarda la configuración de notificación y configuraciones adicionales"""
        instance = super().save(commit=False)

        # Asignar empresa si no está asignada
        if self.company and not instance.company:
            instance.company = self.company

        if commit:
            instance.save()

            # Guardar configuraciones adicionales
            if self.company:
                self._save_additional_configs()

        return instance

    def _save_additional_configs(self):
        """Guarda configuraciones adicionales en CompanyConfiguration"""
        from .models import CompanyConfiguration

        config_prefix = f"notification_{self.instance.notification_type}_"

        additional_configs = {
            "send_to_tenant": str(
                self.cleaned_data.get("send_to_tenant", True)
            ).lower(),
            "send_to_owner": str(self.cleaned_data.get("send_to_owner", False)).lower(),
            "send_to_admin": str(self.cleaned_data.get("send_to_admin", True)).lower(),
            "email_subject": self.cleaned_data.get("email_subject", ""),
            "sms_enabled": str(self.cleaned_data.get("sms_enabled", False)).lower(),
            "sms_template": self.cleaned_data.get("sms_template", ""),
            "days_before_event": str(self.cleaned_data.get("days_before_event", 7)),
        }

        for config_key, config_value in additional_configs.items():
            if config_value:  # Solo guardar si hay valor
                full_key = config_prefix + config_key
                config_type = (
                    "boolean"
                    if config_key
                    in [
                        "send_to_tenant",
                        "send_to_owner",
                        "send_to_admin",
                        "sms_enabled",
                    ]
                    else "string"
                )
                if config_key == "days_before_event":
                    config_type = "integer"

                CompanyConfiguration.objects.update_or_create(
                    company=self.company,
                    config_key=full_key,
                    defaults={"config_value": config_value, "config_type": config_type},
                )
