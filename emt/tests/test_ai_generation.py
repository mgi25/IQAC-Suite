import json
from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from suite import ai_client


class AIGenerationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('u', 'u@example.com', 'p')
        self.client.force_login(self.user)

    @patch('suite.ai_client.chat')
    def test_generate_need_analysis(self, mock_chat):
        mock_chat.return_value = 'need text'
        resp = self.client.post(reverse('emt:generate_need_analysis'), {
            'title': 'T',
            'audience': 'Students'
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['text'], 'need text')

    @patch('suite.ai_client.chat')
    def test_generate_objectives(self, mock_chat):
        mock_chat.return_value = 'obj text'
        resp = self.client.post(reverse('emt:generate_objectives'), {
            'title': 'T',
            'audience': 'Students'
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['text'], 'obj text')

    @patch('suite.ai_client.chat')
    def test_generate_need_analysis_error(self, mock_chat):
        mock_chat.side_effect = ai_client.AIError('All AI backends failed: OLLAMA: down')
        resp = self.client.post(reverse('emt:generate_need_analysis'), {
            'title': 'T',
            'audience': 'Students'
        })
        self.assertEqual(resp.status_code, 503)
        data = resp.json()
        self.assertFalse(data['ok'])
        self.assertIn('All AI backends failed', data['error'])

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
