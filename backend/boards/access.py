from django.db.models import Q, F
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, APIException, ValidationError
from .models import Board, BoardMember, Activity, Notification

def accessible_boards(user):
    return Board.objects.filter(Q(owner=user) | Q(members__user=user)).distinct()

def role_for(board, user):
    if board.owner_id == user.id:
        return 'owner'
    return BoardMember.objects.filter(board=board, user=user).values_list('role', flat=True).first()

class Conflict(APIException):
    status_code = 409
    default_detail = 'O quadro foi alterado por outra pessoa. Atualize os dados antes de tentar novamente.'

class PreconditionRequired(APIException):
    status_code = 428
    default_detail = 'Informe a revisão do quadro no cabeçalho If-Match.'

def lock_board(request, board, manage=False, owner=False, restore=False):
    board = Board.objects.select_for_update().get(pk=board.pk)
    role = role_for(board, request.user)
    if role not in (['owner'] if owner else ['owner', 'admin'] if manage else ['owner', 'admin', 'editor']):
        raise PermissionDenied('Seu perfil não permite esta ação.')
    if board.deleted_at and not restore:
        raise ValidationError('Restaure o quadro antes de alterar seus dados.')
    if board.archived and not restore:
        raise ValidationError('Desarquive o quadro antes de alterar seus dados.')
    revision = request.headers.get('If-Match')
    if revision is None:
        raise PreconditionRequired()
    if revision.strip('"') != str(board.revision):
        raise Conflict()
    return board

def record(request, board, message, task=None, notify_user=None):
    Board.objects.filter(pk=board.pk).update(revision=F('revision') + 1)
    Activity.objects.create(board=board, actor=request.user, task=task, message=message[:500])
    if notify_user and notify_user.id != request.user.id:
        Notification.objects.create(user=notify_user, board=board, task=task, message=message[:500])
    recipients = {board.owner_id, request.user.id, *board.members.values_list('user_id', flat=True)}
    def broadcast():
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        layer = get_channel_layer()
        for user_id in recipients:
            async_to_sync(layer.group_send)(f'user_{user_id}', {'type':'workspace.changed'})
    transaction.on_commit(broadcast, robust=True)

def check_wip(column, task=None):
    if column.deleted_at:
        raise ValidationError('Coluna indisponível.')
    if column.wip_limit:
        count = column.tasks.filter(deleted_at__isnull=True, archived=False)
        if task:
            count = count.exclude(pk=task.pk)
        if count.count() >= column.wip_limit:
            raise ValidationError(f'Limite WIP de {column.wip_limit} tarefas atingido em {column.title}.')

def completion_times(task):
    if task.column.kind in ['progress', 'done'] and task.started_at is None:
        task.started_at = timezone.now()
    if task.column.kind == 'done':
        if task.completed_at is None:
            task.completed_at = timezone.now()
    else:
        task.completed_at = None
