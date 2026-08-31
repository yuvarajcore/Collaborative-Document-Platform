from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views import (
    UserViewSet, WorkspaceViewSet, DocumentViewSet,
    CommentViewSet, TagViewSet, AuditLogViewSet,
)

router = DefaultRouter()
router.register('users', UserViewSet, basename='users')
router.register('workspaces', WorkspaceViewSet, basename='workspaces')
router.register('documents', DocumentViewSet, basename='documents')
router.register('comments', CommentViewSet, basename='comments')
router.register('tags', TagViewSet, basename='tags')
router.register('audit-logs', AuditLogViewSet, basename='audit-logs')

urlpatterns = [path('api/', include(router.urls))]
