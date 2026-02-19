from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('', views.AuctionListCreateAPIView.as_view(), name='auction_list_create'),
    path('<int:pk>/', views.AuctionDetailAPIView.as_view(), name='auction_list_create'),
    path('<int:pk>/bids/', views.AuctionBidsAPIView.as_view(), name='auction_bid_list'),
    path('my-auctions/', views.MyAuctionsAPIView.as_view(), name='my_auctions'),
    path('my-bids/', views.MyBidsAPIView.as_view(), name='my_bids'),
]