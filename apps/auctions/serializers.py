from rest_framework import serializers
from django.utils import timezone
from .models import Auction, Bid
from apps.users.serializers import UserSerializer


class BidSerializer(serializers.ModelSerializer):
    """
    Serializer for Bid model
    """
    
    bidder = UserSerializer(read_only=True)
    bidder_username = serializers.CharField(
        source='bidder.username',
        read_only=True
    )
    
    class Meta:
        model = Bid
        fields = [
            'id',
            'auction',
            'bidder',
            'bidder_username',
            'amount',
            'created_at',
        ]
        read_only_fields = ['id', 'auction', 'bidder', 'created_at']


class AuctionListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for auction list view
    Only includes essential information
    """
    
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    total_bids = serializers.IntegerField(read_only=True)
    time_remaining = serializers.DurationField(read_only=True)
    
    class Meta:
        model = Auction
        fields = [
            'id',
            'title',
            'starting_price',
            'current_price',
            'owner_username',
            'status',
            'is_active',
            'total_bids',
            'start_time',
            'end_time',
            'time_remaining',
            'created_at',
        ]


class AuctionDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for single auction view
    Includes all information and related data
    """
    
    owner = UserSerializer(read_only=True)
    winner = UserSerializer(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    total_bids = serializers.IntegerField(read_only=True)
    time_remaining = serializers.DurationField(read_only=True)
    
    # Include latest bids
    latest_bids = serializers.SerializerMethodField()
    
    class Meta:
        model = Auction
        fields = [
            'id',
            'title',
            'description',
            'starting_price',
            'current_price',
            'reserve_price',
            'owner',
            'winner',
            'status',
            'is_active',
            'total_bids',
            'latest_bids',
            'start_time',
            'end_time',
            'time_remaining',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'current_price',
            'winner',
            'status',
            'created_at',
            'updated_at',
        ]
    
    def get_latest_bids(self, obj):
        """Get 5 most recent bids"""
        latest_bids = obj.bids.all()[:5]
        return BidSerializer(latest_bids, many=True).data


class AuctionCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating auctions
    """
    
    class Meta:
        model = Auction
        fields = [
            'title',
            'description',
            'starting_price',
            'reserve_price',
            'end_time',
        ]
    
    def validate_end_time(self, value):
        """Ensure end time is in the future"""
        if value <= timezone.now():
            raise serializers.ValidationError(
                "End time must be in the future"
            )
        return value
    
    def validate(self, attrs):
        """Validate reserve price is not less than starting price"""
        if attrs.get('reserve_price'):
            if attrs['reserve_price'] < attrs['starting_price']:
                raise serializers.ValidationError({
                    'reserve_price': 'Reserve price cannot be less than starting price'
                })
        return attrs
    
    def create(self, validated_data):
        """Create auction with current_price set to starting_price"""
        validated_data['current_price'] = validated_data['starting_price']
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)