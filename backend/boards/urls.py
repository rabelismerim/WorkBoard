from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import session
from .account_views import account, recovery, reset_password
from .work_views import (BoardViewSet, ColumnViewSet, TaskViewSet, SprintViewSet, RetroNoteViewSet,
                         MemberViewSet, LabelViewSet, ChecklistViewSet, CommentViewSet, AttachmentViewSet, NotificationViewSet)
router = DefaultRouter()
router.register('boards', BoardViewSet, basename='board')
router.register('columns', ColumnViewSet, basename='column')
router.register('tasks', TaskViewSet, basename='task')
router.register('sprints', SprintViewSet, basename='sprint')
router.register('retro-notes', RetroNoteViewSet, basename='retro-note')
router.register('members', MemberViewSet, basename='member')
router.register('labels', LabelViewSet, basename='label')
router.register('checklist', ChecklistViewSet, basename='checklist')
router.register('comments', CommentViewSet, basename='comment')
router.register('attachments', AttachmentViewSet, basename='attachment')
router.register('notifications', NotificationViewSet, basename='notification')
urlpatterns = [path('session/', session),path('account/',account),path('password/recovery/',recovery),path('password/reset/',reset_password), path('', include(router.urls))]
