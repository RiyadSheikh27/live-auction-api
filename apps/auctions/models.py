from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone

class Auction(models.Model):
    """
    Auction Model
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    starting_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    current_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    reserve_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Minimum price for sale (optional)"
    )
    
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_auctions'
    )
    winner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='won_auctions'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'auctions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'end_time']),
            models.Index(fields=['owner']),
        ]

    def __str__(self):
        return f"{self.title} - {self.status}"
    
    @property
    def is_active(self):
        """Check if auction is currently active"""
        return (
            self.status == 'active' and 
            self.start_time <= timezone.now() <= self.end_time
        )
    
    @property
    def total_bids(self):
        """Get total number of bids"""
        return self.bids.count()