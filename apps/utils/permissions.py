"""
Custom Permissions
"""

from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission:
    - Read permissions (GET, HEAD, OPTIONS) allowed to anyone
    - Write permissions (PUT, PATCH, DELETE) only to owner
    """
    
    def has_object_permission(self, request, view, obj):
        """Read permissions allowed to any request (GET, HEAD, OPTIONS)"""
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only allowed to the owner
        return obj.owner == request.user