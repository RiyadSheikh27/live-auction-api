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