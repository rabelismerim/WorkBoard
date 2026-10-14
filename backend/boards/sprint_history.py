from django.utils import timezone
from .models import SprintEntry

def snapshot(task):
    return {'id':task.pk,'title':task.title,'description':task.description,'priority':task.priority,
            'column':task.column.title,'kind':task.column.kind,'assignee':task.assignee.username if task.assignee else None,
            'archived':task.archived,'deleted':task.deleted_at is not None,'completed':task.column.kind=='done',
            'due_date':task.due_date.isoformat() if task.due_date else None,'blocked':task.blocked,'blocked_reason':task.blocked_reason,
            'labels':list(task.labels.values('id','title','color')),'dependencies':list(task.dependencies.values_list('id',flat=True)),
            'recorded_at':timezone.now().isoformat()}

def sync_history(task, previous_sprint=None):
    if previous_sprint and previous_sprint.pk != task.sprint_id and previous_sprint.status!='completed':
        entry,_=SprintEntry.objects.get_or_create(sprint=previous_sprint,task_key=task.pk,defaults={'task':task})
        entry.snapshot=snapshot(task)
        entry.removed_at=timezone.now()
        entry.save(update_fields=['snapshot','removed_at'])
    if task.sprint_id and task.sprint.status!='completed':
        entry,_=SprintEntry.objects.get_or_create(sprint=task.sprint,task_key=task.pk,defaults={'task':task})
        entry.snapshot=snapshot(task)
        entry.removed_at=None
        entry.save(update_fields=['snapshot','removed_at'])

def freeze_sprint(sprint):
    for task in sprint.tasks.select_related('column','assignee','sprint'):
        sync_history(task)
