
# Sistema de Gestión Inmobiliaria

Un sistema completo de gestión interna para inmobiliarias desarrollado con Django y PostgreSQL. Este sistema permite gestionar propiedades, clientes, agentes, contratos, pagos y tareas de manera eficiente y profesional.

## Características Principales

### 🏠 Gestión de Propiedades
- Registro completo de propiedades con información detallada
- Múltiples imágenes por propiedad con imagen de portada
- Categorización por tipo y estado
- Sistema de características y etiquetas
- Búsqueda y filtrado avanzado

### 👥 Gestión de Agentes
- Sistema de autenticación personalizado
- Perfiles de agentes con foto
- Control de comisiones
- Dashboard personalizado

### 👤 Gestión de Clientes
- Base de datos completa de clientes
- Información de contacto y dirección
- Historial de contratos

### 📋 Gestión de Contratos
- Contratos de venta y alquiler
- Sistema de aumentos para alquileres
- Cálculo automático de comisiones
- Estados y fechas de vencimiento

### 💰 Gestión de Pagos
- Registro de pagos de contratos
- Múltiples métodos de pago
- Estados de pago y vencimientos
- Reportes de pagos pendientes

### 🔔 Sistema de Notificaciones
- Tareas y recordatorios
- Prioridades y estados
- Vinculación con propiedades, clientes y contratos

## Requisitos del Sistema

- Python 3.8+
- PostgreSQL 12+
- pip (gestor de paquetes de Python)

## Instalación

### 1. Clonar el repositorio
```bash
git clone <tu-repositorio>
cd real_estate_management
```

### 2. Crear y activar un entorno virtual
```bash
python -m venv venv

# En Linux/Mac:
source venv/bin/activate

# En Windows:
venv\Scripts\activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar PostgreSQL
Crear una base de datos PostgreSQL:
```sql
CREATE DATABASE real_estate_db;
CREATE USER postgres WITH ENCRYPTED PASSWORD 'tu_password';
GRANT ALL PRIVILEGES ON DATABASE real_estate_db TO postgres;
```

### 5. Configurar variables de entorno
Copiar el archivo de ejemplo y configurar:
```bash
cp .env.example .env
```

Editar `.env` con tus configuraciones:
```env
DB_NAME=real_estate_db
DB_USER=postgres
DB_PASSWORD=tu_password
DB_HOST=localhost
DB_PORT=5432
SECRET_KEY=tu-clave-secreta-aqui
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

### 6. Ejecutar migraciones
```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Crear superusuario
```bash
python manage.py createsuperuser
```

### 8. Cargar datos iniciales (opcional)
```bash
python manage.py loaddata initial_data.json
```

### 9. Generar datos de prueba (opcional)
Para poblar la base de datos con datos de prueba generados con Faker, ejecuta:
```bash
./load_test_data.sh
```

### 9. Ejecutar el servidor
```bash
python manage.py runserver
```

El sistema estará disponible en: `http://localhost:8000`

## Estructura del Proyecto

```
real_estate_management/
│
├── real_estate_management/     # Configuración principal
├── agents/                     # App de agentes
├── properties/                 # App de propiedades
├── customers/                  # App de clientes
├── contracts/                  # App de contratos
├── payments/                   # App de pagos
├── notifications/              # App de notificaciones
├── core/                       # App central (modelos base)
├── templates/                  # Templates HTML
├── static/                     # Archivos estáticos
├── media/                      # Archivos subidos
└── requirements.txt           # Dependencias
```

## Uso del Sistema

### Acceso al Sistema
1. Dirigirse a `http://localhost:8000`
2. Iniciar sesión con las credenciales de agente
3. Navegar por el dashboard principal

### Panel de Administración
Acceder a `http://localhost:8000/admin/` con credenciales de superusuario para:
- Gestionar usuarios y permisos
- Configurar tipos de propiedades
- Administrar métodos de pago
- Supervisar todas las entidades

### Gestión de Archivos Media
Las imágenes se almacenan en:
- `media/agents/` - Fotos de perfil de agentes
- `media/properties/` - Imágenes de propiedades

Para producción, configurar un servicio de archivos estáticos como AWS S3.

## Configuración de Producción

### Variables de Entorno para Producción
```env
DEBUG=False
ALLOWED_HOSTS=tu-dominio.com,www.tu-dominio.com
SECRET_KEY=clave-secreta-muy-segura
```

### Archivos Estáticos
```bash
python manage.py collectstatic
```

### Base de Datos
Configurar una base de datos PostgreSQL en producción y actualizar las variables de entorno correspondientes.

## Funcionalidades Destacadas

### Dashboard Intuitivo
- Navegación lateral con menú desplegable
- Contadores de estadísticas en tiempo real
- Acceso rápido a funciones principales

### Búsqueda Avanzada
- Filtros múltiples por tipo, estado, localidad
- Búsqueda de texto en múltiples campos
- Resultados paginados

### Gestión de Imágenes
- Subida múltiple de imágenes para propiedades
- Selección de imagen de portada
- Redimensionamiento automático

### Sistema de Permisos
- Autenticación basada en agentes
- Control de acceso por funcionalidad
- Perfiles de usuario personalizados

## Desarrollo y Personalización

### Agregar Nuevas Funcionalidades
1. Crear nueva app: `python manage.py startapp nueva_app`
2. Agregar a `INSTALLED_APPS` en settings.py
3. Crear modelos, vistas y templates
4. Configurar URLs

### Personalizar Templates
Los templates están organizados por app en `templates/`. Usar Bootstrap 5 para mantener consistencia visual.

### Extender Modelos
Todos los modelos heredan de `BaseModel` que incluye campos de auditoría (`created_at`, `updated_at`).

## Comandos Útiles

```bash
# Crear migraciones
python manage.py makemigrations

# Aplicar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Ejecutar servidor de desarrollo
python manage.py runserver

# Recopilar archivos estáticos
python manage.py collectstatic

# Ejecutar shell de Django
python manage.py shell

# Ejecutar tests
python manage.py test
```

## Soporte

Para soporte técnico o reportar problemas:
1. Revisar la documentación
2. Verificar logs del servidor
3. Consultar la comunidad Django
4. Crear issue en el repositorio

## Licencia

Este proyecto está bajo la Licencia MIT. Ver archivo `LICENSE` para más detalles.

---

**Sistema de Gestión Inmobiliaria** - Desarrollado con Django 4.2 y PostgreSQL
