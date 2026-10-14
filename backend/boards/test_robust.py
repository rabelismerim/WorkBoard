import tempfile
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase, APIClient
from .models import Board, Column, Task, BoardMember, Label, ChecklistItem, Comment, Activity, Notification

class WorkboardTests(APITestCase):
    def setUp(self):
        self.owner=get_user_model().objects.create_user('owner',password='Strong-pass-782!')
        self.editor=get_user_model().objects.create_user('editor',password='Strong-pass-782!')
        self.viewer=get_user_model().objects.create_user('viewer',password='Strong-pass-782!')
        self.stranger=get_user_model().objects.create_user('stranger',password='Strong-pass-782!')
        self.board=Board.objects.create(owner=self.owner,title='Projeto')
        self.todo=Column.objects.create(board=self.board,title='A fazer')
        self.progress=Column.objects.create(board=self.board,title='Fazendo',kind='progress',position=1,wip_limit=1)
        self.done=Column.objects.create(board=self.board,title='Entregue',kind='done',position=2)
        BoardMember.objects.create(board=self.board,user=self.editor,role='editor')
        BoardMember.objects.create(board=self.board,user=self.viewer,role='viewer')
        self.task=Task.objects.create(column=self.todo,title='Primeiro')
        self.client.force_authenticate(self.owner)

    def write(self,path,method='patch',data=None,revision=None,format='json'):
        self.board.refresh_from_db()
        return getattr(self.client,method)(path,data=data,format=format,HTTP_IF_MATCH=str(self.board.revision if revision is None else revision))

    def test_roles_and_revocation(self):
        self.client.force_authenticate(self.editor)
        self.assertEqual(len(self.client.get('/api/boards/').json()['results']),1)
        self.assertEqual(self.write(f'/api/tasks/{self.task.id}/',data={'title':'Editado'}).status_code,200)
        self.assertEqual(self.write(f'/api/boards/{self.board.id}/',data={'title':'Invadido'}).status_code,403)
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.write(f'/api/tasks/{self.task.id}/',data={'title':'Editado'}).status_code,403)
        BoardMember.objects.filter(board=self.board,user=self.viewer).delete()
        self.assertEqual(self.client.get(f'/api/boards/{self.board.id}/').status_code,404)
        self.assertEqual(self.client.get(f'/api/tasks/{self.task.id}/').status_code,404)

    def test_optimistic_concurrency_and_required_header(self):
        self.assertEqual(self.client.patch(f'/api/tasks/{self.task.id}/',{'title':'Sem versão'}).status_code,428)
        revision=self.board.revision
        self.assertEqual(self.write(f'/api/tasks/{self.task.id}/',data={'title':'Primeira alteração'},revision=revision).status_code,200)
        self.assertEqual(self.write(f'/api/tasks/{self.task.id}/',data={'title':'Sobrescrever'},revision=revision).status_code,409)
        self.task.refresh_from_db()
        self.assertEqual(self.task.title,'Primeira alteração')

    def test_wip_on_create_move_and_restore(self):
        task=Task.objects.create(column=self.progress,title='Ocupando')
        self.assertEqual(self.write('/api/tasks/','post',{'column':self.progress.id,'title':'Excesso'}).status_code,400)
        self.assertEqual(self.write(f'/api/tasks/{self.task.id}/move/','post',{'column':self.progress.id}).status_code,400)
        self.assertEqual(self.write(f'/api/tasks/{task.id}/','delete').status_code,204)
        self.assertEqual(self.write(f'/api/tasks/{self.task.id}/move/','post',{'column':self.progress.id}).status_code,200)
        self.assertEqual(self.write(f'/api/tasks/{task.id}/restore/','post',{}).status_code,400)

    def test_reorder_inside_column(self):
        second=Task.objects.create(column=self.todo,title='Segundo',position=1)
        third=Task.objects.create(column=self.todo,title='Terceiro',position=2)
        self.assertEqual(self.write(f'/api/tasks/{third.id}/move/','post',{'column':self.todo.id,'before':self.task.id}).status_code,200)
        self.assertEqual(list(self.todo.tasks.order_by('position').values_list('id',flat=True)),[third.id,self.task.id,second.id])

    def test_dependencies_and_cycles(self):
        second=Task.objects.create(column=self.todo,title='Segundo')
        self.assertEqual(self.write(f'/api/tasks/{self.task.id}/',data={'dependencies':[second.id]}).status_code,200)
        self.assertEqual(self.write(f'/api/tasks/{second.id}/',data={'dependencies':[self.task.id]}).status_code,400)
        self.assertEqual(self.write(f'/api/tasks/{self.task.id}/move/','post',{'column':self.done.id}).status_code,400)
        self.assertEqual(self.write(f'/api/tasks/{second.id}/move/','post',{'column':self.done.id}).status_code,200)
        self.assertEqual(self.write(f'/api/tasks/{self.task.id}/move/','post',{'column':self.done.id}).status_code,200)
        self.assertEqual(self.write(f'/api/tasks/{second.id}/','delete').status_code,400)

    def test_assignment_labels_and_blocked_reason(self):
        self.assertEqual(self.write(f'/api/tasks/{self.task.id}/',data={'assignee':self.stranger.id}).status_code,400)
        self.assertEqual(self.write(f'/api/tasks/{self.task.id}/',data={'blocked':True}).status_code,400)
        label=Label.objects.create(board=self.board,title='Backend')
        self.assertEqual(self.write(f'/api/tasks/{self.task.id}/',data={'assignee':self.editor.id,'labels':[label.id],'blocked':True,'blocked_reason':'Aguardando acesso'}).status_code,200)
        self.assertEqual(Notification.objects.filter(user=self.editor,task=self.task).count(),1)
        self.assertEqual(self.write(f'/api/tasks/{self.task.id}/move/','post',{'column':self.done.id}).status_code,400)
        foreign=Board.objects.create(owner=self.stranger,title='Privado')
        label2=Label.objects.create(board=foreign,title='Privada')
        self.assertEqual(self.write(f'/api/tasks/{self.task.id}/',data={'labels':[label2.id]}).status_code,400)

    def test_soft_delete_restore_and_archiving(self):
        self.assertEqual(self.write(f'/api/tasks/{self.task.id}/','delete').status_code,204)
        self.assertEqual(self.client.get(f'/api/tasks/{self.task.id}/').status_code,404)
        self.assertEqual(self.write(f'/api/tasks/{self.task.id}/restore/','post',{}).status_code,200)
        self.assertEqual(self.write(f'/api/boards/{self.board.id}/',data={'archived':True}).status_code,200)
        self.assertEqual(self.write(f'/api/tasks/{self.task.id}/',data={'title':'Não alterar'}).status_code,400)
        self.assertEqual(self.write(f'/api/boards/{self.board.id}/',data={'archived':False}).status_code,200)
        self.assertEqual(self.write(f'/api/boards/{self.board.id}/','delete').status_code,204)
        self.assertEqual(self.client.get('/api/boards/').json()['results'],[])
        self.assertEqual(self.write(f'/api/boards/{self.board.id}/restore/','post',{}).status_code,200)
        self.assertEqual(self.client.get(f'/api/tasks/{self.task.id}/').status_code,200)

    def test_column_delete_preserves_tasks(self):
        self.assertEqual(self.write(f'/api/columns/{self.todo.id}/','delete').status_code,400)
        self.assertEqual(self.write(f'/api/columns/{self.done.id}/','delete').status_code,204)
        self.assertEqual(self.write(f'/api/columns/{self.done.id}/restore/','post',{}).status_code,200)

    def test_comment_checklist_and_audit(self):
        response=self.write('/api/checklist/','post',{'task':self.task.id,'title':'Validar API'})
        self.assertEqual(response.status_code,201)
        self.assertEqual(self.write(f'/api/checklist/{response.json()["id"]}/',data={'done':True}).status_code,200)
        response=self.write('/api/comments/','post',{'task':self.task.id,'content':'Vamos revisar'})
        self.assertEqual(response.status_code,201)
        self.client.force_authenticate(self.editor)
        self.assertEqual(self.write(f'/api/comments/{response.json()["id"]}/',data={'content':'Alterar outro autor'}).status_code,403)
        self.assertGreaterEqual(Activity.objects.filter(board=self.board).count(),3)

    def test_private_attachment_download_and_limit(self):
        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            file=SimpleUploadedFile('referencia.txt',b'conteudo',content_type='text/plain')
            response=self.write('/api/attachments/','post',{'task':self.task.id,'file':file},format='multipart')
            self.assertEqual(response.status_code,201)
            url=response.json()['download_url']
            response=self.client.get(url)
            self.assertEqual(response.status_code,200)
            self.assertEqual(b''.join(response.streaming_content),b'conteudo')
            self.client.force_authenticate(self.stranger)
            self.assertEqual(self.client.get(url).status_code,404)
            self.client.force_authenticate(self.owner)
            large=SimpleUploadedFile('large.bin',b'x'*(10*1024*1024+1))
            self.assertEqual(self.write('/api/attachments/','post',{'task':self.task.id,'file':large},format='multipart').status_code,400)

    def test_metrics_completion_kind_and_deadlines(self):
        self.assertEqual(self.write(f'/api/tasks/{self.task.id}/move/','post',{'column':self.done.id}).status_code,200)
        metrics=self.client.get(f'/api/boards/{self.board.id}/metrics/').json()
        self.assertEqual(metrics['completed'],1)
        self.assertEqual(len(metrics['cumulative_flow']),14)
        self.assertIsNotNone(metrics['cycle_time_days'])
        self.assertEqual(self.write(f'/api/tasks/{self.task.id}/move/','post',{'column':self.todo.id}).status_code,200)
        self.assertEqual(self.client.get(f'/api/boards/{self.board.id}/metrics/').json()['completed'],0)

    def test_admin_cannot_promote_self(self):
        self.client.force_authenticate(self.editor)
        member=BoardMember.objects.get(board=self.board,user=self.editor)
        member.role='admin'
        member.save()
        viewer=BoardMember.objects.get(board=self.board,user=self.viewer)
        self.assertEqual(self.write(f'/api/members/{viewer.id}/',data={'role':'admin'}).status_code,403)

    def test_throughput_survives_reopening_and_archiving(self):
        self.write(f'/api/tasks/{self.task.id}/move/','post',{'column':self.done.id})
        self.write(f'/api/tasks/{self.task.id}/',data={'description':'Editar sem nova entrega'})
        self.write(f'/api/tasks/{self.task.id}/move/','post',{'column':self.todo.id})
        self.write(f'/api/tasks/{self.task.id}/move/','post',{'column':self.done.id})
        self.write(f'/api/tasks/{self.task.id}/',data={'archived':True})
        metrics=self.client.get(f'/api/boards/{self.board.id}/metrics/').json()
        self.assertEqual(metrics['completed'],0)
        self.assertEqual(sum(day['count'] for day in metrics['throughput']),1)
