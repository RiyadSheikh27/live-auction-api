"""
Django Signals
==============
Automatically trigger actions when certain events occur

SIGNALS IN THIS FILE:
- When a bid is placed, update auction's current_price
- When auction ends, trigger closing task
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Bid, Auction
from .tasks import close_auction
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Bid)
def update_auction_price(sender, instance, created, **kwargs):
    """
    Signal: When a new bid is created, update auction's current price
    
    WHY USE SIGNAL:
    - Automatically happens whenever a bid is placed
    - Keeps Bid model focused on its own data
    - No need to remember to update price manually
    
    Args:
        sender: The model class (Bid)
        instance: The actual bid instance that was saved
        created: True if this is a new bid, False if updated
    """
    if created:  # Only for new bids, not updates
        auction = instance.auction
        
        # Update current price to the bid amount
        if instance.amount > auction.current_price:
            auction.current_price = instance.amount
            auction.save(update_fields=['current_price', 'updated_at'])
            
            logger.info(
                f"Auction {auction.id} price updated to ${instance.amount} "
                f"by {instance.bidder.username}"
            )


# Note: We could add a signal to automatically close auction when end_time is reached,
# but we're using Celery Beat for that instead (more reliable for time-based tasks)
