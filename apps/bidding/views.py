from django.shortcuts import render

# Create your views here.
"""
Bidding Views
=============
REST API endpoints for bidding operations using APIView

NOTE: Primary bidding happens via WebSocket (consumers.py)
These views provide REST endpoints for bid history and statistics
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Count, Max, Avg
from decimal import Decimal

from apps.auctions.models import Auction, Bid
from apps.auctions.serializers import BidSerializer


class PlaceBidAPIView(APIView):
    """
    POST /api/bidding/place-bid/ - Place a bid via REST (alternative to WebSocket)
    
    This is a REST alternative to WebSocket bidding.
    WebSocket is preferred for real-time updates, but this can be used
    for clients that don't support WebSocket.
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """
        Place a bid on an auction
        
        Required fields:
        - auction_id: ID of the auction
        - amount: Bid amount (must be higher than current price)
        """
        auction_id = request.data.get('auction_id')
        amount = request.data.get('amount')
        
        if not auction_id or not amount:
            return Response(
                {'error': 'auction_id and amount are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            amount = Decimal(str(amount))
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid amount format'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get auction
        auction = get_object_or_404(Auction, pk=auction_id)
        
        # Validate auction is active
        if not auction.is_active:
            return Response(
                {'error': 'Auction is not active'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate bid amount
        if amount <= auction.current_price:
            return Response(
                {'error': f'Bid must be higher than current price (${auction.current_price})'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate user is not the owner
        if auction.owner == request.user:
            return Response(
                {'error': 'You cannot bid on your own auction'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create bid
        bid = Bid.objects.create(
            auction=auction,
            bidder=request.user,
            amount=amount
        )
        
        serializer = BidSerializer(bid)
        return Response(
            {
                'message': 'Bid placed successfully',
                'bid': serializer.data,
                'auction': {
                    'id': auction.id,
                    'current_price': str(auction.current_price),
                }
            },
            status=status.HTTP_201_CREATED
        )


class BidHistoryAPIView(APIView):
    """
    GET /api/bidding/history/ - Get user's bid history
    """
    
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PageNumberPagination
    
    def get(self, request):
        """
        Get all bids placed by the authenticated user
        with auction details
        """
        bids = Bid.objects.filter(
            bidder=request.user
        ).select_related('auction', 'auction__owner').order_by('-created_at')
        
        # Pagination
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(bids, request)
        
        if page is not None:
            serializer = BidSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = BidSerializer(bids, many=True)
        return Response(serializer.data)


class BidStatisticsAPIView(APIView):
    """
    GET /api/bidding/statistics/ - Get bidding statistics for current user
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """
        Get statistics about user's bidding activity
        """
        user_bids = Bid.objects.filter(bidder=request.user)
        
        # Calculate statistics
        stats = user_bids.aggregate(
            total_bids=Count('id'),
            highest_bid=Max('amount'),
            average_bid=Avg('amount'),
        )
        
        # Count auctions won
        auctions_won = Auction.objects.filter(
            winner=request.user,
            status='closed'
        ).count()
        
        # Get unique auctions user has bid on
        unique_auctions = user_bids.values('auction').distinct().count()
        
        return Response({
            'total_bids': stats['total_bids'] or 0,
            'highest_bid': str(stats['highest_bid']) if stats['highest_bid'] else '0.00',
            'average_bid': str(round(stats['average_bid'], 2)) if stats['average_bid'] else '0.00',
            'auctions_won': auctions_won,
            'unique_auctions_bid_on': unique_auctions,
        })


class AuctionBidAnalyticsAPIView(APIView):
    """
    GET /api/bidding/auction/{id}/analytics/ - Get bid analytics for specific auction
    """
    
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get(self, request, pk):
        """
        Get bid analytics for a specific auction
        Shows bid distribution, average bid, etc.
        """
        auction = get_object_or_404(Auction, pk=pk)
        
        bids = auction.bids.all()
        
        # Calculate analytics
        analytics = bids.aggregate(
            total_bids=Count('id'),
            highest_bid=Max('amount'),
            lowest_bid=Max('amount'),  # First bid is typically lowest
            average_bid=Avg('amount'),
        )
        
        # Count unique bidders
        unique_bidders = bids.values('bidder').distinct().count()
        
        # Get bid progression (last 5 bids)
        recent_bids = bids.order_by('-created_at')[:5]
        recent_bids_data = BidSerializer(recent_bids, many=True).data
        
        return Response({
            'auction_id': auction.id,
            'auction_title': auction.title,
            'current_price': str(auction.current_price),
            'starting_price': str(auction.starting_price),
            'analytics': {
                'total_bids': analytics['total_bids'] or 0,
                'unique_bidders': unique_bidders,
                'highest_bid': str(analytics['highest_bid']) if analytics['highest_bid'] else str(auction.starting_price),
                'average_bid': str(round(analytics['average_bid'], 2)) if analytics['average_bid'] else '0.00',
            },
            'recent_bids': recent_bids_data,
        })
