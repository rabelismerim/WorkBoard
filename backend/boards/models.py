from django.conf import settings
from django.db import models

class Board(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='boards')
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True, max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    archived = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    revision = models.PositiveIntegerField(default=1)

class BoardMember(models.Model):
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=[('viewer', 'Leitor'), ('editor', 'Editor'), ('admin', 'Administrador')], default='editor')

    class Meta:
        constraints = [models.UniqueConstraint(fields=['board', 'user'], name='unique_board_member')]

class Label(models.Model):
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='labels')
    title = models.CharField(max_length=40)
    color = models.CharField(max_length=7, default='#3b82f6')

    class Meta:
        ordering = ['title', 'id']
        constraints = [models.UniqueConstraint(fields=['board', 'title'], name='unique_board_label')]

class Column(models.Model):
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='columns')
    title = models.CharField(max_length=80)
    position = models.PositiveIntegerField(default=0)
    wip_limit = models.PositiveIntegerField(null=True, blank=True)
    kind = models.CharField(max_length=12, choices=[('backlog', 'A fazer'), ('progress', 'Em execução'), ('done', 'Concluída')], default='backlog')
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['position', 'id']

class Task(models.Model):
    sprint = models.ForeignKey('Sprint', null=True, blank=True, on_delete=models.SET_NULL, related_name='tasks')
    column = models.ForeignKey(Column, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, max_length=5000)
    priority = models.CharField(max_length=10, choices=[('low', 'Baixa'), ('medium', 'Média'), ('high', 'Alta')], default='medium')
    due_date = models.DateField(null=True, blank=True)
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_tasks')
    labels = models.ManyToManyField(Label, blank=True)
    dependencies = models.ManyToManyField('self', symmetrical=False, blank=True)
    blocked = models.BooleanField(default=False)
    blocked_reason = models.CharField(max_length=500, blank=True)
    archived = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['position', 'id']

class Sprint(models.Model):
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='sprints')
    title = models.CharField(max_length=120)
    goal = models.TextField(blank=True, max_length=2000)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=12, choices=[('planned', 'Planejada'), ('active', 'Em andamento'), ('completed', 'Encerrada')], default='planned')
    closed_at = models.DateTimeField(null=True, blank=True)
    total_at_close = models.PositiveIntegerField(default=0)
    completed_at_close = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-start_date', '-id']
        constraints = [models.UniqueConstraint(fields=['board'], condition=models.Q(status='active'), name='one_active_sprint_per_board')]

class RetroNote(models.Model):
    sprint = models.ForeignKey(Sprint, on_delete=models.CASCADE, related_name='notes')
    category = models.CharField(max_length=12, choices=[('positive', 'Foi bem'), ('improve', 'Pode melhorar'), ('action', 'Ações')])
    content = models.TextField(max_length=2000)
    done = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']

class ChecklistItem(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='checklist')
    title = models.CharField(max_length=200)
    done = models.BooleanField(default=False)

    class Meta:
        ordering = ['id']

class Comment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField(max_length=3000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']

class Attachment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='attachments')
    name = models.CharField(max_length=200)
    file = models.FileField(upload_to='attachments/%Y/%m/')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

class Activity(models.Model):
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='activities')
    task = models.ForeignKey(Task, null=True, blank=True, on_delete=models.SET_NULL, related_name='activities')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    message = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']

class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    board = models.ForeignKey(Board, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, null=True, blank=True, on_delete=models.SET_NULL)
    message = models.CharField(max_length=500)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']

class FlowEvent(models.Model):
    board = models.ForeignKey(Board, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    stage = models.CharField(max_length=12)
    delivered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']
