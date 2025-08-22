from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from unittest.mock import patch
from ai import client_ollama


class EnhanceSummaryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('u', 'u@example.com', 'p')
        self.client.force_login(self.user)

    @patch('ai.enhance_summary.chat')
    def test_enhance_summary_success(self, mock_chat):
        mock_chat.return_value = 'improved'
        resp = self.client.post(reverse('emt:enhance_summary'), {
            'text': 'original',
            'title': 'T',
            'department': 'D',
            'start_date': '2024-01-01',
            'end_date': '2024-01-02'
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['summary'], 'improved')

    @patch('ai.enhance_summary.chat')
    def test_enhance_summary_error(self, mock_chat):
        mock_chat.side_effect = client_ollama.AIError('down')
        resp = self.client.post(reverse('emt:enhance_summary'), {'text': 't'})
        self.assertEqual(resp.status_code, 503)
        data = resp.json()
        self.assertFalse(data['ok'])
        self.assertIn('down', data['error'])
