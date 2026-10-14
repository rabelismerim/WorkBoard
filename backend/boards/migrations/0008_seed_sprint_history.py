from django.db import migrations
from django.utils import timezone

def seed(apps,schema_editor):
    Task=apps.get_model('boards','Task')
    Entry=apps.get_model('boards','SprintEntry')
    for task in Task.objects.filter(sprint__isnull=False).select_related('column','assignee'):
        Entry.objects.get_or_create(sprint_id=task.sprint_id,task_key=task.id,defaults={'task_id':task.id,'snapshot':{
            'id':task.id,'title':task.title,'description':task.description,'priority':task.priority,
            'column':task.column.title,'kind':task.column.kind,'assignee':task.assignee.username if task.assignee else None,
            'archived':task.archived,'deleted':task.deleted_at is not None,'completed':task.column.kind=='done',
            'recorded_at':timezone.now().isoformat(),'legacy':True,
        }})

class Migration(migrations.Migration):
    dependencies=[('boards','0007_sprintentry')]
    operations=[migrations.RunPython(seed,migrations.RunPython.noop)]
