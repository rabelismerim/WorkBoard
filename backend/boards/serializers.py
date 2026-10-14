import re
from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import (Board, Column, Task, Sprint, RetroNote, BoardMember, Label,
                     ChecklistItem, Comment, Attachment, Activity, Notification)
from .access import accessible_boards, role_for

def check_board(serializer, board):
    if not accessible_boards(serializer.context['request'].user).filter(pk=board.pk, deleted_at__isnull=True).exists():
        raise serializers.ValidationError('Quadro indisponível.')
    return board

class ActivitySerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source='actor.username', read_only=True, default='Conta removida')
    class Meta:
        model = Activity
        fields = ['id', 'task', 'actor_name', 'message', 'created_at']

class ChecklistSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChecklistItem
        fields = ['id', 'task', 'title', 'done']
    def validate_task(self, task):
        check_board(self, task.column.board)
        if task.deleted_at:
            raise serializers.ValidationError('Tarefa indisponível.')
        if self.instance and self.instance.task_id != task.id:
            raise serializers.ValidationError('Não é possível transferir o item.')
        return task

class CommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.username', read_only=True)
    class Meta:
        model = Comment
        fields = ['id', 'task', 'author_name', 'content', 'created_at']
        read_only_fields = ['author_name', 'created_at']
    def validate_task(self, task):
        check_board(self, task.column.board)
        if task.deleted_at:
            raise serializers.ValidationError('Tarefa indisponível.')
        if self.instance and self.instance.task_id != task.id:
            raise serializers.ValidationError('Não é possível transferir o comentário.')
        return task

class AttachmentSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()
    class Meta:
        model = Attachment
        fields = ['id', 'task', 'name', 'file', 'created_at', 'download_url']
        extra_kwargs = {'file': {'write_only': True}, 'name': {'read_only': True}}
    def get_download_url(self, obj):
        return f'/api/attachments/{obj.id}/download/'
    def validate_task(self, task):
        check_board(self, task.column.board)
        if task.deleted_at:
            raise serializers.ValidationError('Tarefa indisponível.')
        return task
    def validate_file(self, file):
        if file.size > 10 * 1024 * 1024:
            raise serializers.ValidationError('O limite por arquivo é 10 MB.')
        return file

class LabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Label
        fields = ['id', 'board', 'title', 'color']
    def validate_board(self, board):
        check_board(self, board)
        if self.instance and self.instance.board_id != board.id:
            raise serializers.ValidationError('Não é possível transferir a etiqueta.')
        return board
    def validate_color(self, color):
        if not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
            raise serializers.ValidationError('Informe uma cor hexadecimal válida.')
        return color

class TaskSerializer(serializers.ModelSerializer):
    checklist = ChecklistSerializer(many=True, read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)
    activities = serializers.SerializerMethodField()
    assignee_name = serializers.CharField(source='assignee.username', read_only=True, default=None)
    class Meta:
        model = Task
        fields = ['id', 'column', 'sprint', 'title', 'description', 'priority', 'due_date', 'position',
                  'assignee', 'assignee_name', 'labels', 'dependencies', 'blocked', 'blocked_reason',
                  'archived', 'deleted_at', 'started_at', 'completed_at', 'checklist', 'comments',
                  'attachments', 'activities', 'created_at', 'updated_at']
        read_only_fields = ['position', 'deleted_at', 'started_at', 'completed_at', 'created_at', 'updated_at']
    def get_activities(self, obj):
        return ActivitySerializer(list(obj.activities.all())[:30], many=True).data
    def validate_column(self, column):
        check_board(self, column.board)
        if column.deleted_at:
            raise serializers.ValidationError('Coluna indisponível.')
        if self.instance and column.board_id != self.instance.column.board_id:
            raise serializers.ValidationError('Não é possível transferir tarefas entre quadros.')
        return column
    def validate(self, attrs):
        column = attrs.get('column', getattr(self.instance, 'column', None))
        board = column.board
        sprint = attrs.get('sprint', getattr(self.instance, 'sprint', None))
        if sprint:
            if sprint.board_id != board.id:
                raise serializers.ValidationError('A sprint deve pertencer ao mesmo quadro da tarefa.')
            if 'sprint' in attrs and sprint.status == 'completed' and (not self.instance or self.instance.sprint_id != sprint.id):
                raise serializers.ValidationError('Não é possível adicionar tarefas a uma sprint encerrada.')
        assignee = attrs.get('assignee', getattr(self.instance, 'assignee', None))
        if assignee and assignee.id != board.owner_id and not board.members.filter(user=assignee).exists():
            raise serializers.ValidationError('O responsável deve ser membro do quadro.')
        for label in attrs.get('labels', []):
            if label.board_id != board.id:
                raise serializers.ValidationError('Etiqueta de outro quadro.')
        dependencies = attrs.get('dependencies', list(self.instance.dependencies.all()) if self.instance else [])
        for dependency in dependencies:
            if dependency.column.board_id != board.id or dependency.deleted_at or (self.instance and dependency.id == self.instance.id):
                raise serializers.ValidationError('Dependência inválida.')
            if self.instance:
                visited, pending = set(), [dependency.id]
                while pending:
                    pk = pending.pop()
                    if pk == self.instance.id:
                        raise serializers.ValidationError('As dependências não podem formar um ciclo.')
                    if pk not in visited:
                        visited.add(pk)
                        pending.extend(Task.objects.get(pk=pk).dependencies.values_list('id', flat=True))
        blocked = attrs.get('blocked', getattr(self.instance, 'blocked', False))
        reason = attrs.get('blocked_reason', getattr(self.instance, 'blocked_reason', ''))
        if blocked and not reason.strip():
            raise serializers.ValidationError('Informe o motivo do bloqueio.')
        if column.kind == 'done' and (blocked or any(d.column.kind != 'done' for d in dependencies)):
            raise serializers.ValidationError('Resolva o bloqueio e conclua as dependências antes de finalizar a tarefa.')
        return attrs

class ColumnSerializer(serializers.ModelSerializer):
    tasks = serializers.SerializerMethodField()
    class Meta:
        model = Column
        fields = ['id', 'board', 'title', 'position', 'kind', 'wip_limit', 'tasks', 'deleted_at']
        read_only_fields = ['deleted_at']
    def get_tasks(self, obj):
        return TaskSerializer([t for t in obj.tasks.all() if t.deleted_at is None], many=True, context=self.context).data
    def validate_board(self, board):
        check_board(self, board)
        if self.instance and self.instance.board_id != board.id:
            raise serializers.ValidationError('Não é possível transferir uma coluna para outro quadro.')
        return board
    def validate_wip_limit(self, value):
        if value == 0:
            raise serializers.ValidationError('Use um limite positivo ou deixe vazio.')
        if value and self.instance and self.instance.tasks.filter(deleted_at__isnull=True, archived=False).count() > value:
            raise serializers.ValidationError('O limite não pode ser menor que a quantidade atual de tarefas.')
        return value
    def validate_kind(self, value):
        if self.instance and self.instance.kind != value and self.instance.tasks.filter(deleted_at__isnull=True).exists():
            raise serializers.ValidationError('Mova as tarefas antes de alterar o tipo da coluna.')
        return value

class RetroNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = RetroNote
        fields = ['id', 'sprint', 'category', 'content', 'done', 'created_at']
        read_only_fields = ['created_at']
    def validate(self, attrs):
        sprint = attrs.get('sprint', getattr(self.instance, 'sprint', None))
        check_board(self, sprint.board)
        if self.instance and sprint.id != self.instance.sprint_id:
            raise serializers.ValidationError('Não é possível transferir a nota.')
        if sprint.status == 'planned':
            raise serializers.ValidationError('Inicie a sprint antes de registrar a retrospectiva.')
        if attrs.get('done', getattr(self.instance, 'done', False)) and attrs.get('category', getattr(self.instance, 'category', None)) != 'action':
            raise serializers.ValidationError('Apenas ações podem ser marcadas como concluídas.')
        return attrs

class SprintSerializer(serializers.ModelSerializer):
    notes = RetroNoteSerializer(many=True, read_only=True)
    class Meta:
        model = Sprint
        fields = ['id', 'board', 'title', 'goal', 'start_date', 'end_date', 'status', 'closed_at', 'total_at_close', 'completed_at_close', 'notes']
        read_only_fields = ['status', 'closed_at', 'total_at_close', 'completed_at_close']
    def validate_board(self, board):
        check_board(self, board)
        if self.instance and self.instance.board_id != board.id:
            raise serializers.ValidationError('Não é possível transferir uma sprint entre quadros.')
        return board
    def validate(self, attrs):
        if self.instance and self.instance.status != 'planned':
            raise serializers.ValidationError('Somente sprints planejadas podem ser editadas.')
        start = attrs.get('start_date', getattr(self.instance, 'start_date', None))
        end = attrs.get('end_date', getattr(self.instance, 'end_date', None))
        if start and end and end < start:
            raise serializers.ValidationError('A data final deve ser igual ou posterior ao início.')
        return attrs

class MemberSerializer(serializers.ModelSerializer):
    username = serializers.CharField(write_only=True, required=False)
    user_name = serializers.CharField(source='user.username', read_only=True)
    user = serializers.IntegerField(source='user_id', read_only=True)
    class Meta:
        model = BoardMember
        fields = ['id', 'board', 'user', 'username', 'user_name', 'role']
    def validate(self, attrs):
        board = attrs.get('board', getattr(self.instance, 'board', None))
        check_board(self, board)
        if self.instance and board.id != self.instance.board_id:
            raise serializers.ValidationError('Não é possível transferir membros.')
        username = attrs.pop('username', None)
        if self.instance and username is not None:
            raise serializers.ValidationError('Edite apenas o perfil do membro.')
        if not self.instance:
            user = get_user_model().objects.filter(username=username).first()
            if not user or user.id == board.owner_id or board.members.filter(user=user).exists():
                raise serializers.ValidationError('Usuário indisponível ou já faz parte do quadro.')
            attrs['user'] = user
        return attrs

class BoardSerializer(serializers.ModelSerializer):
    sprints = SprintSerializer(many=True, read_only=True)
    columns = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()
    labels = LabelSerializer(many=True, read_only=True)
    role = serializers.SerializerMethodField()
    class Meta:
        model = Board
        fields = ['id', 'title', 'description', 'created_at', 'columns', 'sprints', 'members', 'labels', 'role', 'archived', 'deleted_at', 'revision']
        read_only_fields = ['created_at', 'deleted_at', 'revision']
    def get_columns(self, obj):
        return ColumnSerializer([c for c in obj.columns.all() if c.deleted_at is None], many=True, context=self.context).data
    def get_members(self, obj):
        return [{'id':None, 'user':obj.owner_id, 'user_name':obj.owner.username, 'role':'owner'}] + MemberSerializer(obj.members.all(), many=True).data
    def get_role(self, obj):
        return role_for(obj, self.context['request'].user)

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'board', 'task', 'message', 'read', 'created_at']
        read_only_fields = ['board', 'task', 'message', 'created_at']
