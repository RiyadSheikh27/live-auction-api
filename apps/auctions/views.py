import logging
from rest_framework.views import APIView
from rest_framework import status, permissions
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import ValidationError
from apps.utils.permissions import IsOwnerOrReadOnly
from django.shortcuts import get_object_or_404

from django.utils import timezone
from django.db.models import Q

from .models import Auction, Bid
from .serializers import AuctionListSerializer, AuctionCreateSerializer, AuctionDetailSerializer, BidSerializer
from apps.utils.views import APIResponse

logger = logging.getLogger(__name__)


class AuctionListCreateAPIView(APIResponse, APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = PageNumberPagination

    def get(self, request):
        try:
            queryset = (
                Auction.objects.select_related("owner", "winner")
                .all()
                .order_by("-id")
            )

            # Filter by status
            status_filter = request.query_params.get("status")
            if status_filter:
                queryset = queryset.filter(status=status_filter)

            # Filter active auctions only
            active_only = request.query_params.get("active")
            if active_only and active_only.lower() == "true":
                now = timezone.now()
                queryset = queryset.filter(
                    status="active",
                    start_time__lte=now,
                    end_time__gt=now,
                )

            # Search by title or description
            search = request.query_params.get("search")
            if search:
                queryset = queryset.filter(
                    Q(title__icontains=search) |
                    Q(description__icontains=search)
                )

            # Pagination
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(queryset, request)

            if page is not None:
                serializer = AuctionListSerializer(page, many=True)

                now = timezone.now()

                meta = {
                    "count": paginator.page.paginator.count,
                    "next": paginator.get_next_link(),
                    "previous": paginator.get_previous_link(),
                }

                return self.success_response(
                    message="Retrieved auction list successfully",
                    data=serializer.data,
                    meta=meta,
                )

            # # No pagination case
            # serializer = AuctionListSerializer(queryset, many=True)
            # return self.success_response(
            #     message="Retrieved auction list successfully",
            #     data=serializer.data,
            # )

        except ValidationError as e:
            logger.warning(f"Validation error in AuctionList API: {e}")
            return self.error_response(
                message="Validation error",
                errors=e.detail,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            logger.exception("Unexpected error in AuctionList API")
            return self.error_response(
                message="Internal server error",
                errors=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


    def post(self, request):
        """Create a New Auction"""
        try:
            serializer = AuctionCreateSerializer(
                data=request.data,
                context={'request': request}
            )

            if serializer.is_valid():
                auction = serializer.save()

                response_serializer = AuctionDetailSerializer(auction)

                return self.success_response(
                    message="Auction uploaded successfully",
                    data=response_serializer.data,
                    status_code=status.HTTP_201_CREATED
                )

            return self.error_response(
                message="Validation Error",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        except ValidationError as e:
            return self.error_response(
                message="Validation Error",
                errors=e.detail,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            return self.error_response(
                message="internal Server Error",
                errors=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class AuctionDetailAPIView(APIResponse, APIView):
    """
    GET /api/auctions/{id}/ - Retrieve auction details
    PUT /api/auctions/{id}/ - Update auction (owner only)
    PATCH /api/auctions/{id}/ - Partial update (owner only)
    DELETE /api/auctions/{id}/ - Cancel auction (owner only, no bids)
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def get_object(self, pk):
        """Get auction object or return 404"""
        auction = get_object_or_404(Auction.objects.select_related('owner', 'winner'), pk=pk)

        self.check_object_permissions(self.request, auction)
        return auction

    def get(self, request, pk):
        """Retrieve detailed auction information"""
        try:
            auction = self.get_object(pk)
            serializer = AuctionDetailSerializer(auction)

            return self.success_response(
                message='Retrived data successfully',
                data = serializer.data,
            )
        except ValidationError as e:
            return self.error_response(
                message="Validation Error",
                errors=e.detail,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return self.error_response(
                message="Internal Server Error",
                errors=e.detail,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def patch(self, request, pk):
        """
        Update auction (full update)
        Only owner can update
        """
        try:
            auction = self.get_object(pk)
            serializer = AuctionCreateSerializer(
                auction,
                data=request.data,
                partial=True,
                context={'request': request}
            )

            if serializer.is_valid():
                serializer.save()
                response_serializer = AuctionDetailSerializer(auction)

                return self.success_response(
                    message="Auction updated successfully",
                    data=response_serializer.data,
                    status_code=status.HTTP_200_OK
                )
            return self.error_response(
                message="Validation Error",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return self.error_response(
                message="Internal Server Error",
                errors=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request, pk):
        """Cancel auction (owner only, no bids)"""
        try:
            auction = self.get_object(pk)
            if auction.total_bids > 0:
                return self.error_response(
                    message="Cannot delete auction with existing bids",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            if auction.status == 'active':
                auction.status = 'cancelled'
                auction.save()
                return self.success_response(
                    message="Auction cancelled successfully",
                    status_code=status.HTTP_200_OK
                )
            return self.error_response(
                message="Can only cancel active auctions",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return self.error_response(
                message="Internal Server Error",
                errors=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class AuctionBidsAPIView(APIResponse, APIView):
    """
    GET /api/auctions/{id}/bids/ - Get all bids for an auction
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = PageNumberPagination
    def get(self, request, pk):
        """Get all bids for a specific auction"""
        try:
            auction = get_object_or_404(Auction, pk=pk)
            bids = auction.bids.select_related('bidder').all()
            # Pagination
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(bids, request)
            if page is not None:
                serializer = BidSerializer(page, many=True)
                meta = {
                    "count": paginator.page.paginator.count,
                    "next": paginator.get_next_link(),
                    "previous": paginator.get_previous_link(),
                }
                return self.success_response(
                    message="Retrieved bids successfully",
                    data=serializer.data,
                    meta=meta
                )
            serializer = BidSerializer(bids, many=True)
            return self.success_response(
                message="Retrieved bids successfully",
                data=serializer.data,
            )
        except ValidationError as e:
            return self.error_response(
                message="Validation Error",
                errors=e.detail,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return self.error_response(
                message="Internal Server Error",
                errors=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MyAuctionsAPIView(APIResponse, APIView):
    """
    GET /api/auctions/my-auctions/ - Get auctions created by current user
    """
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PageNumberPagination

    def get(self, request):
        """Get all auctions owned by the authenticated user"""
        try:
            auctions = Auction.objects.filter(
                owner=request.user
            ).select_related('winner')
            # Pagination
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(auctions, request)
            if page is not None:
                serializer = AuctionListSerializer(page, many=True)
                meta = {
                    "count": paginator.page.paginator.count,
                    "next": paginator.get_next_link(),
                    "previous": paginator.get_previous_link(),
                }
                return self.success_response(
                    message="Retrieved auction list successfully",
                    data=serializer.data,
                    meta=meta
                )
            serializer = AuctionListSerializer(auctions, many=True)
            return self.success_response(
                message="Retrieved auction list successfully",
                data=serializer.data,
            )
        except ValidationError as e:
            return self.error_response(
                message="Validation Error",
                errors=e.detail,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return self.error_response(
                message="Internal Server Error",
                errors=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MyBidsAPIView(APIResponse, APIView):
    """
    GET /api/auctions/my-bids/ - Get bids placed by current user
    """
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PageNumberPagination

    def get(self, request):
        """Get all bids placed by the authenticated user"""
        try:
            bids = Bid.objects.filter(
                bidder=request.user
            ).select_related('auction', 'auction__owner')
            # Pagination
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(bids, request)
            if page is not None:
                serializer = BidSerializer(page, many=True)
                meta = {
                    "count": paginator.page.paginator.count,
                    "next": paginator.get_next_link(),
                    "previous": paginator.get_previous_link(),
                }
                return self.success_response(
                    message="Retrieved bids successfully",
                    data=serializer.data,
                    meta=meta
                )
            serializer = BidSerializer(bids, many=True)
            return self.success_response(
                message="Retrieved bids successfully",
                data=serializer.data,
            )
        except ValidationError as e:
            return self.error_response(
                message="Validation Error",
                errors=e.detail,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return self.error_response(
                message="Internal Server Error",
                errors=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )