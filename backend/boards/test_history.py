from . import test_robust
from rest_framework.test import APITestCase
from .models import Sprint, SprintEntry

class SprintHistoryTests(APITestCase):
    setUp=test_robust.WorkboardTests.setUp
    write=test_robust.WorkboardTests.write
    def test_history_survives_return_to_backlog_and_later_edits(self):
        sprint=Sprint.objects.create(board=self.board,title='Ciclo',start_date='2026-10-14',end_date='2026-10-28')
        self.write(f'/api/tasks/{self.task.id}/',data={'sprint':sprint.id})
        self.write(f'/api/sprints/{sprint.id}/start/','post',{})
        self.write(f'/api/sprints/{sprint.id}/complete/','post',{})
        self.task.refresh_from_db()
        self.assertIsNone(self.task.sprint_id)
        self.write(f'/api/tasks/{self.task.id}/',data={'title':'Outro nome'})
        self.write(f'/api/tasks/{self.task.id}/','delete')
        history=self.client.get(f'/api/sprints/{sprint.id}/history/').json()
        self.assertEqual(history[0]['snapshot']['title'],'Primeiro')
        self.assertFalse(history[0]['snapshot']['completed'])
        self.assertEqual(history[0]['task_key'],self.task.id)

    def test_removed_participant_remains_in_history(self):
        sprint=Sprint.objects.create(board=self.board,title='Ciclo',start_date='2026-10-14',end_date='2026-10-28')
        self.write(f'/api/tasks/{self.task.id}/',data={'sprint':sprint.id})
        self.write(f'/api/tasks/{self.task.id}/',data={'sprint':None})
        entry=SprintEntry.objects.get(sprint=sprint)
        self.assertIsNotNone(entry.removed_at)
        self.client.force_authenticate(self.stranger)
        self.assertEqual(self.client.get(f'/api/sprints/{sprint.id}/history/').status_code,404)
