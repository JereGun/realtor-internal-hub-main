# Celery Beat Configuration for Notification System

This document explains the Celery Beat configuration for automated notification tasks in the real estate management system.

## Overview

The notification system uses Celery Beat to schedule periodic tasks that check for various business events and create notifications for agents. The system is configured to run daily checks for:

- Contract expirations (8:00 AM)
- Overdue invoices (9:00 AM) 
- Rent increases (10:00 AM)
- Invoices due soon (11:00 AM)
- Notification batch processing (6:00 PM)

## Configuration

### Celery Beat Schedule

The periodic tasks are configured in `settings.py` under `CELERY_BEAT_SCHEDULE`:

```python
CELERY_BEAT_SCHEDULE = {
    'check-contract-expirations': {
        'task': 'user_notifications.tasks.check_contract_expirations',
        'schedule': crontab(hour=8, minute=0),
        'options': {
            'expires': 3600,  # Task expires after 1 hour
            'retry': True,
            'retry_policy': {
                'max_retries': 3,
                'interval_start': 0,
                'interval_step': 0.2,
                'interval_max': 0.2,
            }
        }
    },
    # ... other tasks
}
```

### Task Configuration

Each task is configured with:
- **Schedule**: Using crontab for daily execution at specific times
- **Expiration**: Tasks expire after 1 hour if not executed
- **Retry Policy**: Up to 3 retries with exponential backoff
- **Queue**: All notification tasks use the 'notifications' queue

### Error Handling

The system includes comprehensive error handling:
- Database errors trigger automatic retries
- Task failures are logged with full context
- Circuit breaker pattern for repeated failures
- Monitoring signals for task success/failure/retry

## Installation

1. Install required packages:
```bash
pip install django-celery-beat==2.5.0
```

2. Add to `INSTALLED_APPS`:
```python
INSTALLED_APPS = [
    # ... other apps
    'django_celery_beat',
]
```

3. Run migrations:
```bash
python manage.py migrate django_celery_beat
```

## Running Celery Services

### Option 1: Using the Helper Script

```bash
python start_celery.py
```

This script starts both the worker and beat scheduler with appropriate configuration.

### Option 2: Manual Commands

Start Celery worker:
```bash
celery -A real_estate_management worker --loglevel=info --concurrency=2 --queues=notifications,celery
```

Start Celery beat scheduler:
```bash
celery -A real_estate_management beat --loglevel=info --scheduler=django_celery_beat.schedulers:DatabaseScheduler
```

### Option 3: Production with Supervisor

For production, use supervisor or systemd to manage the processes:

```ini
# /etc/supervisor/conf.d/celery-worker.conf
[program:celery-worker]
command=/path/to/venv/bin/celery -A real_estate_management worker --loglevel=info
directory=/path/to/project
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/celery/worker.log

# /etc/supervisor/conf.d/celery-beat.conf
[program:celery-beat]
command=/path/to/venv/bin/celery -A real_estate_management beat --loglevel=info --scheduler=django_celery_beat.schedulers:DatabaseScheduler
directory=/path/to/project
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/celery/beat.log
```

## Monitoring

### Check Configuration Status

```bash
python manage.py celery_beat_status
```

This command shows:
- Configured scheduled tasks
- Celery app configuration
- Task module import status
- Next steps for starting services

### Monitor Task Execution

1. **Flower** (Web-based monitoring):
```bash
celery -A real_estate_management flower
```
Access at http://localhost:5555

2. **Logs**: Check application logs for task execution:
```bash
tail -f logs/app.log | grep celery
```

3. **Django Admin**: View scheduled tasks in Django admin under "Periodic Tasks"

## Task Schedules

| Task | Schedule | Purpose |
|------|----------|---------|
| Contract Expirations | Daily 8:00 AM | Check for contracts expiring in 30/7 days or expired |
| Invoice Overdue | Daily 9:00 AM | Check for overdue invoices with escalating urgency |
| Rent Increases | Daily 10:00 AM | Check for rent increases due within 7 days or overdue |
| Invoice Due Soon | Daily 11:00 AM | Check for invoices due within 7/3 days |
| Notification Batches | Daily 6:00 PM | Process batched notifications for users |

## Troubleshooting

### Common Issues

1. **Tasks not executing**:
   - Check if Celery beat is running
   - Verify Redis/broker connection
   - Check task registration with `celery -A real_estate_management inspect registered`

2. **Database connection errors**:
   - Ensure database is accessible from Celery processes
   - Check connection pool settings
   - Verify database migrations are applied

3. **Import errors**:
   - Ensure all notification task modules are importable
   - Check Python path and virtual environment
   - Verify Django settings module is correct

### Debugging Commands

```bash
# List registered tasks
celery -A real_estate_management inspect registered

# Check active tasks
celery -A real_estate_management inspect active

# Check scheduled tasks
celery -A real_estate_management inspect scheduled

# Purge all tasks
celery -A real_estate_management purge

# Test task execution
python manage.py shell
>>> from user_notifications.tasks import check_contract_expirations
>>> result = check_contract_expirations.delay()
>>> result.get()
```

## Security Considerations

1. **Queue Isolation**: Notification tasks use dedicated queue
2. **Rate Limiting**: Tasks limited to 10 per minute
3. **Time Limits**: Hard and soft time limits configured
4. **Result Expiration**: Task results expire after 1 hour
5. **Worker Limits**: Max 1000 tasks per worker child process

## Performance Tuning

- **Concurrency**: Adjust worker concurrency based on server resources
- **Prefetch**: Set to 1 for fair task distribution
- **Memory Management**: Workers restart after 1000 tasks
- **Queue Routing**: Separate queues for different task types
- **Rate Limiting**: Prevents system overload

## Maintenance

1. **Regular Monitoring**: Check task execution logs daily
2. **Database Cleanup**: Periodic cleanup of old task results
3. **Performance Review**: Monitor task execution times
4. **Error Analysis**: Review failed tasks and adjust retry policies
5. **Schedule Updates**: Adjust task schedules based on business needs