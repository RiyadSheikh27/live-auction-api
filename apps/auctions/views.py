import logging
from rest_framework.views import APIView
from rest_framework import status, permissions
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import ValidationError

from django.utils import timezone
from django.db.models import Q

from .models import Auction
from .serializers import AuctionListSerializer
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
                .order_by("-id")  # important for pagination stability
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

                return self.success_response(
                    message="Retrieved auction list successfully",
                    data={
                        "count": paginator.page.paginator.count,
                        "next": paginator.get_next_link(),
                        "previous": paginator.get_previous_link(),
                        "results": serializer.data,
                    },
                )

            # No pagination case
            serializer = AuctionListSerializer(queryset, many=True)
            return self.success_response(
                message="Retrieved auction list successfully",
                data=serializer.data,
            )

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
