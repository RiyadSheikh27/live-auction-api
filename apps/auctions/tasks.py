"""
Celery Tasks
============
Background tasks for auction management

CELERY TASKS:
- Run asynchronously in the background
- Don't block HTTP requests
- Can be scheduled or triggered manually
- Use @shared_task decorator for reusability

TASKS IN THIS FILE:
1. check_and_close_expired_auctions - Periodic task (runs every minute)
2. close_auction - Called when auction ends
3. notify_auction_participants - Send notifications
"""

from celery import shared_task
from django.utils import timezone
from django.db.models import Max
from .models import Auction

import logging

logger = logging.getLogger(__name__)

@shared_task
def check_and_close_expired_auctions():
    """
    Periodic task to check and close expired auctions
    
    This task runs every minute (configured in celery.py)
    It finds all active auctions that have passed their end_time
    and closes them
    
    WHY WE USE THIS:
    - Auctions need to close automatically at end_time
    - Can't rely on users or manual actions
    - Celery Beat scheduler ensures it runs reliably
    """
    expired_auctions = Auction.objects.filter(status='active', end_time__lte=timezone.now())
    count = 0

    for auction in expired_auctions:
        close_auction.delay(auction.id)
        count += 1

    logger.info(f"Fouond and queued {count} expired auctions for closing.")
    return f"Queued {count} expired auctions for closing."

@shared_task
def close_auction(auction_id):
    """
    Close a specific auction and determine winner
    
    WHY SEPARATE TASK:
    - Keeps each task focused and small
    - Can be called independently
    - Better error handling
    
    Args:
        auction_id: ID of the auction to close
    """
    pass