import re
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.core import mail
from rest_framework.test import APITestCase
from .models import RecoveryEmail

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',AUTH_RATE_LIMIT=100)
class AuthSecurityTests(APITestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user('recover',password='Original-strong-982!',email='recover@example.com')
        RecoveryEmail.objects.create(user=self.user,email=self.user.email)

    @override_settings(AUTH_RATE_LIMIT=2)
    def test_failed_logins_are_rate_limited(self):
        data={'username':'recover','password':'wrong'}
        self.assertEqual(self.client.post('/api/session/',data,format='json').status_code,400)
        self.assertEqual(self.client.post('/api/session/',data,format='json').status_code,400)
        response=self.client.post('/api/session/',data,format='json')
        self.assertEqual(response.status_code,429)
        self.assertIn('Retry-After',response)

    def test_reset_is_single_use_and_revokes_old_session(self):
        self.client.force_login(self.user)
        response=self.client.post('/api/password/recovery/',{'email':self.user.email},format='json')
        self.assertEqual(response.status_code,200)
        uid,token=re.search(r'reset_uid=([^&\s]+)&reset_token=([^\s]+)',mail.outbox[0].body).groups()
        data={'uid':uid,'token':token,'password':'New-strong-password-741!'}
        self.assertEqual(self.client.post('/api/password/reset/',data,format='json').status_code,200)
        self.assertIsNone(self.client.get('/api/session/').json()['user'])
        self.assertEqual(self.client.post('/api/password/reset/',data,format='json').status_code,400)
        self.assertEqual(self.client.post('/api/session/',{'username':'recover','password':data['password']},format='json').status_code,200)

    def test_unknown_email_has_same_response(self):
        unknown=self.client.post('/api/password/recovery/',{'email':'unknown@example.com'},format='json')
        known=self.client.post('/api/password/recovery/',{'email':self.user.email},format='json')
        self.assertEqual(unknown.json(),known.json())
        self.assertEqual(len(mail.outbox),1)

    def test_email_change_requires_current_password(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.post('/api/account/',{'email':'new@example.com','password':'wrong'},format='json').status_code,400)
        self.assertEqual(self.client.post('/api/account/',{'email':'new@example.com','password':'Original-strong-982!'},format='json').status_code,200)
        self.assertEqual(RecoveryEmail.objects.get(user=self.user).email,'new@example.com')

    def test_expired_token_is_rejected(self):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from datetime import datetime,timedelta
        from unittest.mock import patch
        with patch.object(default_token_generator,'_now',return_value=datetime.now()-timedelta(hours=2)):
            token=default_token_generator.make_token(self.user)
        data={'uid':urlsafe_base64_encode(force_bytes(self.user.pk)),'token':token,'password':'New-strong-password-741!'}
        self.assertEqual(self.client.post('/api/password/reset/',data,format='json').status_code,400)
