from django.db import migrations
from django.utils import timezone

def initialize(apps, schema_editor):
    Column = apps.get_model('boards','Column')
    Task = apps.get_model('boards','Task')
    FlowEvent = apps.get_model('boards','FlowEvent')
    Column.objects.filter(title='Em andamento').update(kind='progress')
    Column.objects.filter(title='Concluído').update(kind='done')
    now = timezone.now()
    events = []
    for task in Task.objects.select_related('column').all():
        if task.column.kind in ['progress','done']:
            task.started_at = now
        if task.column.kind == 'done':
            task.completed_at = now
        task.save(update_fields=['started_at','completed_at'])
        events.append(FlowEvent(board_id=task.column.board_id,task_id=task.id,stage=task.column.kind))
    FlowEvent.objects.bulk_create(events)

class Migration(migrations.Migration):
    dependencies = [('boards','0003_board_archived_board_deleted_at_board_revision_and_more')]
    operations = [migrations.RunPython(initialize,migrations.RunPython.noop)]
