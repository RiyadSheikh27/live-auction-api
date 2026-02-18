import logging
from rest_framework.views import APIView
from rest_framework import status, permissions
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import ValidationError
from apps.utils.permissions import IsOwnerOrReadOnly
from django.shortcuts import get_object_or_404

from django.utils import timezone
from django.db.models import Q

from .models import Auction
from .serializers import AuctionListSerializer, AuctionCreateSerializer, AuctionDetailSerializer
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
        
    def put(self, request, pk):
         """
        Update auction (full update)
        Only owner can update
        """
        try:
            auction = self.get_object(pk)
            serializer = AuctionCreateSerializer(
                auction,
                data=request.data,
                context={'request': request}
            )
            
            if serializer.is_valid():
                serializer.save()
                response_serializer = AuctionDetailSerializer(auction)

        
        

