from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from django.db.models import Q
from django.shortcuts import get_object_or_404
from .models import Auction, Bid
from .serializers import (
    AuctionListSerializer,
    AuctionDetailSerializer,
    AuctionCreateSerializer,
    BidSerializer,
)
from apps.utils.permissions import IsOwnerOrReadOnly
from apps.utils.views import APIResponse

class AuctionListCreateAPIView(APIView):
    """
    GET /api/auctions/ - List all auctions
    POST /api/auctions/ - Create new auction
    
    Supports filtering via query parameters:
    - ?status=active
    - ?active=true
    - ?search=camera
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = PageNumberPagination

    def get(self, request):
        """List all auction with filtering

        Query Parameters:
        - status: Filter by auction status (active, closed, cancelled)
        - active: If 'true', show only currently active auctions
        - search: Search in title and description
        """

        queryset = Auction.objects.select_related('owner', 'winner')

        serializer = AuctionListSerializer(queryset, many=True)
        return APIResponse.success_response(
            data=serializer.data,
            messgae="Data fetched successfully"
        )