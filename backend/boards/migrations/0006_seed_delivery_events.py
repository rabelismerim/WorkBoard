from django.db import migrations

def seed(apps,schema_editor):
    Event=apps.get_model('boards','FlowEvent')
    state={}
    ids=[]
    for event in Event.objects.order_by('created_at','id').iterator():
        if event.stage=='done' and state.get(event.task_id) not in ['done','hidden']:
            ids.append(event.id)
        state[event.task_id]=event.stage
    Event.objects.filter(id__in=ids).update(delivered=True)

class Migration(migrations.Migration):
    dependencies=[('boards','0005_flowevent_delivered')]
    operations=[migrations.RunPython(seed,migrations.RunPython.noop)]
