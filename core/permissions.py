from rest_framework import permissions


class AccessForInstructor(permissions.BasePermission):
    """Enable access for Instructors only"""
    def has_permission(self, request, view):
        return request.user.is_instructor()


class AccessForParent(permissions.BasePermission):
    """Enable access for Parents only"""
    def has_permission(self, request, view):
        return request.user.is_parent()


class AccessForStudent(permissions.BasePermission):
    """Enable access for Students only"""
    def has_permission(self, request, view):
        return request.user.is_student()


class AccessForParentOrStudent(permissions.BasePermission):
    """Enable access for Parents or Students only"""
    def has_permission(self, request, view):
        return request.user.is_parent() or request.user.is_student()
