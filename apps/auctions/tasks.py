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
    try:
        auction = Auction.objects.get(id=auction_id)

        # Check if auction is still active
        if auction.status != 'active':
            logger.warning(f"Auction {auction_id} is already closed.")
            return f"Auction {auction_id} is already closed."
        
        # Get highest bid
        highest_bid = auction.bids.order_by('-amount').first()

        # Determine winner
        if highest_bid:
            # Check if reserve price is met (if set)
            if auction.reserve_price:
                if highest_bid.amount >= auction.reserve_price:
                    auction.winner = highest_bid.bidder
                    auction.status = 'closed'
                    logger.info(
                        f"Auction {auction_id} closed. Winner: {highest_bid.bidder.username}"
                    )
                else:
                    # Reserve price not met
                    auction.status = 'closed'
                    logger.info(
                        f"Auction {auction_id} closed. Reserve price not met."
                    )
            else:
                # No reserve price, highest bidder wins
                auction.winner = highest_bid.bidder
                auction.status = 'closed'
                logger.info(
                    f"Auction {auction_id} closed. Winner: {highest_bid.bidder.username}"
                )
        else:
            # No bids placed, just close the auction
            auction.status = 'closed'
            logger.info(f"Auction {auction_id} closed with no bids.")

        auction.save()

        notify_auction_participants.delay(auction_id)

        return f"Auction {auction_id} closed successfully."
    
    except Auction.DoesNotExist:
        logger.error(f"Auction with ID {auction_id} does not exist.")
        return f"Auction with ID {auction_id} does not exist."
    except Exception as e:
        logger.error(f"Error closing auction {auction_id}: {str(e)}")
        raise

@shared_task
def notify_auction_participants(auction_id):
    """
    Send notifications to auction participants
    
    In a real app, this would send emails or push notifications
    For this demo, we'll just log the notifications
    
    Args:
        auction_id: ID of the auction
    """
    from .models import Auction
    
    try:
        auction = Auction.objects.get(id=auction_id)
        
        # Get all unique bidders
        bidders = auction.bids.values_list('bidder__email', flat=True).distinct()
        
        if auction.winner:
            # Notify winner
            logger.info(
                f"📧 NOTIFICATION: {auction.winner.email} - "
                f"Congratulations! You won '{auction.title}' for ${auction.current_price}"
            )
            
            # Notify other bidders
            for bidder_email in bidders:
                if bidder_email != auction.winner.email:
                    logger.info(
                        f"📧 NOTIFICATION: {bidder_email} - "
                        f"Auction '{auction.title}' has ended. You were outbid."
                    )
        else:
            # No winner
            logger.info(
                f"📧 NOTIFICATION: {auction.owner.email} - "
                f"Your auction '{auction.title}' ended with no winner."
            )
        
        # Notify owner
        if auction.winner and auction.owner.email != auction.winner.email:
            logger.info(
                f"📧 NOTIFICATION: {auction.owner.email} - "
                f"Your auction '{auction.title}' sold for ${auction.current_price}"
            )
        
        return f"Notifications sent for auction {auction_id}"
        
    except Auction.DoesNotExist:
        logger.error(f"Auction {auction_id} not found")
        return f"Auction {auction_id} not found"
    except Exception as e:
        logger.error(f"Error notifying participants for auction {auction_id}: {str(e)}")
        raise
