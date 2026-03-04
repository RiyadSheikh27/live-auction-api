# Visual Workflow & Dependency Maps

## Quick Navigation
1. [File Dependency Tree](#file-dependency-tree)
2. [Function Call Flow](#function-call-flow)
3. [Data Flow Diagrams](#data-flow-diagrams)
4. [Module Interaction Map](#module-interaction-map)
5. [Build Order Timeline](#build-order-timeline)

---

## File Dependency Tree

### Complete File Dependencies (Bottom to Top)

```
DATABASE (SQLite)
    ↑
models.py (defines database structure)
    ↑
    ├── serializers.py (converts models ↔ JSON)
    │        ↑
    │   views.py (handles requests)
    │        ↑
    │   urls.py (maps URLs → views)
    │        ↑
    │   config/urls.py (includes app URLs)
    │
    ├── signals.py (reacts to model events)
    │        ↑
    │   tasks.py (background jobs)
    │        ↑
    │   config/celery.py (task config)
    │
    ├── consumers.py (WebSocket handlers)
    │        ↑
    │   routing.py (WebSocket URLs)
    │        ↑
    │   config/asgi.py (includes routing)
    │
    └── admin.py (admin interface)

config/settings/base.py (REQUIRED FOR EVERYTHING)
    ↑
manage.py (entry point)
```

---

## Function Call Flow

### 1. HTTP REST API Request Flow

```
User Browser
    ↓
    sends: POST /api/auctions/
    ↓
manage.py → runserver
    ↓
config/urls.py
    ├─ matches: /api/auctions/
    └─ includes: apps.auctions.urls
            ↓
apps/auctions/urls.py
    ├─ matches: '' (empty path after /api/auctions/)
    └─ routes to: AuctionListCreateAPIView.as_view()
            ↓
apps/auctions/views.py
    └─ AuctionListCreateAPIView
        └─ post(self, request):
                ↓
            serializer = AuctionCreateSerializer(data=request.data)
                ↓
apps/auctions/serializers.py
    └─ AuctionCreateSerializer
        ├─ validate(self, attrs):  # Validates data
        └─ create(self, validated_data):  # Creates auction
                ↓
            auction = Auction.objects.create(**validated_data)
                ↓
apps/auctions/models.py
    └─ Auction.objects.create()
        └─ SQL: INSERT INTO auctions ...
                ↓
            DATABASE
                ↓
        Returns: Auction instance
            ↓
apps/auctions/signals.py (if bid was created)
    └─ post_save signal fires
        └─ update_auction_price()
            └─ Updates Auction.current_price
                ↓
apps/auctions/serializers.py
    └─ AuctionDetailSerializer
        └─ Converts Auction → JSON
            ↓
apps/auctions/views.py
    └─ Returns: Response(serializer.data, status=201)
        ↓
    User Browser receives JSON
```

---

### 2. WebSocket Bidding Flow

```
User Browser
    ↓
    connects to: ws://localhost:8000/ws/auction/1/
    ↓
config/asgi.py
    └─ ProtocolTypeRouter
        ├─ checks: websocket protocol
        └─ routes to: URLRouter(websocket_urlpatterns)
                ↓
apps/bidding/routing.py
    ├─ matches: /ws/auction/(?P<auction_id>\d+)/
    └─ routes to: AuctionConsumer.as_asgi()
            ↓
apps/bidding/consumers.py
    └─ AuctionConsumer
        ├─ async def connect(self):
        │   ├─ self.auction_id = from URL
        │   ├─ self.auction_group_name = f'auction_{auction_id}'
        │   ├─ channel_layer.group_add(group, channel_name)
        │   └─ accept()
        │
        ├─ async def receive(self, text_data):
        │   ├─ data = json.loads(text_data)
        │   └─ if type == 'place_bid':
        │       └─ handle_place_bid(data)
        │           ↓
        │       bid = await create_bid(amount)
        │           ↓
        │       @database_sync_to_async
        │       def create_bid(amount):
        │           ↓
        │       apps/auctions/models.py
        │           └─ Bid.objects.create()
        │               ↓
        │           DATABASE
        │               ↓
        │           apps/auctions/signals.py
        │               └─ update_auction_price()
        │                   ↓
        │           channel_layer.group_send(
        │               'auction_1',
        │               {
        │                   'type': 'bid_placed',
        │                   'bid': {...}
        │               }
        │           )
        │               ↓
        │           REDIS (channel layer)
        │               ↓
        │           Broadcasts to ALL connected clients
        │               ↓
        └─ async def bid_placed(self, event):
            └─ send(json.dumps(event))
                ↓
            ALL users see update in real-time
```

---

### 3. Celery Background Task Flow

```
config/celery.py
    └─ beat_schedule defined:
        {
            'check-expired-auctions': {
                'task': 'apps.auctions.tasks.check_and_close_expired_auctions',
                'schedule': 60.0  # every 60 seconds
            }
        }
            ↓
Celery Beat (scheduler process)
    └─ Every 60 seconds, triggers task
        ↓
    REDIS (broker)
        └─ Task queued: check_and_close_expired_auctions
            ↓
Celery Worker (worker process)
    └─ Picks up task from queue
        ↓
apps/auctions/tasks.py
    └─ @shared_task
        check_and_close_expired_auctions():
            ↓
        Query: Auction.objects.filter(
            status='active',
            end_time__lte=now()
        )
            ↓
        For each expired auction:
            close_auction.delay(auction_id)
                ↓
            REDIS (broker)
                └─ New task queued: close_auction(1)
                    ↓
                Celery Worker picks up
                    ↓
                apps/auctions/tasks.py
                    └─ close_auction(auction_id):
                        ├─ Get auction
                        ├─ Get highest bid
                        ├─ Determine winner
                        ├─ auction.status = 'closed'
                        ├─ auction.save()
                        └─ notify_auction_participants.delay(auction_id)
                            ↓
                        REDIS (broker)
                            └─ New task: notify_auction_participants(1)
                                ↓
                            Celery Worker picks up
                                ↓
                            apps/auctions/tasks.py
                                └─ notify_auction_participants(auction_id):
                                    ├─ Get all bidders
                                    ├─ Log notifications
                                    └─ (In production: send emails)
```

---

## Data Flow Diagrams

### User Registration Flow

```
┌─────────────────────────────────────────────────────────┐
│ Client                                                  │
│ POST /api/auth/register/                               │
│ {                                                       │
│   "username": "john",                                   │
│   "email": "john@test.com",                            │
│   "password": "Test123!"                               │
│ }                                                       │
└───────────────────┬─────────────────────────────────────┘
                    ↓
┌───────────────────────────────────────────────────────┐
│ urls.py: /api/auth/register/                          │
│ → apps.users.urls                                     │
│   → UserRegistrationView                              │
└───────────────────┬───────────────────────────────────┘
                    ↓
┌───────────────────────────────────────────────────────┐
│ views.py: UserRegistrationView.post()                 │
│ 1. Get request data                                    │
└───────────────────┬───────────────────────────────────┘
                    ↓
┌───────────────────────────────────────────────────────┐
│ serializers.py: UserRegistrationSerializer            │
│ 1. Validate username (unique, length)                 │
│ 2. Validate email (unique, format)                    │
│ 3. Validate password (strength)                       │
│ 4. Check passwords match                              │
└───────────────────┬───────────────────────────────────┘
                    ↓
┌───────────────────────────────────────────────────────┐
│ serializers.py: create()                               │
│ 1. Hash password                                       │
│ 2. Create User instance                               │
└───────────────────┬───────────────────────────────────┘
                    ↓
┌───────────────────────────────────────────────────────┐
│ models.py: User.objects.create_user()                 │
│ 1. INSERT INTO users ...                              │
└───────────────────┬───────────────────────────────────┘
                    ↓
┌───────────────────────────────────────────────────────┐
│ Database: SQLite                                       │
│ users table now has new row                           │
└───────────────────┬───────────────────────────────────┘
                    ↓
┌───────────────────────────────────────────────────────┐
│ views.py: Generate JWT tokens                         │
│ RefreshToken.for_user(user)                           │
└───────────────────┬───────────────────────────────────┘
                    ↓
┌───────────────────────────────────────────────────────┐
│ Client receives:                                       │
│ {                                                      │
│   "user": {...},                                       │
│   "tokens": {                                          │
│     "access": "eyJ...",                               │
│     "refresh": "eyJ..."                               │
│   }                                                    │
│ }                                                      │
└────────────────────────────────────────────────────────┘
```

---

### Auction Creation Flow

```
Client (with JWT token)
    ↓
POST /api/auctions/
Authorization: Bearer <token>
{
  "title": "Camera",
  "starting_price": "100.00",
  "end_time": "2026-12-31T23:59:59Z"
}
    ↓
Middleware: JWT Authentication
    ├─ Decode token
    ├─ Verify signature
    ├─ Check expiration
    └─ Set request.user
        ↓
    AuctionListCreateAPIView.post()
        ↓
    AuctionCreateSerializer
        ├─ Validate title (not empty, max 200 chars)
        ├─ Validate starting_price (> 0)
        ├─ Validate end_time (in future)
        └─ create():
            ├─ Set owner = request.user
            ├─ Set current_price = starting_price
            └─ Auction.objects.create()
                ↓
            Database INSERT
                ↓
            Return Auction instance
                ↓
        AuctionDetailSerializer (for response)
            └─ Convert to JSON with nested user data
                ↓
            Response(status=201)
```

---

### Bid Placement Flow (WebSocket)

```
Browser JavaScript
    ↓
ws.send(JSON.stringify({
  type: 'place_bid',
  amount: 150.00
}))
    ↓
WebSocket Connection (authenticated)
    ↓
AuctionConsumer.receive(text_data)
    ├─ Parse JSON
    └─ handle_place_bid(data)
        ├─ Check user authenticated
        ├─ Validate amount > current_price
        ├─ Validate user != auction owner
        └─ create_bid(amount)
            ↓
        @database_sync_to_async
        def create_bid():
            ↓
        Bid.objects.create(
            auction=auction,
            bidder=user,
            amount=amount
        )
            ↓
        Database INSERT
            ↓
        Signal: post_save fires
            ↓
        update_auction_price()
            ├─ auction.current_price = bid.amount
            └─ auction.save()
                ↓
            Database UPDATE
                ↓
        channel_layer.group_send('auction_1', {
            'type': 'bid_placed',
            'bid': {...}
        })
            ↓
        REDIS pub/sub
            ↓
        ALL consumers in group receive message
            ↓
        Each consumer's bid_placed() called
            ↓
        Each sends JSON to their WebSocket client
            ↓
        ALL browsers update UI in real-time
```

---

## Module Interaction Map

### How Apps Interact

```
┌──────────────────────────────────────────────────────┐
│                   config/                             │
│  ┌────────────┐  ┌────────────┐  ┌─────────────┐   │
│  │ settings/  │  │  celery.py │  │   asgi.py   │   │
│  │  base.py   │  └─────┬──────┘  └──────┬──────┘   │
│  └──────┬─────┘        │                 │          │
│         │              │                 │          │
└─────────┼──────────────┼─────────────────┼──────────┘
          │              │                 │
          │              │                 │
    ┌─────▼──────┐  ┌────▼────┐      ┌────▼──────┐
    │            │  │         │      │           │
    │   users    │  │auctions │      │  bidding  │
    │            │  │         │      │           │
    │  ┌──────┐  │  │┌──────┐ │      │ ┌──────┐  │
    │  │models│  │  ││models│ │      │ │models│  │
    │  └───┬──┘  │  │└───┬──┘ │      │ └──────┘  │
    │      │     │  │    │    │      │           │
    │  ┌───▼───┐ │  │┌───▼──┐ │      │ ┌──────┐  │
    │  │serial-│ │  ││serial││ │      │ │consu-│  │
    │  │izers  │ │  ││izers │ │      │ │mers  │  │
    │  └───┬───┘ │  │└───┬──┘ │      │ └───┬──┘  │
    │      │     │  │    │    │      │     │     │
    │  ┌───▼───┐ │  │┌───▼──┐ │      │ ┌───▼───┐ │
    │  │ views │ │  ││views │ │      │ │ views │ │
    │  └───┬───┘ │  │└───┬──┘ │      │ └───┬───┘ │
    │      │     │  │    │    │      │     │     │
    │  ┌───▼───┐ │  │┌───▼──┐ │      │ ┌───▼───┐ │
    │  │ urls  │ │  ││urls  │ │      │ │ urls  │ │
    │  └───────┘ │  │└──────┘ │      │ └───────┘ │
    │            │  │         │      │           │
    │            │  │┌──────┐ │      │ ┌───────┐ │
    │            │  ││tasks │ │      │ │routing│ │
    │            │  │└──────┘ │      │ └───────┘ │
    │            │  │         │      │           │
    │            │  │┌──────┐ │      │           │
    │            │  ││signal│ │      │           │
    │            │  │└──────┘ │      │           │
    └────────────┘  └─────────┘      └───────────┘
          │              │                 │
          │              │                 │
          └──────┬───────┴────────┬────────┘
                 │                │
                 ▼                ▼
         ┌──────────────┐  ┌──────────┐
         │   Database   │  │  Redis   │
         │   (SQLite)   │  │          │
         └──────────────┘  └──────────┘
```

### Dependency Between Apps

```
users (independent)
    ↓ (ForeignKey)
auctions (depends on users)
    ↓ (imports models)
bidding (depends on auctions)
```

**Key:**
- `users` has NO dependencies on other apps
- `auctions` depends on `users` for User model
- `bidding` depends on `auctions` for Auction/Bid models

---

## Build Order Timeline

### Complete Build Sequence with Time Estimates

```
Hour 0:00 ─┐
           │ PHASE 1: Foundation (30 min)
           │ ├─ 0:00 - Install Python packages
           │ ├─ 0:10 - Create settings files
           │ ├─ 0:20 - Create manage.py, urls.py
           │ └─ 0:30 - Test: python manage.py check ✓
           │
Hour 0:30 ─┤
           │ PHASE 2: Users (1 hour)
           │ ├─ 0:30 - Create User model
           │ ├─ 0:35 - Run migrations
           │ ├─ 0:40 - Test: Create user in shell ✓
           │ ├─ 0:45 - Create serializers
           │ ├─ 0:50 - Test: Validate data ✓
           │ ├─ 1:00 - Create views
           │ ├─ 1:10 - Create URLs
           │ ├─ 1:20 - Test: Register via API ✓
           │ └─ 1:30 - Create admin, Test admin panel ✓
           │
Hour 1:30 ─┤
           │ PHASE 3: Auctions (1.5 hours)
           │ ├─ 1:30 - Create Auction & Bid models
           │ ├─ 1:35 - Run migrations
           │ ├─ 1:40 - Test: Create auction in shell ✓
           │ ├─ 1:50 - Create serializers
           │ ├─ 2:00 - Test: Serialize auction ✓
           │ ├─ 2:05 - Create permissions
           │ ├─ 2:10 - Create views (5 APIViews)
           │ ├─ 2:30 - Create URLs
           │ ├─ 2:40 - Test: CRUD via API ✓
           │ └─ 3:00 - Create admin, Test admin panel ✓
           │
Hour 3:00 ─┤
           │ PHASE 4: Celery (45 min)
           │ ├─ 3:00 - Install Redis
           │ ├─ 3:10 - Test: redis-cli ping ✓
           │ ├─ 3:15 - Create signals.py
           │ ├─ 3:20 - Test: Bid updates price ✓
           │ ├─ 3:25 - Create tasks.py
           │ ├─ 3:30 - Start Celery worker
           │ ├─ 3:35 - Test: Manual task execution ✓
           │ ├─ 3:40 - Start Celery beat
           │ └─ 3:45 - Test: Auto-close auction ✓
           │
Hour 3:45 ─┤
           │ PHASE 5: WebSocket (1 hour)
           │ ├─ 3:45 - Create routing.py
           │ ├─ 3:50 - Create consumers.py
           │ ├─ 4:10 - Update asgi.py
           │ ├─ 4:15 - Test: WebSocket connection ✓
           │ ├─ 4:25 - Create bidding views.py
           │ ├─ 4:35 - Create bidding urls.py
           │ └─ 4:45 - Test: Place bid via REST & WS ✓
           │
Hour 4:45 ─┤
           │ PHASE 6: Testing & Polish (30 min)
           │ ├─ 4:45 - Create test data
           │ ├─ 5:00 - Run full integration test
           │ └─ 5:15 - Verify all features ✓
           │
Hour 5:15 ─┘ COMPLETE!
```

---

## Which File Depends on Which

### Dependency Matrix

```
File A depends on File B means: "A imports from B" or "A requires B to exist"

┌─────────────────────────────────────────────────────────┐
│ INDEPENDENT FILES (No dependencies)                      │
├─────────────────────────────────────────────────────────┤
│ requirements.txt                                         │
│ .env.example                                            │
│ .gitignore                                              │
│ manage.py (only needs settings)                         │
│ config/settings/__init__.py                             │
│ config/settings/base.py (only needs installed packages) │
│ apps/users/models.py (only needs Django)                │
│ apps/auctions/permissions.py (only needs DRF)           │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ LEVEL 1 DEPENDENCIES                                     │
├─────────────────────────────────────────────────────────┤
│ config/settings/development.py                          │
│   └─ depends on: config/settings/base.py               │
│                                                          │
│ config/__init__.py                                      │
│   └─ depends on: config/celery.py                      │
│                                                          │
│ config/celery.py                                        │
│   └─ depends on: config/settings/base.py               │
│                                                          │
│ apps/users/serializers.py                              │
│   └─ depends on: apps/users/models.py                  │
│                                                          │
│ apps/auctions/models.py                                 │
│   └─ depends on: apps/users/models.py                  │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ LEVEL 2 DEPENDENCIES                                     │
├─────────────────────────────────────────────────────────┤
│ apps/users/views.py                                     │
│   └─ depends on: apps/users/serializers.py             │
│       └─ depends on: apps/users/models.py              │
│                                                          │
│ apps/auctions/serializers.py                            │
│   ├─ depends on: apps/auctions/models.py               │
│   │   └─ depends on: apps/users/models.py              │
│   └─ depends on: apps/users/serializers.py             │
│                                                          │
│ apps/auctions/signals.py                                │
│   └─ depends on: apps/auctions/models.py               │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ LEVEL 3 DEPENDENCIES                                     │
├─────────────────────────────────────────────────────────┤
│ apps/users/urls.py                                      │
│   └─ depends on: apps/users/views.py                   │
│       └─ depends on: apps/users/serializers.py         │
│           └─ depends on: apps/users/models.py          │
│                                                          │
│ apps/auctions/views.py                                  │
│   ├─ depends on: apps/auctions/serializers.py          │
│   └─ depends on: apps/auctions/permissions.py          │
│                                                          │
│ apps/auctions/tasks.py                                  │
│   ├─ depends on: apps/auctions/models.py               │
│   └─ depends on: apps/auctions/signals.py              │
│                                                          │
│ apps/bidding/consumers.py                               │
│   └─ depends on: apps/auctions/models.py               │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ LEVEL 4 DEPENDENCIES (Top Level)                        │
├─────────────────────────────────────────────────────────┤
│ apps/auctions/urls.py                                   │
│   └─ depends on: apps/auctions/views.py                │
│       └─ depends on: apps/auctions/serializers.py      │
│           └─ depends on: apps/auctions/models.py       │
│                                                          │
│ apps/bidding/views.py                                   │
│   └─ depends on: apps/auctions/models.py               │
│                                                          │
│ config/urls.py                                          │
│   ├─ depends on: apps/users/urls.py                    │
│   └─ depends on: apps/auctions/urls.py                 │
│                                                          │
│ config/asgi.py                                          │
│   └─ depends on: apps/bidding/routing.py               │
│       └─ depends on: apps/bidding/consumers.py         │
└─────────────────────────────────────────────────────────┘
```

---

## Summary: Build in This Order

### Quick Reference

1. **config/settings/base.py** - Everything needs this
2. **apps/users/models.py** - Core user model
3. **apps/users/serializers.py** - Depends on models
4. **apps/users/views.py** - Depends on serializers
5. **apps/users/urls.py** - Depends on views
6. **apps/auctions/models.py** - Depends on users models
7. **apps/auctions/serializers.py** - Depends on auction models
8. **apps/auctions/views.py** - Depends on serializers
9. **apps/auctions/urls.py** - Depends on views
10. **apps/auctions/signals.py** - Depends on models
11. **apps/auctions/tasks.py** - Depends on models & signals
12. **apps/bidding/consumers.py** - Depends on auction models
13. **apps/bidding/routing.py** - Depends on consumers
14. **config/asgi.py** - Depends on routing
15. **config/urls.py** - Depends on all app urls

**Test after each file to catch errors early!**

---

## Final Visual: Complete System

```
                    ┌─────────────┐
                    │   Client    │
                    │  (Browser)  │
                    └──────┬──────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
      HTTP │          WebSocket       Timer│
           │               │               │
           ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐   ┌──────────┐
    │  urls.py │    │routing.py│   │Celery    │
    │          │    │          │   │Beat      │
    └────┬─────┘    └────┬─────┘   └────┬─────┘
         │               │              │
         ▼               ▼              ▼
    ┌──────────┐    ┌──────────┐   ┌──────────┐
    │ views.py │    │consumers │   │ tasks.py │
    │          │    │   .py    │   │          │
    └────┬─────┘    └────┬─────┘   └────┬─────┘
         │               │              │
         ▼               │              │
    ┌──────────┐         │              │
    │serializer│         │              │
    │   .py    │         │              │
    └────┬─────┘         │              │
         │               │              │
         └───────┬───────┴──────┬───────┘
                 │              │
                 ▼              ▼
            ┌─────────┐    ┌────────┐
            │models.py│    │signals │
            │         │───>│  .py   │
            └────┬────┘    └────────┘
                 │
                 ▼
         ┌───────────────┐
         │   Database    │
         │   (SQLite)    │
         └───────────────┘
         
         ┌───────────────┐
         │     Redis     │
         │ (Celery+Chnl) │
         └───────────────┘
```

This is your complete roadmap! Follow it step by step, test after each phase, and you'll have a fully functional auction system! 🎯
