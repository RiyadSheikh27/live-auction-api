"""
Bidding URLs
============
REST API endpoints for bidding operations

NOTE: WebSocket bidding URLs are in routing.py
"""

from django.urls import path
from . import views

app_name = 'bidding'

urlpatterns = [
    # Place bid via REST API (alternative to WebSocket)
    path(
        'place-bid/',
        views.PlaceBidAPIView.as_view(),
        name='place-bid'
    ),
    
    # User's bid history
    path(
        'history/',
        views.BidHistoryAPIView.as_view(),
        name='bid-history'
    ),
    
    # User's bidding statistics
    path(
        'statistics/',
        views.BidStatisticsAPIView.as_view(),
        name='bid-statistics'
    ),
    
    # Analytics for specific auction
    path(
        'auction/<int:pk>/analytics/',
        views.AuctionBidAnalyticsAPIView.as_view(),
        name='auction-analytics'
    ),
]
