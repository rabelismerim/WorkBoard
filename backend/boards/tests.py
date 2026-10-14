from django.contrib.auth import get_user_model
import re
import tempfile
from django.test import override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase, APIClient
from .models import Board, Column, Task, Sprint, RetroNote, BoardMember, Label, Activity, Notification

class RevisionClient(APIClient):
    def generic(self, method, path, data='', content_type='application/octet-stream', secure=False, **extra):
        if method not in ['GET','HEAD','OPTIONS'] and 'HTTP_IF_MATCH' not in extra:
            match=re.search(r'/api/([^/]+)/(\d+)/',path)
            models={'boards':Board,'columns':Column,'tasks':Task,'sprints':Sprint,'retro-notes':RetroNote,'members':BoardMember,'labels':Label}
            board=None
            if match and match[1] in models:
                obj=models[match[1]].objects.filter(pk=match[2]).first()
                if obj:
                    board=obj if isinstance(obj,Board) else obj.column.board if isinstance(obj,Task) else obj.sprint.board if isinstance(obj,RetroNote) else obj.board
            board=board or Board.objects.order_by('id').first()
            if board:
                extra['HTTP_IF_MATCH']=str(board.revision)
        return super().generic(method,path,data,content_type,secure,**extra)

class AccessTests(APITestCase):
    client_class=RevisionClient
    def setUp(self):
        self.owner = get_user_model().objects.create_user('owner', password='Strong-pass-782!')
        self.other = get_user_model().objects.create_user('other', password='Strong-pass-782!')
        self.board = Board.objects.create(owner=self.owner, title='Projeto')
        self.column = Column.objects.create(board=self.board, title='A fazer')
        self.task = Task.objects.create(column=self.column, title='Implementar')
        self.client.force_authenticate(self.owner)

    def test_anonymous_access_denied(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/boards/').status_code, 403)

    def test_foreign_data_hidden(self):
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get('/api/boards/').json(), [])
        self.assertEqual(self.client.get(f'/api/boards/{self.board.id}/').status_code, 404)
        self.assertEqual(self.client.patch(f'/api/tasks/{self.task.id}/', {'title':'Invadido'}).status_code, 404)

    def test_foreign_relationship_rejected(self):
        board = Board.objects.create(owner=self.other, title='Privado')
        column = Column.objects.create(board=board, title='Privado')
        self.assertEqual(self.client.patch(f'/api/tasks/{self.task.id}/', {'column':column.id}).status_code, 400)
        self.task.refresh_from_db()
        self.assertEqual(self.task.column_id, self.column.id)

    def test_board_default_columns(self):
        response = self.client.post('/api/boards/', {'title':'Novo'})
        self.assertEqual(response.status_code, 201)
        self.assertEqual([c['title'] for c in response.json()['columns']], ['A fazer','Em andamento','Concluído'])

    def test_task_validation_and_move(self):
        self.assertEqual(self.client.patch(f'/api/tasks/{self.task.id}/', {'priority':'invalid'}).status_code, 400)
        target = Column.objects.create(board=self.board, title='Concluído',kind='done')
        self.assertEqual(self.client.patch(f'/api/tasks/{self.task.id}/', {'column':target.id}).status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.column_id, target.id)

class SessionTests(APITestCase):
    def test_csrf_registration_and_logout(self):
        client = self.client_class(enforce_csrf_checks=True)
        client.get('/api/session/')
        data = {'username':'dev','password':'Long-strong-pass-782!','register':True}
        self.assertEqual(client.post('/api/session/', data, format='json').status_code, 403)
        token = client.cookies['csrftoken'].value
        self.assertEqual(client.post('/api/session/', data, format='json', HTTP_X_CSRFTOKEN=token).status_code, 200)
        self.assertEqual(client.get('/api/boards/').status_code, 200)
        token = client.cookies['csrftoken'].value
        self.assertEqual(client.delete('/api/session/', HTTP_X_CSRFTOKEN=token).status_code, 200)
        self.assertEqual(client.get('/api/boards/').status_code, 403)

class SprintTests(AccessTests):
    def setUp(self):
        super().setUp()
        self.sprint = Sprint.objects.create(board=self.board, title='Sprint 1', start_date='2026-10-14', end_date='2026-10-28')

    def test_dates_and_ownership_validation(self):
        data = {'board':self.board.id, 'title':'Sprint', 'start_date':'2026-10-28', 'end_date':'2026-10-14'}
        self.assertEqual(self.client.post('/api/sprints/', data).status_code, 400)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get('/api/sprints/').json(), [])
        self.assertEqual(self.client.post(f'/api/sprints/{self.sprint.id}/start/').status_code, 404)
        data['end_date'] = '2026-11-01'
        self.assertEqual(self.client.post('/api/sprints/', data).status_code, 400)

    def test_lifecycle_and_snapshot(self):
        self.task.sprint = self.sprint
        self.task.save()
        done = Column.objects.create(board=self.board, title='Concluído',kind='done')
        Task.objects.create(column=done, sprint=self.sprint, title='Feito')
        self.assertEqual(self.client.post(f'/api/sprints/{self.sprint.id}/complete/').status_code, 400)
        self.assertEqual(self.client.post(f'/api/sprints/{self.sprint.id}/start/').status_code, 200)
        second = Sprint.objects.create(board=self.board, title='Sprint 2', start_date='2026-11-01', end_date='2026-11-14')
        self.assertEqual(self.client.post(f'/api/sprints/{second.id}/start/').status_code, 400)
        self.assertEqual(self.client.patch(f'/api/sprints/{self.sprint.id}/', {'title':'Alterar'}).status_code, 400)
        self.assertEqual(self.client.delete(f'/api/sprints/{self.sprint.id}/').status_code, 400)
        response = self.client.post(f'/api/sprints/{self.sprint.id}/complete/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['total_at_close'], 2)
        self.assertEqual(response.json()['completed_at_close'], 1)
        self.task.refresh_from_db()
        self.assertIsNone(self.task.sprint)
        self.assertEqual(self.client.post(f'/api/sprints/{self.sprint.id}/start/').status_code, 400)
        self.assertEqual(self.client.patch(f'/api/tasks/{self.task.id}/', {'sprint':self.sprint.id}).status_code, 400)
        self.assertEqual(self.client.post(f'/api/sprints/{second.id}/start/').status_code, 200)

    def test_task_sprint_must_match_board(self):
        another = Board.objects.create(owner=self.owner, title='Outro quadro')
        other_sprint = Sprint.objects.create(board=another, title='Outro', start_date='2026-10-14', end_date='2026-10-28')
        self.assertEqual(self.client.patch(f'/api/tasks/{self.task.id}/', {'sprint':other_sprint.id}).status_code, 400)
        self.assertEqual(self.client.patch(f'/api/tasks/{self.task.id}/', {'sprint':self.sprint.id}).status_code, 200)
        other_column = Column.objects.create(board=another, title='Outra')
        self.assertEqual(self.client.patch(f'/api/tasks/{self.task.id}/', {'column':other_column.id}).status_code, 400)
        self.assertEqual(self.client.patch(f'/api/columns/{self.column.id}/', {'board':another.id}).status_code, 400)

    def test_retro_notes_permissions_and_actions(self):
        data = {'sprint':self.sprint.id, 'category':'action', 'content':'Revisar testes'}
        self.assertEqual(self.client.post('/api/retro-notes/', data).status_code, 400)
        self.client.post(f'/api/sprints/{self.sprint.id}/start/')
        response = self.client.post('/api/retro-notes/', data)
        self.assertEqual(response.status_code, 201)
        note_id = response.json()['id']
        self.assertEqual(self.client.patch(f'/api/retro-notes/{note_id}/', {'done':True}).status_code, 200)
        self.assertEqual(self.client.patch(f'/api/retro-notes/{note_id}/', {'category':'positive'}).status_code, 400)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get('/api/retro-notes/').json(), [])
        self.assertEqual(self.client.patch(f'/api/retro-notes/{note_id}/', {'content':'Invadido'}).status_code, 404)
        self.assertEqual(self.client.post('/api/retro-notes/', data).status_code, 400)

    def test_delete_planned_sprint_preserves_tasks(self):
        self.task.sprint = self.sprint
        self.task.save()
        self.assertEqual(self.client.delete(f'/api/sprints/{self.sprint.id}/').status_code, 204)
        self.task.refresh_from_db()
        self.assertIsNone(self.task.sprint)
