from datetime import timedelta
from collections import defaultdict
from pathlib import Path
from django.db import transaction
from django.db.models import Max, F
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.http import FileResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from .models import (Board, Column, Task, Sprint, RetroNote, BoardMember, Label,
                     ChecklistItem, Comment, Attachment, Activity, Notification, FlowEvent)
from .serializers import (BoardSerializer, ColumnSerializer, TaskSerializer, SprintSerializer,
                          RetroNoteSerializer, MemberSerializer, LabelSerializer, ChecklistSerializer,
                          CommentSerializer, AttachmentSerializer, ActivitySerializer, NotificationSerializer)
from .access import accessible_boards, role_for, lock_board, record, check_wip, completion_times

def board_ids(request):
    return accessible_boards(request.user).filter(deleted_at__isnull=True).values_list('id', flat=True)

def task_prefetch(queryset):
    return queryset.select_related('column__board', 'assignee', 'sprint').prefetch_related('labels', 'dependencies__column', 'checklist', 'comments__author', 'attachments', 'activities__actor')

def flow(task, delivered=False):
    stage = 'hidden' if task.deleted_at or task.archived else task.column.kind
    FlowEvent.objects.create(board=task.column.board, task=task, stage=stage, delivered=delivered)

@method_decorator(transaction.atomic, name='dispatch')
class BoardViewSet(viewsets.ModelViewSet):
    serializer_class = BoardSerializer
    def get_queryset(self):
        queryset = accessible_boards(self.request.user)
        if self.action not in ['restore', 'trash']:
            queryset = queryset.filter(deleted_at__isnull=True)
        return queryset.select_related('owner').prefetch_related(
            'members__user', 'labels', 'sprints__notes',
            'columns__tasks__labels', 'columns__tasks__dependencies__column',
            'columns__tasks__checklist', 'columns__tasks__comments__author',
            'columns__tasks__attachments', 'columns__tasks__activities__actor',
            'columns__tasks__assignee').order_by('id')
    def perform_create(self, serializer):
        board = serializer.save(owner=self.request.user)
        Column.objects.bulk_create([Column(board=board, title=title, kind=kind, position=i) for i, (title, kind) in enumerate([('A fazer','backlog'),('Em andamento','progress'),('Concluído','done')])])
        record(self.request, board, f'Criou o quadro {board.title}.')
        board.refresh_from_db()
    def perform_update(self, serializer):
        board = lock_board(self.request, serializer.instance, manage=True, restore=True)
        if board.deleted_at:
            raise ValidationError('Restaure o quadro antes de editar.')
        serializer.save()
        record(self.request, board, 'Atualizou as configurações do quadro.')
        serializer.instance.refresh_from_db()
    def perform_destroy(self, instance):
        board = lock_board(self.request, instance, owner=True, restore=True)
        board.deleted_at = timezone.now()
        board.save(update_fields=['deleted_at'])
        record(self.request, board, 'Moveu o quadro para a lixeira.')
    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        board = lock_board(request, self.get_object(), owner=True, restore=True)
        board.deleted_at = None
        board.save(update_fields=['deleted_at'])
        record(request, board, 'Restaurou o quadro.')
        board.refresh_from_db()
        return Response(self.get_serializer(board).data)
    @action(detail=False, methods=['get'])
    def trash(self, request):
        return Response(self.get_serializer(self.get_queryset().filter(owner=request.user, deleted_at__isnull=False), many=True).data)
    @action(detail=True, methods=['get'])
    def activity(self, request, pk=None):
        board = self.get_object()
        return Response(ActivitySerializer(board.activities.select_related('actor')[:100], many=True).data)
    @action(detail=True, methods=['get'])
    def trash_items(self, request, pk=None):
        board = self.get_object()
        if role_for(board, request.user) not in ['owner','admin','editor']:
            raise PermissionDenied()
        return Response({'tasks':TaskSerializer(task_prefetch(Task.objects.filter(column__board=board, deleted_at__isnull=False)), many=True, context=self.get_serializer_context()).data,
                         'columns':ColumnSerializer(board.columns.filter(deleted_at__isnull=False), many=True, context=self.get_serializer_context()).data})
    @action(detail=True, methods=['get'])
    def metrics(self, request, pk=None):
        board = self.get_object()
        tasks = list(Task.objects.filter(column__board=board, deleted_at__isnull=True, archived=False).select_related('column'))
        today = timezone.localdate()
        start = today - timedelta(days=13)
        done = [t for t in tasks if t.completed_at]
        lead = [(t.completed_at-t.created_at).total_seconds()/86400 for t in done]
        cycle = [(t.completed_at-t.started_at).total_seconds()/86400 for t in done if t.started_at]
        events = list(FlowEvent.objects.filter(board=board).order_by('created_at','id'))
        throughput = []
        for i in range(14):
            day = start + timedelta(days=i)
            throughput.append({'date':day.isoformat(), 'count':len({event.task_id for event in events if event.delivered and timezone.localdate(event.created_at)==day})})
        state, index, cumulative = {}, 0, []
        for i in range(14):
            day = start + timedelta(days=i)
            while index < len(events) and timezone.localdate(events[index].created_at) <= day:
                event = events[index]
                state[event.task_id] = event.stage
                index += 1
            cumulative.append({'date':day.isoformat(), **{stage:sum(value==stage for value in state.values()) for stage in ['backlog','progress','done']}})
        columns = [{'id':c.id,'title':c.title,'count':sum(t.column_id==c.id for t in tasks), 'wip_limit':c.wip_limit} for c in board.columns.filter(deleted_at__isnull=True)]
        return Response({'total':len(tasks),'completed':len(done),'blocked':sum(t.blocked for t in tasks),
                         'lead_time_days':round(sum(lead)/len(lead),2) if lead else None,
                         'cycle_time_days':round(sum(cycle)/len(cycle),2) if cycle else None,
                         'throughput':throughput,'cumulative_flow':cumulative,'columns':columns})

@method_decorator(transaction.atomic, name='dispatch')
class EntityViewSet(viewsets.ModelViewSet):
    manage = False
    def entity_board(self, entity):
        if hasattr(entity, 'board'):
            return entity.board
        if hasattr(entity, 'column'):
            return entity.column.board
        if hasattr(entity, 'task'):
            return entity.task.column.board
        return entity.sprint.board
    def create_board(self, data):
        if 'board' in data:
            return data['board']
        if 'column' in data:
            return data['column'].board
        if 'task' in data:
            return data['task'].column.board
        return data['sprint'].board
    def message(self, verb, entity):
        names = {Column:'coluna',Task:'tarefa',Sprint:'sprint',RetroNote:'nota da retrospectiva',BoardMember:'membro',Label:'etiqueta',ChecklistItem:'item de checklist',Comment:'comentário',Attachment:'anexo'}
        title = getattr(entity,'title',getattr(entity,'name',''))
        return f'{verb} {names.get(type(entity),"item")}{": " + title if title else ""}.'
    def perform_create(self, serializer):
        board = lock_board(self.request, self.create_board(serializer.validated_data), manage=self.manage)
        extra = {'author':self.request.user} if serializer.Meta.model is Comment else {}
        if serializer.Meta.model is Attachment:
            extra = {'uploaded_by':self.request.user, 'name':Path(serializer.validated_data['file'].name).name[:200]}
        entity = serializer.save(**extra)
        record(self.request, board, self.message('Adicionou',entity), getattr(entity,'task',None), getattr(entity.task,'assignee',None) if isinstance(entity,Comment) else None)
    def perform_update(self, serializer):
        entity = serializer.instance
        board = lock_board(self.request, self.entity_board(entity), manage=self.manage)
        if isinstance(entity, Comment) and entity.author_id != self.request.user.id and role_for(board,self.request.user) not in ['owner','admin']:
            raise PermissionDenied('Edite apenas seus próprios comentários.')
        serializer.save()
        record(self.request,board,self.message('Atualizou',entity),getattr(entity,'task',None))
    def perform_destroy(self, instance):
        board = lock_board(self.request,self.entity_board(instance),manage=self.manage)
        if isinstance(instance, Comment) and instance.author_id != self.request.user.id and role_for(board,self.request.user) not in ['owner','admin']:
            raise PermissionDenied('Exclua apenas seus próprios comentários.')
        record(self.request,board,self.message('Removeu',instance),getattr(instance,'task',None))
        instance.delete()

class ColumnViewSet(EntityViewSet):
    serializer_class = ColumnSerializer
    manage = True
    def perform_update(self, serializer):
        super().perform_update(serializer)
        # Renaming/reordering columns must not leave stale completion timestamps.
        for task in serializer.instance.tasks.filter(deleted_at__isnull=True):
            completion_times(task)
            task.save(update_fields=['started_at','completed_at'])
    def get_queryset(self):
        qs = Column.objects.filter(board_id__in=board_ids(self.request)).prefetch_related('tasks')
        return qs if self.action=='restore' else qs.filter(deleted_at__isnull=True)
    def perform_destroy(self, instance):
        board = lock_board(self.request,instance.board,manage=True)
        if instance.tasks.filter(deleted_at__isnull=True).exists():
            raise ValidationError('Mova ou exclua as tarefas antes de excluir a coluna.')
        if board.columns.filter(deleted_at__isnull=True).count() <= 1:
            raise ValidationError('O quadro deve manter pelo menos uma coluna.')
        instance.deleted_at = timezone.now()
        instance.save(update_fields=['deleted_at'])
        record(self.request,board,self.message('Excluiu',instance))
    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        instance = self.get_object()
        board = lock_board(request,instance.board,manage=True)
        instance.deleted_at = None
        instance.save(update_fields=['deleted_at'])
        record(request,board,self.message('Restaurou',instance))
        return Response(self.get_serializer(instance).data)

class TaskViewSet(EntityViewSet):
    serializer_class = TaskSerializer
    def get_queryset(self):
        qs = task_prefetch(Task.objects.filter(column__board_id__in=board_ids(self.request)))
        return qs if self.action=='restore' else qs.filter(deleted_at__isnull=True)
    def perform_create(self, serializer):
        data = serializer.validated_data
        board = lock_board(self.request,data['column'].board)
        if not data.get('archived',False):
            check_wip(data['column'])
        position = (data['column'].tasks.aggregate(value=Max('position'))['value'] or 0) + 1
        task = serializer.save(position=position)
        completion_times(task)
        task.save(update_fields=['started_at','completed_at'])
        flow(task, delivered=task.completed_at is not None)
        record(self.request,board,self.message('Criou',task),task,task.assignee)
    def perform_update(self, serializer):
        task = serializer.instance
        board = lock_board(self.request,task.column.board)
        if not serializer.validated_data.get('archived',task.archived):
            check_wip(serializer.validated_data.get('column',task.column),task)
        changes = []
        for key,value in serializer.validated_data.items():
            if key in ['labels','dependencies']:
                if set(v.id for v in value)!=set(getattr(task,key).values_list('id',flat=True)):
                    changes.append(key)
            elif getattr(task,key)!=value:
                changes.append(key)
        old_assignee = task.assignee_id
        old_column = task.column_id
        old_completed = task.completed_at
        serializer.save()
        if old_column != task.column_id:
            task.position = (task.column.tasks.exclude(pk=task.pk).aggregate(value=Max('position'))['value'] or 0)+1
        completion_times(task)
        task.save(update_fields=['position','started_at','completed_at'])
        flow(task, delivered=old_completed is None and task.completed_at is not None)
        labels={'title':'título','description':'descrição','priority':'prioridade','due_date':'prazo','column':'coluna','sprint':'sprint','assignee':'responsável','labels':'etiquetas','dependencies':'dependências','blocked':'bloqueio','blocked_reason':'motivo do bloqueio','archived':'arquivamento'}
        message=f'Atualizou {task.title}: {", ".join(labels.get(c,c) for c in changes) or "dados"}.'
        record(self.request,board,message,task,task.assignee if old_assignee!=task.assignee_id else None)
    def perform_destroy(self, instance):
        board = lock_board(self.request,instance.column.board)
        if Task.objects.filter(dependencies=instance,deleted_at__isnull=True).exists():
            raise ValidationError('Remova as dependências desta tarefa antes de excluir.')
        instance.deleted_at = timezone.now()
        instance.save(update_fields=['deleted_at'])
        flow(instance)
        record(self.request,board,self.message('Moveu para a lixeira a',instance),instance)
    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        task=self.get_object()
        board=lock_board(request,task.column.board)
        if not task.archived:
            check_wip(task.column,task)
        task.deleted_at=None
        task.save(update_fields=['deleted_at'])
        flow(task)
        record(request,board,self.message('Restaurou',task),task)
        return Response(self.get_serializer(task).data)
    @action(detail=True, methods=['post'])
    def move(self, request, pk=None):
        task=self.get_object()
        board=lock_board(request,task.column.board)
        serializer=self.get_serializer(task,data={'column':request.data.get('column')},partial=True)
        serializer.is_valid(raise_exception=True)
        target=serializer.validated_data['column']
        check_wip(target,task)
        before=request.data.get('before')
        siblings=list(target.tasks.filter(deleted_at__isnull=True,archived=False).exclude(pk=task.pk).order_by('position','id'))
        if before is not None:
            matching=[i for i,t in enumerate(siblings) if t.id==before]
            if not matching:
                raise ValidationError('Posição de destino inválida.')
            index=matching[0]
        else:
            index=len(siblings)
        old_completed=task.completed_at
        task.column=target
        completion_times(task)
        siblings.insert(index,task)
        for i,item in enumerate(siblings):
            item.position=i
        Task.objects.bulk_update(siblings,['column','position','started_at','completed_at'])
        flow(task, delivered=old_completed is None and task.completed_at is not None)
        record(request,board,f'Moveu {task.title} para {target.title}, posição {index+1}.',task)
        return Response(self.get_serializer(task).data)

class SprintViewSet(EntityViewSet):
    serializer_class = SprintSerializer
    def get_queryset(self):
        return Sprint.objects.filter(board_id__in=board_ids(self.request)).prefetch_related('notes')
    def perform_destroy(self, instance):
        if instance.status!='planned':
            raise ValidationError('Somente sprints planejadas podem ser excluídas.')
        super().perform_destroy(instance)
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        sprint=self.get_object()
        board=lock_board(request,sprint.board)
        sprint.refresh_from_db()
        if sprint.status!='planned' or Sprint.objects.filter(board=board,status='active').exists():
            raise ValidationError('A sprint deve estar planejada e o quadro não pode ter outra sprint ativa.')
        sprint.status='active'
        sprint.save(update_fields=['status'])
        record(request,board,f'Iniciou a sprint {sprint.title}.')
        return Response(self.get_serializer(sprint).data)
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        sprint=self.get_object()
        board=lock_board(request,sprint.board)
        sprint.refresh_from_db()
        if sprint.status!='active':
            raise ValidationError('Somente uma sprint em andamento pode ser encerrada.')
        tasks=sprint.tasks.filter(deleted_at__isnull=True,archived=False)
        sprint.total_at_close=tasks.count()
        sprint.completed_at_close=tasks.filter(column__kind='done').count()
        sprint.tasks.exclude(column__kind='done').update(sprint=None)
        sprint.status='completed'
        sprint.closed_at=timezone.now()
        sprint.save(update_fields=['total_at_close','completed_at_close','status','closed_at'])
        record(request,board,f'Encerrou a sprint {sprint.title}: {sprint.completed_at_close}/{sprint.total_at_close} tarefas concluídas.')
        return Response(self.get_serializer(sprint).data)

class RetroNoteViewSet(EntityViewSet):
    serializer_class=RetroNoteSerializer
    def get_queryset(self):
        return RetroNote.objects.filter(sprint__board_id__in=board_ids(self.request)).select_related('sprint__board')

class MemberViewSet(EntityViewSet):
    serializer_class=MemberSerializer
    manage=True
    def get_queryset(self):
        return BoardMember.objects.filter(board_id__in=board_ids(self.request)).select_related('board','user')
    def perform_create(self, serializer):
        board=self.create_board(serializer.validated_data)
        if serializer.validated_data['role']=='admin' and role_for(board,self.request.user)!='owner':
            raise PermissionDenied('Somente o dono pode nomear administradores.')
        super().perform_create(serializer)
        record(self.request,board,f'Adicionou {serializer.instance.user.username} ao quadro.',notify_user=serializer.instance.user)
    def protect_admin(self, member, role=None):
        if (member.role=='admin' or role=='admin') and role_for(member.board,self.request.user)!='owner':
            raise PermissionDenied('Somente o dono pode gerenciar administradores.')
    def perform_update(self, serializer):
        self.protect_admin(serializer.instance,serializer.validated_data.get('role'))
        super().perform_update(serializer)
    def perform_destroy(self, instance):
        self.protect_admin(instance)
        board=instance.board
        user=instance.user
        super().perform_destroy(instance)
        Task.objects.filter(column__board=board,assignee=user).update(assignee=None)

class LabelViewSet(EntityViewSet):
    serializer_class=LabelSerializer
    manage=True
    def get_queryset(self):
        return Label.objects.filter(board_id__in=board_ids(self.request))

class ChecklistViewSet(EntityViewSet):
    serializer_class=ChecklistSerializer
    def get_queryset(self):
        return ChecklistItem.objects.filter(task__column__board_id__in=board_ids(self.request),task__deleted_at__isnull=True)

class CommentViewSet(EntityViewSet):
    serializer_class=CommentSerializer
    def get_queryset(self):
        return Comment.objects.filter(task__column__board_id__in=board_ids(self.request),task__deleted_at__isnull=True).select_related('author')

class AttachmentViewSet(EntityViewSet):
    serializer_class=AttachmentSerializer
    http_method_names=['get','post','delete','head','options']
    def get_queryset(self):
        return Attachment.objects.filter(task__column__board_id__in=board_ids(self.request),task__deleted_at__isnull=True)
    @action(detail=True,methods=['get'])
    def download(self,request,pk=None):
        attachment=self.get_object()
        return FileResponse(attachment.file.open('rb'),as_attachment=True,filename=attachment.name,content_type='application/octet-stream')

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class=NotificationSerializer
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user,board_id__in=board_ids(self.request))
    @action(detail=False,methods=['get'])
    def deadlines(self,request):
        today=timezone.localdate()
        tasks=Task.objects.filter(column__board_id__in=board_ids(request),deleted_at__isnull=True,archived=False,due_date__lte=today+timedelta(days=2)).exclude(column__kind='done').select_related('column__board')
        return Response([{'id':t.id,'board':t.column.board_id,'title':t.title,'due_date':t.due_date,'overdue':t.due_date<today} for t in tasks])
    @action(detail=False,methods=['post'])
    def read_all(self,request):
        self.get_queryset().update(read=True)
        return Response({'ok':True})
