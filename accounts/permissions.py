from rest_framework import permissions


class IsNotObserver(permissions.BasePermission):
    """Kuzatuvchi (read-only) yozish huquqiga ega emas."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        return not request.user.is_read_only()
