from rest_framework import permissions


class IsAgentOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow agents to edit listings.
    """

    def has_permission(self, request, view):
        # Allow read permissions for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to agents
        return request.user and request.user.is_agent

    def has_object_permission(self, request, view, obj):
        # Allow read permissions for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the agent who created the listing
        return obj.created_by == request.user