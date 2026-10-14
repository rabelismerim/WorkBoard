from rest_framework.test import APITestCase
from . import test_robust
from .models import Task, Comment

class PaginationTests(APITestCase):
    setUp=test_robust.WorkboardTests.setUp
    def test_summaries_omit_details_and_pages_are_bounded(self):
        Task.objects.bulk_create([Task(column=self.todo,title=f'Tarefa {i}',position=i+1) for i in range(60)])
        Comment.objects.create(task=self.task,author=self.owner,content='Contexto privado do cartão')
        boards=self.client.get('/api/boards/').json()
        self.assertNotIn('columns',boards['results'][0])
        workspace=self.client.get(f'/api/boards/{self.board.id}/').json()
        self.assertEqual(workspace['columns'][0]['tasks'],[])
        tasks=self.client.get(f'/api/tasks/?column={self.todo.id}').json()
        self.assertEqual(len(tasks['results']),50)
        self.assertEqual(tasks['count'],61)
        self.assertNotIn('comments',tasks['results'][0])
        self.assertIsNotNone(tasks['next'])
        detail=self.client.get(f'/api/tasks/{self.task.id}/').json()
        self.assertEqual(detail['comments'][0]['content'],'Contexto privado do cartão')

    def test_filters_apply_before_pagination(self):
        Task.objects.bulk_create([Task(column=self.todo,title=f'Tarefa {i}',priority='low') for i in range(60)])
        result=self.client.get(f'/api/tasks/?column={self.todo.id}&search=Primeiro&priority=medium').json()
        self.assertEqual(result['count'],1)
        self.assertEqual(result['results'][0]['id'],self.task.id)
