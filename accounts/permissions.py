from rest_framework import permissions


class IsNotObserver(permissions.BasePermission):
    """Kuzatuvchi (read-only) yozish huquqiga ega emas."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        if getattr(request.user, 'is_superuser', False):
            return True
        return not request.user.is_read_only()


class IsAdminRole(permissions.BasePermission):
    """Faqat admin roli yoki Django superuser."""

    def has_permission(self, request, view):
        u = request.user
        if not u or not u.is_authenticated:
            return False
        return bool(getattr(u, 'is_superuser', False) or getattr(u, 'role', None) == 'admin')
