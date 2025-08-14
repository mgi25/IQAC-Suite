import json
from unittest.mock import patch
import requests
from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth.models import User


class GenerateNeedAnalysisTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('u', 'u@example.com', 'p')
        self.client.force_login(self.user)
    @override_settings(OPENROUTER_API_KEY='k', OPENROUTER_MODEL='m')
    @patch('emt.views.requests.post')
    def test_openrouter_success(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'choices': [{'message': {'content': 'ok'}}]
        }
        resp = self.client.post(reverse('emt:generate_need_analysis'), {'context': 'hello'})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['text'], 'ok')
        mock_post.assert_called_once()
        self.assertIn('openrouter.ai', mock_post.call_args[0][0])

    @override_settings(AI_BACKEND='LOCAL_HTTP', LOCAL_AI_BASE_URL='http://local', LOCAL_AI_MODEL='m')
    @patch('emt.views.requests.post')
    def test_local_success(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'choices': [{'message': {'content': 'local'}}]
        }
        resp = self.client.post(reverse('emt:generate_need_analysis'), {'context': 'ctx'})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['text'], 'local')
        mock_post.assert_called_once()
        self.assertTrue(mock_post.call_args[0][0].startswith('http://local'))

    @override_settings(OPENROUTER_API_KEY='k', OPENROUTER_MODEL='m')
    @patch('emt.views.requests.post', side_effect=requests.Timeout)
    def test_timeout_error(self, mock_post):
        resp = self.client.post(reverse('emt:generate_need_analysis'), {'context': 'hello'})
        self.assertEqual(resp.status_code, 503)
        data = resp.json()
        self.assertFalse(data['ok'])

