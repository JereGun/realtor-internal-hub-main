# Docker Setup para Real Estate Management System

Este proyecto incluye una configuración completa de Docker para facilitar el despliegue y desarrollo.

## Estructura de Docker

- **Dockerfile**: Imagen principal de la aplicación Django
- **docker-compose.yml**: Orquestación de todos los servicios
- **.dockerignore**: Archivos excluidos del build
- **.env.docker**: Variables de entorno para Docker
- **docker-entrypoint.sh**: Script de inicialización

## Servicios Incluidos

1. **web**: Aplicación Django principal (puerto 8000)
2. **db**: PostgreSQL 15 (puerto 5432)
3. **redis**: Redis para Celery (puerto 6379)
4. **celery**: Worker de Celery para tareas asíncronas
5. **celery-beat**: Scheduler para tareas programadas

## Instrucciones de Uso

### 1. Construcción y Inicio

```bash
# Construir y levantar todos los servicios
docker-compose up --build

# Ejecutar en segundo plano
docker-compose up -d --build
```

### 2. Comandos Útiles

```bash
# Ver logs de todos los servicios
docker-compose logs -f

# Ver logs de un servicio específico
docker-compose logs -f web

# Ejecutar comandos Django
docker-compose exec web python manage.py createsuperuser
docker-compose exec web python manage.py shell

# Acceder al contenedor
docker-compose exec web bash

# Parar todos los servicios
docker-compose down

# Parar y eliminar volúmenes
docker-compose down -v
```

### 3. Acceso a la Aplicación

- **Aplicación Web**: http://localhost:8000
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

### 4. Configuración de Producción

Para producción, modifica las siguientes variables en `.env.docker`:

```env
DEBUG=False
SECRET_KEY=tu-clave-secreta-muy-segura
ALLOWED_HOSTS=tu-dominio.com,www.tu-dominio.com
SENTRY_DSN=tu-sentry-dsn-si-lo-usas
```

### 5. Migraciones y Datos Iniciales

```bash
# Ejecutar migraciones
docker-compose exec web python manage.py migrate

# Crear superusuario
docker-compose exec web python manage.py createsuperuser

# Cargar datos de prueba (si tienes fixtures)
docker-compose exec web python manage.py loaddata fixtures/initial_data.json
```

### 6. Backup de Base de Datos

```bash
# Crear backup
docker-compose exec db pg_dump -U inmobiliaria real_estate_db > backup.sql

# Restaurar backup
docker-compose exec -T db psql -U inmobiliaria real_estate_db < backup.sql
```

### 7. Monitoreo de Celery

```bash
# Ver estado de workers
docker-compose exec celery celery -A real_estate_management inspect active

# Ver tareas programadas
docker-compose exec celery-beat celery -A real_estate_management inspect scheduled
```

## Troubleshooting

### Problema: Base de datos no se conecta
```bash
# Verificar que el servicio db esté corriendo
docker-compose ps

# Ver logs de la base de datos
docker-compose logs db
```

### Problema: Celery no procesa tareas
```bash
# Verificar workers
docker-compose logs celery

# Reiniciar worker
docker-compose restart celery
```

### Problema: Archivos estáticos no se cargan
```bash
# Recolectar archivos estáticos
docker-compose exec web python manage.py collectstatic --noinput
```

## Desarrollo Local

Para desarrollo, puedes usar el archivo `.env` original y ejecutar:

```bash
# Solo base de datos y Redis
docker-compose up db redis

# Luego ejecutar Django localmente
python manage.py runserver
```

## Notas Importantes

1. Los volúmenes `media` y `logs` se montan para persistir datos
2. La base de datos usa un volumen nombrado `postgres_data`
3. El superusuario por defecto es `admin/admin123` (cámbialo en producción)
4. Asegúrate de cambiar las credenciales de base de datos en producción
5. El script `docker-entrypoint.sh` maneja la inicialización automática