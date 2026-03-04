"""
Celery Configuration
====================
Celery is a distributed task queue system that allows you to run tasks asynchronously.

WHY WE USE IT:
- Auto-close auctions when time expires (scheduled tasks)
- Send notifications without blocking HTTP requests
- Process heavy operations in background

KEY CONCEPTS:
- Task: A function decorated with @shared_task or @celery_app.task
- Worker: Process that executes tasks
- Beat: Scheduler that triggers periodic tasks
- Broker: Message queue (we use Redis)
"""

import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

# Create Celery app
app = Celery('auction_project')

# Load configuration from Django settings with CELERY_ prefix
# Example: CELERY_BROKER_URL in settings.py becomes broker_url in Celery
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
# Looks for tasks.py in each app directory
app.autodiscover_tasks()


# Periodic tasks configuration (Celery Beat)
app.conf.beat_schedule = {
    # Check every minute for expired auctions
    'check-expired-auctions': {
        'task': 'apps.auctions.tasks.check_and_close_expired_auctions',
        'schedule': 60.0,  # Run every 60 seconds
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to test if Celery is working"""
    print(f'Request: {self.request!r}')
