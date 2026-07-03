from rest_framework.permissions import BasePermission, SAFE_METHODS, IsAdminUser
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
    """Only the submission owner, assigned grader, or staff can view it."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        #Admin
        if request.user.is_superuser:
            return True
            
        #Owner (Student)
        if obj.user == request.user:
            return True
        
        # Staff with view permission
        if request.user.is_staff and request.user.has_perm("exams.view_submission"):
            return True
            
        # Assigned Grader
        return obj.graders.filter(pk=request.user.pk).exists()


class CanGradeSubmission(BasePermission):
    """Only staff/superuser or the assigned grader can grade."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (
            request.user.is_staff or request.user.has_perm("exams.change_submission")
        ))

    def has_object_permission(self, request, view, obj):
        # Admin
        if request.user.is_superuser:
            return True

        # Staff with change permission
        if request.user.is_staff and request.user.has_perm("exams.change_submission"):
            return True
        
        # Assigned Grader
        return obj.graders.filter(pk=request.user.pk).exists()
    