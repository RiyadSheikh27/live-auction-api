"""
WebSocket Consumer
==================
Handles WebSocket connections for real-time bidding

DJANGO CHANNELS CONSUMERS:
- Similar to Django views, but for WebSocket connections
- Handle connect, disconnect, and receive events
- Can send messages to clients
- Use async for better performance

CHANNEL LAYERS:
- Allow consumers to talk to each other
- Send messages to groups of connections
- Use Redis as backend for production

HOW IT WORKS:
1. User connects to ws://localhost:8000/ws/auction/{auction_id}/
2. Connection added to auction's group
3. When user places bid:
   - Validate bid
   - Save to database
   - Broadcast to all users in auction group
4. All connected users receive real-time updates
"""

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from decimal import Decimal

logger = logging.getLogger(__name__)


class AuctionConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for auction bidding
    
    Handles real-time bidding for a specific auction
    """
    
    async def connect(self):
        """
        Called when WebSocket connection is established
        
        Steps:
        1. Extract auction_id from URL
        2. Create a group name for this auction
        3. Add this connection to the group
        4. Accept the connection
        """
        # Get auction ID from URL route
        self.auction_id = self.scope['url_route']['kwargs']['auction_id']
        self.auction_group_name = f'auction_{self.auction_id}'
        
        # Get user from scope (set by AuthMiddlewareStack)
        self.user = self.scope.get('user', AnonymousUser())
        
        # Join auction group (so we can broadcast to all watchers)
        await self.channel_layer.group_add(
            self.auction_group_name,
            self.channel_name
        )
        
        # Accept the WebSocket connection
        await self.accept()
        
        logger.info(
            f"User {self.user.username if self.user.is_authenticated else 'Anonymous'} "
            f"connected to auction {self.auction_id}"
        )
        
        # Send current auction status to the newly connected user
        auction_data = await self.get_auction_data()
        if auction_data:
            await self.send(text_data=json.dumps({
                'type': 'auction_status',
                'auction': auction_data
            }))
    
    async def disconnect(self, close_code):
        """
        Called when WebSocket connection is closed
        
        Remove this connection from the auction group
        """
        await self.channel_layer.group_discard(
            self.auction_group_name,
            self.channel_name
        )
        
        logger.info(
            f"User {self.user.username if self.user.is_authenticated else 'Anonymous'} "
            f"disconnected from auction {self.auction_id}"
        )
    
    async def receive(self, text_data):
        """
        Called when message is received from WebSocket
        
        Expected message format:
        {
            "type": "place_bid",
            "amount": 150.00
        }
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'place_bid':
                await self.handle_place_bid(data)
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': f'Unknown message type: {message_type}'
                }))
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
        except Exception as e:
            logger.error(f"Error in receive: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Internal server error'
            }))
    
    async def handle_place_bid(self, data):
        """
        Handle bid placement
        
        Steps:
        1. Validate user is authenticated
        2. Validate bid amount
        3. Create bid in database
        4. Broadcast to all users in auction group
        """
        # Check authentication
        if not self.user.is_authenticated:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Authentication required to place bids'
            }))
            return
        
        try:
            amount = Decimal(str(data.get('amount', 0)))
            
            # Validate and create bid
            bid, error = await self.create_bid(amount)
            
            if error:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': error
                }))
                return
            
            # Broadcast bid to all users watching this auction
            await self.channel_layer.group_send(
                self.auction_group_name,
                {
                    'type': 'bid_placed',  # This will call self.bid_placed()
                    'bid': {
                        'id': bid.id,
                        'amount': str(bid.amount),
                        'bidder': bid.bidder.username,
                        'created_at': bid.created_at.isoformat(),
                    },
                    'auction': {
                        'id': bid.auction.id,
                        'current_price': str(bid.auction.current_price),
                    }
                }
            )
            
        except (ValueError, TypeError):
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid bid amount'
            }))
    
    async def bid_placed(self, event):
        """
        Called when a bid is broadcast to the group
        
        This method receives the event from group_send
        and sends it to the WebSocket client
        """
        await self.send(text_data=json.dumps({
            'type': 'bid_placed',
            'bid': event['bid'],
            'auction': event['auction'],
        }))
    
    # Database operations (must be sync -> async)
    
    @database_sync_to_async
    def get_auction_data(self):
        """Get current auction data"""
        from apps.auctions.models import Auction
        
        try:
            auction = Auction.objects.get(id=self.auction_id)
            return {
                'id': auction.id,
                'title': auction.title,
                'current_price': str(auction.current_price),
                'status': auction.status,
                'is_active': auction.is_active,
                'total_bids': auction.total_bids,
            }
        except Auction.DoesNotExist:
            return None
    
    @database_sync_to_async
    def create_bid(self, amount):
        """
        Create a bid in the database
        
        Returns:
            tuple: (bid_object, error_message)
        """
        from apps.auctions.models import Auction, Bid
        
        try:
            auction = Auction.objects.get(id=self.auction_id)
            
            # Validate auction is active
            if not auction.is_active:
                return None, "Auction is not active"
            
            # Validate bid amount
            if amount <= auction.current_price:
                return None, f"Bid must be higher than current price (${auction.current_price})"
            
            # Validate user is not the owner
            if auction.owner == self.user:
                return None, "You cannot bid on your own auction"
            
            # Create bid
            bid = Bid.objects.create(
                auction=auction,
                bidder=self.user,
                amount=amount
            )
            
            logger.info(
                f"Bid placed: {self.user.username} bid ${amount} on auction {self.auction_id}"
            )
            
            return bid, None
            
        except Auction.DoesNotExist:
            return None, "Auction not found"
        except Exception as e:
            logger.error(f"Error creating bid: {str(e)}")
            return None, "Failed to place bid"
