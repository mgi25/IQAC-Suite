import json
from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from suite import ai_client
import requests


class AIGenerationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('u', 'u@example.com', 'p')
        self.client.force_login(self.user)

    @patch('emt.views.chat')
    def test_generate_need_analysis(self, mock_chat):
        mock_chat.return_value = 'need text'
        resp = self.client.post(reverse('emt:generate_need_analysis'), {
            'title': 'T',
            'audience': 'Students'
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['text'], 'need text')

    @patch('emt.views.chat')
    def test_generate_objectives(self, mock_chat):
        mock_chat.return_value = 'obj text'
        resp = self.client.post(reverse('emt:generate_objectives'), {
            'title': 'T',
            'audience': 'Students'
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['text'], 'obj text')

    @patch('emt.views.chat')
    def test_generate_need_analysis_error(self, mock_chat):
        mock_chat.side_effect = ai_client.AIError('Ollama request failed: down')
        resp = self.client.post(reverse('emt:generate_need_analysis'), {
            'title': 'T',
            'audience': 'Students'
        })
        self.assertEqual(resp.status_code, 503)
        data = resp.json()
        self.assertIn('Ollama request failed', data['error'])

    @patch('emt.views.requests.post')
    def test_generate_expected_outcomes(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'choices': [{'message': {'content': 'out text'}}]
        }
        resp = self.client.post(reverse('emt:generate_expected_outcomes'), {
            'title': 'T',
            'audience': 'Students'
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['text'], 'out text')

    @patch('suite.ai_client._ollama_available', return_value=True)
    @patch('suite.ai_client.requests.post')
    def test_generate_need_analysis_timeout(self, mock_post, mock_avail):
        mock_post.side_effect = requests.Timeout
        resp = self.client.post(reverse('emt:generate_need_analysis'), {
            'title': 'T',
            'audience': 'Students'
        })
        self.assertEqual(resp.status_code, 503)
        data = resp.json()
        self.assertIn('timed out', data['error'])
