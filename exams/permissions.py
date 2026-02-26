from rest_framework.permissions import BasePermission, SAFE_METHODS

class CanDesigne(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user.is_authenticated
        else:
            return request.user.has_perm("exams.add_exammodl")