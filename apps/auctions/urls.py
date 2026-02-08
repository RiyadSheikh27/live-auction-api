from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('', views.AuctionListCreateAPIView.as_view(), name='auction_list_create'),
]