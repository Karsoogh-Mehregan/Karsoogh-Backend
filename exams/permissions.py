from rest_framework.permissions import BasePermission, SAFE_METHODS

class CanDesigne(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user.is_authenticated
        else:
            return request.user.has_perm("exams.add_exammodel")

class CanViewQuestion(BasePermission):
    def has_permission(self, request, view):
        return request.user.has_perm("exams.view_questionmodel") or request.user.is_superuser


class CanViewSubmission(BasePermission):
    """Only the submission owner or staff can view it."""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user or request.user.is_staff


class CanGradeSubmission(BasePermission):
    """Only staff/superuser or users with change_submission permission can grade."""

    def has_permission(self, request, view):
        return request.user and (request.user.is_staff or request.user.has_perm("exams.change_submission"))