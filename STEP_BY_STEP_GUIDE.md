# Step-by-Step Build, Run & Test Guide

## Table of Contents
1. [Project Building Order](#project-building-order)
2. [File Dependencies Map](#file-dependencies-map)
3. [Step-by-Step Implementation](#step-by-step-implementation)
4. [Testing Each Step](#testing-each-step)
5. [Workflow Diagrams](#workflow-diagrams)

---

## Project Building Order

### The Correct Order to Build This Project

```
Phase 1: Foundation (Django Setup)
  ↓
Phase 2: User Authentication
  ↓
Phase 3: Auction Models & API
  ↓
Phase 4: Celery Background Tasks
  ↓
Phase 5: WebSocket Real-time Bidding
  ↓
Phase 6: Additional Features
```

**Why This Order?**
- Each phase builds on the previous
- You can test after each phase
- Dependencies are clear
- Easy to debug

---

## File Dependencies Map

### Visual Dependency Tree

```
manage.py
    ↓
config/settings/base.py (REQUIRED FIRST)
    ↓
    ├── config/__init__.py
    ├── config/urls.py
    ├── config/wsgi.py
    ├── config/asgi.py
    └── config/celery.py
    ↓
apps/users/
    ├── models.py (REQUIRED FIRST)
    ├── serializers.py (depends on models.py)
    ├── views.py (depends on serializers.py)
    ├── urls.py (depends on views.py)
    └── admin.py (depends on models.py)
    ↓
apps/auctions/
    ├── models.py (depends on users/models.py)
    ├── serializers.py (depends on models.py)
    ├── permissions.py (standalone)
    ├── views.py (depends on serializers.py, permissions.py)
    ├── urls.py (depends on views.py)
    ├── signals.py (depends on models.py)
    ├── tasks.py (depends on models.py, signals.py)
    └── admin.py (depends on models.py)
    ↓
apps/bidding/
    ├── routing.py (standalone)
    ├── consumers.py (depends on auctions/models.py)
    ├── views.py (depends on auctions/models.py)
    └── urls.py (depends on views.py)
```

### Function Call Flow

```
HTTP Request Flow:
User Request → urls.py → views.py → serializers.py → models.py → Database

WebSocket Flow:
WS Connection → routing.py → consumers.py → models.py → Database
                                          ↓
                                    channel_layer (Redis)
                                          ↓
                              Broadcast to all connected

Celery Task Flow:
Celery Beat → tasks.py → models.py → Database
                      ↓
                  signals.py (triggers on model save)
```

---

## Step-by-Step Implementation

## PHASE 1: Foundation Setup (30 minutes)

### Step 1.1: Project Initialization

**Files to Create (in order):**
1. `requirements.txt`
2. `.env.example`
3. `.gitignore`

**What to Do:**
```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create .env file
cp .env.example .env

# 4. Generate SECRET_KEY
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# 5. Add the key to .env
# SECRET_KEY=<paste-generated-key-here>
```

**Dependencies:**
- None (this is the starting point)

**Test:**
```bash
# Verify Python packages installed
pip list | grep -E "Django|celery|channels|redis"

# Should see:
# Django                5.0.1
# celery                5.3.6
# channels              4.0.0
# redis                 5.0.1
```

---

### Step 1.2: Django Configuration Files

**Files to Create (in order):**
1. `config/settings/__init__.py`
2. `config/settings/base.py`
3. `config/settings/development.py`
4. `config/settings/production.py`
5. `config/__init__.py`
6. `manage.py`

**What Each File Does:**

**`config/settings/base.py`:**
- Defines INSTALLED_APPS (all Django apps and third-party packages)
- Sets up database configuration
- Configures DRF, JWT, Channels, Celery
- **This is the heart of your project configuration**

**`config/settings/development.py`:**
- Imports everything from base.py
- Sets DEBUG=True
- Allows all CORS origins

**`config/__init__.py`:**
- Imports Celery app
- Makes Celery auto-discovered when Django starts

**`manage.py`:**
- Django's command-line tool
- Uses settings from config.settings.development

**Dependencies:**
- Requires Step 1.1 (packages installed)

**Test:**
```bash
# Check Django can find settings
python manage.py check

# Expected output:
# System check identified no issues (0 silenced).

# If error: "No module named 'apps.users'"
# This is OK - we haven't created apps yet
```

**Common Errors:**
```
❌ Error: SECRET_KEY not found
✅ Fix: Add SECRET_KEY to .env file

❌ Error: redis.exceptions.ConnectionError
✅ Fix: Install and start Redis (we'll do this later)
```

---

### Step 1.3: URL Configuration

**Files to Create:**
1. `config/urls.py`
2. `config/wsgi.py`
3. `config/asgi.py`
4. `config/celery.py`

**What Each File Does:**

**`config/urls.py`:**
- Routes HTTP requests to correct app
- Maps URLs to views
- Example: `/api/auth/` → `apps.users.urls`

**`config/wsgi.py`:**
- Traditional HTTP server interface
- Used for non-WebSocket deployment

**`config/asgi.py`:**
- Async server interface
- Handles both HTTP and WebSocket
- Routes WebSocket to consumers

**`config/celery.py`:**
- Configures Celery task queue
- Sets up periodic tasks (Beat schedule)
- Auto-discovers tasks in all apps

**Dependencies:**
- Requires Step 1.2 (settings configured)

**Test:**
```bash
# Test Django can start
python manage.py runserver

# Visit: http://localhost:8000/
# Should see Django welcome page or error about /api/

# Stop with Ctrl+C
```

---

## PHASE 2: User Authentication (1 hour)

### Step 2.1: User Model

**Files to Create (in order):**
1. `apps/users/__init__.py`
2. `apps/users/apps.py`
3. `apps/users/models.py`

**What Happens:**

**`apps/users/models.py`:**
- Defines custom User model
- Extends Django's AbstractUser
- Adds extra fields (phone, bio)

**Why This Order:**
- models.py MUST be created before serializers
- Everything else depends on the User model

**Dependencies:**
- Requires Phase 1 complete
- Requires Django installed

**Test:**
```bash
# Create migrations
python manage.py makemigrations

# Expected output:
# Migrations for 'users':
#   apps/users/migrations/0001_initial.py
#     - Create model User

# Apply migrations
python manage.py migrate

# Expected output:
# Running migrations:
#   Applying users.0001_initial... OK

# Verify database created
ls -la db.sqlite3

# Should see: db.sqlite3 file exists

# Test in Django shell
python manage.py shell

>>> from apps.users.models import User
>>> User.objects.create_user('test', 'test@test.com', 'pass123')
>>> User.objects.count()
1
>>> exit()
```

**Common Errors:**
```
❌ Error: auth.User conflicts
✅ Fix: Make sure AUTH_USER_MODEL='users.User' in settings

❌ Error: No such table
✅ Fix: Run python manage.py migrate
```

---

### Step 2.2: User Serializers

**Files to Create:**
1. `apps/users/serializers.py`

**What It Does:**
- Converts User model to/from JSON
- Validates registration data
- Handles password hashing

**Dependencies:**
- Requires `apps/users/models.py` (Step 2.1)

**Test:**
```bash
# Test in Django shell
python manage.py shell

>>> from apps.users.serializers import UserRegistrationSerializer
>>> data = {
...     'username': 'newuser',
...     'email': 'new@test.com',
...     'password': 'Test123!',
...     'password_confirm': 'Test123!'
... }
>>> serializer = UserRegistrationSerializer(data=data)
>>> serializer.is_valid()
True
>>> user = serializer.save()
>>> print(user.username)
newuser
>>> exit()
```

---

### Step 2.3: User Views

**Files to Create:**
1. `apps/users/views.py`

**What It Does:**
- Handles HTTP requests for user operations
- UserRegistrationView - POST to create user
- UserProfileView - GET/PUT to view/update profile
- ChangePasswordView - POST to change password

**Dependencies:**
- Requires `apps/users/serializers.py` (Step 2.2)

**Test:**
```bash
# Can't test yet - need URLs
```

---

### Step 2.4: User URLs

**Files to Create:**
1. `apps/users/urls.py`

**What It Does:**
- Maps URLs to views
- `/api/auth/register/` → UserRegistrationView
- `/api/auth/login/` → TokenObtainPairView (JWT)

**Dependencies:**
- Requires `apps/users/views.py` (Step 2.3)
- Requires `config/urls.py` to include these URLs

**Test:**
```bash
# Start server
python manage.py runserver

# In another terminal, test registration:
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "apiuser",
    "email": "api@test.com",
    "password": "Test123!",
    "password_confirm": "Test123!"
  }'

# Expected: JSON response with user data and tokens

# Test login:
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "apiuser",
    "password": "Test123!"
  }'

# Expected: JSON with access and refresh tokens
```

**✅ Checkpoint:** Authentication works! You can register and login.

---

### Step 2.5: User Admin

**Files to Create:**
1. `apps/users/admin.py`

**What It Does:**
- Customizes Django admin interface
- Allows managing users via web UI

**Dependencies:**
- Requires `apps/users/models.py` (Step 2.1)

**Test:**
```bash
# Create superuser
python manage.py createsuperuser

# Username: admin
# Email: admin@test.com
# Password: admin123

# Start server
python manage.py runserver

# Visit: http://localhost:8000/admin/
# Login with admin credentials
# You should see "Users" in the admin panel
# Click "Users" - see list of registered users
```

**✅ Phase 2 Complete:** User authentication fully functional!

---

## PHASE 3: Auction Models & API (1.5 hours)

### Step 3.1: Auction Models

**Files to Create (in order):**
1. `apps/auctions/__init__.py`
2. `apps/auctions/apps.py`
3. `apps/auctions/models.py`

**What Happens:**

**`apps/auctions/models.py`:**
- Defines Auction model (title, price, owner, status, etc.)
- Defines Bid model (auction, bidder, amount)
- Creates relationship: User → Auction, User → Bid

**Why This Order:**
- Models must be created before serializers/views
- Auction depends on User model

**Dependencies:**
- Requires `apps/users/models.py` (Phase 2.1)

**Test:**
```bash
# Create migrations
python manage.py makemigrations

# Expected:
# Migrations for 'auctions':
#   apps/auctions/migrations/0001_initial.py
#     - Create model Auction
#     - Create model Bid

# Apply migrations
python manage.py migrate

# Test in shell
python manage.py shell

>>> from apps.users.models import User
>>> from apps.auctions.models import Auction
>>> from datetime import datetime, timedelta
>>> 
>>> user = User.objects.first()
>>> auction = Auction.objects.create(
...     title="Test Auction",
...     description="Test",
...     starting_price=100,
...     current_price=100,
...     owner=user,
...     end_time=datetime.now() + timedelta(days=1)
... )
>>> print(auction.title)
Test Auction
>>> print(auction.is_active)
True
>>> exit()
```

---

### Step 3.2: Auction Serializers

**Files to Create:**
1. `apps/auctions/serializers.py`

**What It Does:**
- AuctionListSerializer - Light data for list view
- AuctionDetailSerializer - Full data for single auction
- AuctionCreateSerializer - Validation for creating
- BidSerializer - Bid data formatting

**Dependencies:**
- Requires `apps/auctions/models.py` (Step 3.1)
- Requires `apps/users/serializers.py` (for nested user data)

**Test:**
```bash
python manage.py shell

>>> from apps.auctions.serializers import AuctionCreateSerializer
>>> from apps.users.models import User
>>> from datetime import datetime, timedelta
>>> 
>>> user = User.objects.first()
>>> data = {
...     'title': 'Camera',
...     'description': 'Nice camera',
...     'starting_price': '100.00',
...     'end_time': (datetime.now() + timedelta(days=1)).isoformat()
... }
>>> 
>>> # Create fake request context
>>> class FakeRequest:
...     user = user
>>> 
>>> serializer = AuctionCreateSerializer(
...     data=data,
...     context={'request': FakeRequest()}
... )
>>> serializer.is_valid()
True
>>> auction = serializer.save()
>>> print(auction.title)
Camera
>>> exit()
```

---

### Step 3.3: Auction Permissions

**Files to Create:**
1. `apps/auctions/permissions.py`

**What It Does:**
- IsOwnerOrReadOnly - Only owner can edit/delete

**Dependencies:**
- None (standalone)

**Test:**
```bash
# Can't test directly - will test with views
```

---

### Step 3.4: Auction Views

**Files to Create:**
1. `apps/auctions/views.py`

**What It Does:**
- AuctionListCreateAPIView - GET (list) and POST (create)
- AuctionDetailAPIView - GET, PUT, PATCH, DELETE
- AuctionBidsAPIView - GET bids for auction
- MyAuctionsAPIView - GET user's auctions
- MyBidsAPIView - GET user's bids

**Dependencies:**
- Requires `apps/auctions/serializers.py` (Step 3.2)
- Requires `apps/auctions/permissions.py` (Step 3.3)

**Test:**
```bash
# Can't test yet - need URLs
```

---

### Step 3.5: Auction URLs

**Files to Create:**
1. `apps/auctions/urls.py`

**What It Does:**
- Maps URLs to views
- `/api/auctions/` → AuctionListCreateAPIView
- `/api/auctions/1/` → AuctionDetailAPIView

**Dependencies:**
- Requires `apps/auctions/views.py` (Step 3.4)
- Requires `config/urls.py` to include these URLs

**Test:**
```bash
# Get access token first
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"apiuser","password":"Test123!"}' \
  | python -c "import sys, json; print(json.load(sys.stdin)['access'])")

# Create auction
curl -X POST http://localhost:8000/api/auctions/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "title": "Vintage Camera",
    "description": "Great camera",
    "starting_price": "100.00",
    "end_time": "2026-12-31T23:59:59Z"
  }'

# Expected: JSON with created auction

# List auctions
curl http://localhost:8000/api/auctions/

# Expected: Paginated list of auctions

# Get specific auction
curl http://localhost:8000/api/auctions/1/

# Expected: Detailed auction data
```

**✅ Checkpoint:** Auction CRUD works!

---

### Step 3.6: Auction Admin

**Files to Create:**
1. `apps/auctions/admin.py`

**What It Does:**
- Admin interface for managing auctions
- Shows bids inline

**Dependencies:**
- Requires `apps/auctions/models.py` (Step 3.1)

**Test:**
```bash
# Visit: http://localhost:8000/admin/
# Login with superuser
# See "Auctions" section
# Click "Auctions" - see created auctions
# Click "Bids" - see bids (empty for now)
```

**✅ Phase 3 Complete:** Auction API fully functional!

---

## PHASE 4: Celery Background Tasks (45 minutes)

### Step 4.1: Install & Start Redis

**What to Do:**

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install redis-server
sudo systemctl start redis
sudo systemctl enable redis
```

**macOS:**
```bash
brew install redis
brew services start redis
```

**Windows:**
```bash
# Download from: https://github.com/microsoftarchive/redis/releases
# Or use Docker:
docker run -d -p 6379:6379 redis
```

**Test:**
```bash
# Test Redis is running
redis-cli ping

# Expected output: PONG

# If error: Command not found
# Redis not installed or not in PATH
```

**Dependencies:**
- None (external service)

---

### Step 4.2: Auction Signals

**Files to Create:**
1. `apps/auctions/signals.py`

**What It Does:**
- Listens for Bid save events
- Automatically updates Auction.current_price
- Uses Django signals (event-driven programming)

**How It Works:**
```
User places bid → Bid.save() called → post_save signal fires
                                              ↓
                                    update_auction_price() runs
                                              ↓
                                    Auction.current_price updated
```

**Dependencies:**
- Requires `apps/auctions/models.py` (Step 3.1)

**Test:**
```bash
python manage.py shell

>>> from apps.auctions.models import Auction, Bid
>>> from apps.users.models import User
>>> 
>>> auction = Auction.objects.first()
>>> user = User.objects.last()
>>> 
>>> print(f"Current price: {auction.current_price}")
# Current price: 100.00
>>> 
>>> # Create bid
>>> bid = Bid.objects.create(
...     auction=auction,
...     bidder=user,
...     amount=150
... )
>>> 
>>> # Reload auction from database
>>> auction.refresh_from_db()
>>> print(f"New price: {auction.current_price}")
# New price: 150.00
>>> 
>>> # Signal worked! Price updated automatically
>>> exit()
```

**Important:** Update `apps/auctions/apps.py` to import signals:
```python
class AuctionsConfig(AppConfig):
    # ... existing code ...
    
    def ready(self):
        import apps.auctions.signals  # Add this line
```

---

### Step 4.3: Celery Tasks

**Files to Create:**
1. `apps/auctions/tasks.py`

**What It Does:**
- `check_and_close_expired_auctions()` - Runs every minute
- `close_auction(auction_id)` - Closes one auction
- `notify_auction_participants(auction_id)` - Sends notifications

**How It Works:**
```
Celery Beat (scheduler)
    ↓ (every 60 seconds)
check_and_close_expired_auctions()
    ↓ (finds expired auctions)
    ├── close_auction.delay(1)
    ├── close_auction.delay(2)
    └── close_auction.delay(3)
              ↓
        Celery Worker picks up tasks
              ↓
        Determines winner, updates status
              ↓
        notify_auction_participants.delay(1)
              ↓
        Logs notifications
```

**Dependencies:**
- Requires `apps/auctions/models.py` (Step 3.1)
- Requires `config/celery.py` configured
- Requires Redis running (Step 4.1)

**Test:**
```bash
# Terminal 1: Start Celery Worker
celery -A config worker --loglevel=info

# Expected output:
# [tasks]
#   . apps.auctions.tasks.check_and_close_expired_auctions
#   . apps.auctions.tasks.close_auction
#   . apps.auctions.tasks.notify_auction_participants

# Terminal 2: Test task manually
python manage.py shell

>>> from apps.auctions.tasks import check_and_close_expired_auctions
>>> 
>>> # Call synchronously (for testing)
>>> result = check_and_close_expired_auctions()
>>> print(result)
# Queued 0 auctions for closing
>>> 
>>> # Call asynchronously (production way)
>>> task = check_and_close_expired_auctions.delay()
>>> print(task.id)
# <task-id>
>>> exit()

# Check Terminal 1 - should see task execution logs
```

---

### Step 4.4: Start Celery Beat

**What to Do:**
```bash
# Terminal 3: Start Celery Beat (scheduler)
celery -A config beat --loglevel=info

# Expected output:
# LocalTime -> 2026-02-16 15:30:00
# Configuration ->
#     . broker -> redis://localhost:6379/0
#     . loader -> celery.loaders.app.AppLoader
# Scheduler: Running...
```

**What Happens:**
- Every 60 seconds, Beat triggers `check_and_close_expired_auctions`
- Worker picks up the task and executes it
- Expired auctions are automatically closed

**Test:**
```bash
# Create an auction that expires in 2 minutes
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"apiuser","password":"Test123!"}' \
  | python -c "import sys, json; print(json.load(sys.stdin)['access'])")

# Get time 2 minutes from now
END_TIME=$(python -c "from datetime import datetime, timedelta; print((datetime.now() + timedelta(minutes=2)).strftime('%Y-%m-%dT%H:%M:%S') + 'Z')")

curl -X POST http://localhost:8000/api/auctions/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{
    \"title\": \"Expiring Soon\",
    \"description\": \"Will close in 2 minutes\",
    \"starting_price\": \"50.00\",
    \"end_time\": \"$END_TIME\"
  }"

# Wait 2-3 minutes, watch Celery Beat logs
# Should see: "Queued 1 auctions for closing"
# Then in Worker logs: "Auction X closed successfully"

# Verify auction closed
curl http://localhost:8000/api/auctions/ | grep -i "status.*closed"
```

**✅ Phase 4 Complete:** Background tasks working!

---

## PHASE 5: WebSocket Real-time Bidding (1 hour)

### Step 5.1: Bidding Routing

**Files to Create:**
1. `apps/bidding/__init__.py`
2. `apps/bidding/apps.py`
3. `apps/bidding/routing.py`

**What It Does:**
- Maps WebSocket URLs to consumers
- Similar to urls.py but for WebSocket

**Dependencies:**
- None (standalone routing)

**Test:**
```bash
# Can't test yet - need consumer
```

---

### Step 5.2: Bidding Consumer

**Files to Create:**
1. `apps/bidding/consumers.py`

**What It Does:**
- Handles WebSocket connections
- `connect()` - User joins auction
- `receive()` - User sends bid
- `disconnect()` - User leaves
- `bid_placed()` - Broadcast to all users

**How It Works:**
```
User A connects to ws://localhost:8000/ws/auction/1/
    ↓
connect() called → join group "auction_1"
    ↓
User B connects to ws://localhost:8000/ws/auction/1/
    ↓
connect() called → join group "auction_1"
    ↓
User A sends bid
    ↓
receive() → create_bid() → save to DB
    ↓
channel_layer.group_send("auction_1", {...})
    ↓
Both User A and User B receive update via bid_placed()
```

**Dependencies:**
- Requires `apps/auctions/models.py` (Step 3.1)
- Requires `apps/bidding/routing.py` (Step 5.1)
- Requires Redis running (Step 4.1)

**Test:**
```bash
# Install WebSocket client
pip install websockets

# Create test script: test_ws.py
cat > test_ws.py << 'EOF'
import asyncio
import websockets
import json

async def test():
    uri = "ws://localhost:8000/ws/auction/1/"
    
    async with websockets.connect(uri) as ws:
        # Receive initial status
        status = await ws.recv()
        print(f"Status: {status}")
        
        # Send bid
        await ws.send(json.dumps({
            "type": "place_bid",
            "amount": 120.00
        }))
        
        # Receive response
        response = await ws.recv()
        print(f"Response: {response}")

asyncio.run(test())
EOF

# Make sure Django server is running
# python manage.py runserver

# Run test
python test_ws.py

# Expected output:
# Status: {"type":"auction_status","auction":{...}}
# Response: {"type":"bid_placed","bid":{...}}
```

**Important:** Update `config/asgi.py` to import routing:
```python
from apps.bidding.routing import websocket_urlpatterns
```

---

### Step 5.3: Bidding REST API

**Files to Create:**
1. `apps/bidding/views.py`
2. `apps/bidding/urls.py`
3. Update `config/urls.py` to include bidding URLs

**What It Does:**
- PlaceBidAPIView - REST alternative to WebSocket
- BidHistoryAPIView - Get user's bids
- BidStatisticsAPIView - Get user stats
- AuctionBidAnalyticsAPIView - Get auction analytics

**Dependencies:**
- Requires `apps/auctions/models.py` (Step 3.1)

**Test:**
```bash
# Place bid via REST
curl -X POST http://localhost:8000/api/bidding/place-bid/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "auction_id": 1,
    "amount": "130.00"
  }'

# Expected: JSON with bid confirmation

# Get bid history
curl http://localhost:8000/api/bidding/history/ \
  -H "Authorization: Bearer $TOKEN"

# Expected: List of user's bids

# Get statistics
curl http://localhost:8000/api/bidding/statistics/ \
  -H "Authorization: Bearer $TOKEN"

# Expected: Statistics (total bids, average, etc.)

# Get auction analytics
curl http://localhost:8000/api/bidding/auction/1/analytics/

# Expected: Analytics for auction #1
```

**✅ Phase 5 Complete:** Real-time bidding works!

---

## PHASE 6: Testing & Polish (30 minutes)

### Step 6.1: Create Test User & Data

```bash
# Create test script: seed_data.py
python manage.py shell << 'EOF'
from apps.users.models import User
from apps.auctions.models import Auction
from datetime import datetime, timedelta

# Create users
user1 = User.objects.create_user('alice', 'alice@test.com', 'pass123')
user2 = User.objects.create_user('bob', 'bob@test.com', 'pass123')

# Create auctions
for i in range(5):
    Auction.objects.create(
        title=f"Test Auction {i+1}",
        description=f"Description for auction {i+1}",
        starting_price=100 * (i+1),
        current_price=100 * (i+1),
        owner=user1 if i % 2 == 0 else user2,
        end_time=datetime.now() + timedelta(days=i+1)
    )

print("Created 2 users and 5 auctions")
EOF
```

---

### Step 6.2: Full Integration Test

```bash
# Save this as: full_test.sh
cat > full_test.sh << 'EOF'
#!/bin/bash

echo "=== Full Integration Test ==="

BASE_URL="http://localhost:8000/api"

# 1. Register User
echo "\n1. Registering user..."
curl -s -X POST $BASE_URL/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "integrationtest",
    "email": "integration@test.com",
    "password": "Test123!",
    "password_confirm": "Test123!"
  }' | python -m json.tool

# 2. Login
echo "\n2. Logging in..."
TOKEN=$(curl -s -X POST $BASE_URL/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "integrationtest",
    "password": "Test123!"
  }' | python -c "import sys, json; print(json.load(sys.stdin)['access'])")

echo "Token: $TOKEN"

# 3. Create Auction
echo "\n3. Creating auction..."
AUCTION_ID=$(curl -s -X POST $BASE_URL/auctions/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "title": "Integration Test Auction",
    "description": "Testing the API",
    "starting_price": "100.00",
    "end_time": "2026-12-31T23:59:59Z"
  }' | python -c "import sys, json; print(json.load(sys.stdin)['id'])")

echo "Created auction ID: $AUCTION_ID"

# 4. List Auctions
echo "\n4. Listing auctions..."
curl -s $BASE_URL/auctions/ | python -m json.tool | head -20

# 5. Place Bid
echo "\n5. Placing bid..."
curl -s -X POST $BASE_URL/bidding/place-bid/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{
    \"auction_id\": $AUCTION_ID,
    \"amount\": \"150.00\"
  }" | python -m json.tool

# 6. Get Bid History
echo "\n6. Getting bid history..."
curl -s $BASE_URL/bidding/history/ \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# 7. Get Statistics
echo "\n7. Getting statistics..."
curl -s $BASE_URL/bidding/statistics/ \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

echo "\n=== Test Complete ==="
EOF

chmod +x full_test.sh
./full_test.sh
```

---

## Testing Each Step - Summary

### Quick Test Checklist

**Phase 1: Foundation**
- [ ] `python manage.py check` - No errors
- [ ] `python manage.py runserver` - Server starts

**Phase 2: Users**
- [ ] `python manage.py migrate` - Migrations applied
- [ ] Register via API - Returns user + tokens
- [ ] Login via API - Returns tokens
- [ ] Access admin panel - See users

**Phase 3: Auctions**
- [ ] Create auction via API - Returns auction
- [ ] List auctions - Returns list
- [ ] Get auction details - Returns full data
- [ ] Update auction - Returns updated data

**Phase 4: Celery**
- [ ] `redis-cli ping` - Returns PONG
- [ ] Celery worker starts - Shows tasks
- [ ] Celery beat starts - Shows schedule
- [ ] Create expiring auction - Auto-closes

**Phase 5: WebSocket**
- [ ] Connect to WebSocket - Gets status
- [ ] Send bid via WebSocket - Broadcast received
- [ ] Place bid via REST - Returns confirmation

**Phase 6: Full Test**
- [ ] Run full_test.sh - All steps pass

---

## Workflow Diagrams

### Complete Request Flow

```
┌─────────────┐
│   CLIENT    │
└──────┬──────┘
       │
       ├──────────────────────────────────────────┐
       │                                          │
       │ HTTP Request                             │ WebSocket
       │                                          │
       ▼                                          ▼
┌──────────────┐                          ┌──────────────┐
│   urls.py    │                          │  routing.py  │
└──────┬───────┘                          └──────┬───────┘
       │                                          │
       ▼                                          ▼
┌──────────────┐                          ┌──────────────┐
│   views.py   │                          │ consumers.py │
└──────┬───────┘                          └──────┬───────┘
       │                                          │
       ▼                                          │
┌──────────────┐                                  │
│serializers.py│                                  │
└──────┬───────┘                                  │
       │                                          │
       ├──────────────────────────────────────────┤
       │                                          │
       ▼                                          ▼
┌────────────────────────────────────────────────────┐
│                    models.py                       │
│              ┌───────────┐  ┌──────────┐          │
│              │  Auction  │  │   Bid    │          │
│              └─────┬─────┘  └────┬─────┘          │
│                    │             │                 │
│                    └─────┬───────┘                 │
│                          │                         │
│                    ┌─────▼─────┐                   │
│                    │  signals  │                   │
│                    └───────────┘                   │
└────────────────────────┬───────────────────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │   Database   │
                  └──────────────┘
```

### Celery Task Flow

```
┌─────────────┐
│ Celery Beat │ (Scheduler)
└──────┬──────┘
       │ Every 60 seconds
       ▼
┌────────────────────────────────┐
│ check_and_close_expired_auctions │
└──────┬─────────────────────────┘
       │ Query expired auctions
       ▼
┌──────────────┐
│ Redis Queue  │
│  ┌────────┐  │
│  │ Task 1 │  │
│  │ Task 2 │  │
│  │ Task 3 │  │
│  └────────┘  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│Celery Worker │
└──────┬───────┘
       │ Pick up task
       ▼
┌──────────────┐
│close_auction │
└──────┬───────┘
       │ Update database
       ▼
┌──────────────┐
│   Database   │
└──────┬───────┘
       │
       ▼
┌────────────────────────┐
│notify_auction_participants│
└───────────────────────┘
```

### File Creation Order (Visual)

```
1. requirements.txt
        ↓
2. .env, .gitignore
        ↓
3. config/settings/base.py
        ↓
4. config/settings/development.py
        ↓
5. manage.py
        ↓
6. config/urls.py, wsgi.py, asgi.py, celery.py
        ↓
7. apps/users/models.py
        ↓
8. apps/users/serializers.py
        ↓
9. apps/users/views.py
        ↓
10. apps/users/urls.py
        ↓
11. apps/auctions/models.py
        ↓
12. apps/auctions/serializers.py
        ↓
13. apps/auctions/permissions.py
        ↓
14. apps/auctions/views.py
        ↓
15. apps/auctions/urls.py
        ↓
16. apps/auctions/signals.py
        ↓
17. apps/auctions/tasks.py
        ↓
18. apps/bidding/routing.py
        ↓
19. apps/bidding/consumers.py
        ↓
20. apps/bidding/views.py
        ↓
21. apps/bidding/urls.py
```

---

## Common Issues & Solutions

### Issue: Import Error

```
❌ ModuleNotFoundError: No module named 'apps.users'
```

**Solution:**
```bash
# Check INSTALLED_APPS in settings.py
# Make sure it includes:
'apps.users',
'apps.auctions',
'apps.bidding',
```

---

### Issue: Database Error

```
❌ django.db.utils.OperationalError: no such table: users_user
```

**Solution:**
```bash
# Run migrations
python manage.py makemigrations
python manage.py migrate
```

---

### Issue: Redis Connection Error

```
❌ redis.exceptions.ConnectionError: Error 111 connecting to localhost:6379
```

**Solution:**
```bash
# Start Redis
# Ubuntu: sudo systemctl start redis
# macOS: brew services start redis
# Windows: Start redis-server.exe

# Test connection
redis-cli ping
```

---

### Issue: Celery Tasks Not Running

```
❌ Tasks queued but not executing
```

**Solution:**
```bash
# Make sure both are running:
# Terminal 1:
celery -A config worker --loglevel=info

# Terminal 2:
celery -A config beat --loglevel=info
```

---

### Issue: WebSocket Won't Connect

```
❌ WebSocket connection to 'ws://localhost:8000/ws/auction/1/' failed
```

**Solution:**
```bash
# Make sure:
# 1. Django running with: python manage.py runserver
# 2. Redis is running: redis-cli ping
# 3. routing.py imported in asgi.py
# 4. CHANNEL_LAYERS configured in settings.py
```

---

## Final Checklist

Before considering the project complete:

- [ ] All migrations applied
- [ ] Redis running
- [ ] Django server running
- [ ] Celery worker running
- [ ] Celery beat running
- [ ] Can register user
- [ ] Can login
- [ ] Can create auction
- [ ] Can list auctions
- [ ] Can place bid (REST)
- [ ] Can place bid (WebSocket)
- [ ] Auction auto-closes
- [ ] Admin panel works
- [ ] API docs accessible at /api/docs/

---

## Next Steps After Completion

1. **Add Tests** - Write unit tests for each component
2. **Add Validation** - More robust input validation
3. **Add Logging** - Better logging for debugging
4. **Add Monitoring** - Track performance
5. **Deploy** - Follow DEPLOYMENT.md
6. **Add Features** - Categories, images, payments

---

**Congratulations!** You now know exactly how to build and test each part of the project step by step! 🎉
