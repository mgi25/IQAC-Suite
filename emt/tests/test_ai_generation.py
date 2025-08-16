import json
from unittest.mock import patch
from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.auth.models import User
from suite import ai_client
import requests


class AIGenerationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('u', 'u@example.com', 'p')
        self.client.force_login(self.user)
        self.factory = RequestFactory()

    @patch('suite.views.chat')
    def test_generate_need_analysis(self, mock_chat):
        mock_chat.return_value = 'need text'
        resp = self.client.post(reverse('emt:generate_need_analysis'), {
            'title': 'T',
            'audience': 'Students'
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['field'], 'need_analysis')
        self.assertEqual(data['value'], 'need text')

    @patch('suite.views.chat')
    def test_generate_objectives(self, mock_chat):
        mock_chat.return_value = 'obj text'
        resp = self.client.post(reverse('emt:generate_objectives'), {
            'title': 'T',
            'audience': 'Students'
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['field'], 'objectives')
        self.assertEqual(data['value'], ['obj text'])

    @patch('suite.views.chat')
    def test_generate_objectives_error(self, mock_chat):
        mock_chat.side_effect = ai_client.AIError('down')
        resp = self.client.post(reverse('emt:generate_objectives'), {
            'title': 'T',
            'audience': 'Students'
        })
        self.assertEqual(resp.status_code, 503)
        data = resp.json()
        self.assertFalse(data['ok'])
        self.assertIn('down', data['error'])

    @patch('suite.views.chat')
    def test_generate_need_analysis_error(self, mock_chat):
        mock_chat.side_effect = ai_client.AIError('Ollama request failed: down')
        resp = self.client.post(reverse('emt:generate_need_analysis'), {
            'title': 'T',
            'audience': 'Students'
        })
        self.assertEqual(resp.status_code, 503)
        data = resp.json()
        self.assertFalse(data['ok'])
        self.assertIn('Ollama request failed', data['error'])

    @patch('suite.views.chat')
    def test_generate_expected_outcomes(self, mock_chat):
        mock_chat.return_value = 'out text'
        resp = self.client.post(reverse('emt:generate_expected_outcomes'), {
            'title': 'T',
            'audience': 'Students'
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['field'], 'learning_outcomes')
        self.assertEqual(data['value'], ['out text'])

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
        self.assertFalse(data['ok'])
        self.assertIn('timed out', data['error'])

    @patch('suite.views.chat')
    def test_generate_why_event(self, mock_chat):
        mock_chat.return_value = json.dumps({
            'need_analysis': 'need',
            'objectives': ['o1'],
            'learning_outcomes': ['l1']
        })
        resp = self.client.post(reverse('emt:generate_why_event'), {
            'title': 'T'
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['need_analysis'], 'need')
        self.assertEqual(data['objectives'], ['o1'])
        self.assertEqual(data['learning_outcomes'], ['l1'])

    @patch('suite.views.chat')
    def test_generate_why_event_fenced_json(self, mock_chat):
        mock_chat.return_value = (
            "Here you go:\n```json\n"
            '{"need_analysis": "need", "objectives": ["o1"], "learning_outcomes": ["l1"]}\n'
            "```\nThanks"
        )
        resp = self.client.post(reverse('emt:generate_why_event'), {'title': 'T'})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['need_analysis'], 'need')
        self.assertEqual(data['objectives'], ['o1'])
        self.assertEqual(data['learning_outcomes'], ['l1'])

    @patch('suite.views.chat')
    def test_generate_why_event_trailing_commas(self, mock_chat):
        mock_chat.return_value = (
            '{"need_analysis": "need", "objectives": ["o1",], '
            '"learning_outcomes": ["l1"],}'
        )
        resp = self.client.post(reverse('emt:generate_why_event'), {'title': 'T'})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['need_analysis'], 'need')
        self.assertEqual(data['objectives'], ['o1'])
        self.assertEqual(data['learning_outcomes'], ['l1'])

    @patch('suite.views.chat')
    def test_generate_why_event_string_lists(self, mock_chat):
        mock_chat.return_value = json.dumps({
            'need_analysis': 'need',
            'objectives': '1. o1\n2. o2',
            'learning_outcomes': '• l1\n• l2'
        })
        resp = self.client.post(reverse('emt:generate_why_event'), {'title': 'T'})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['need_analysis'], 'need')
        self.assertEqual(data['objectives'], ['o1', 'o2'])
        self.assertEqual(data['learning_outcomes'], ['l1', 'l2'])

    @patch('suite.views.chat')
    def test_generate_why_event_missing_fields(self, mock_chat):
        mock_chat.side_effect = [
            json.dumps({'need_analysis': 'need'}),
            'obj1\nobj2',
            'out1\nout2',
        ]
        resp = self.client.post(reverse('emt:generate_why_event'), {'title': 'T'})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['need_analysis'], 'need')
        self.assertEqual(data['objectives'], ['obj1', 'obj2'])
        self.assertEqual(data['learning_outcomes'], ['out1', 'out2'])
        self.assertEqual(mock_chat.call_count, 3)

    @patch('suite.views.chat')
    def test_generate_why_event_empty_response(self, mock_chat):
        mock_chat.return_value = ""
        resp = self.client.post(reverse('emt:generate_why_event'), {'title': 'T'})
        self.assertEqual(resp.status_code, 500)
        data = resp.json()
        self.assertFalse(data['ok'])
        self.assertIn('Empty model response', data['error'])

    @patch('suite.views.chat')
    def test_generate_why_event_error(self, mock_chat):
        mock_chat.side_effect = ai_client.AIError('down')
        resp = self.client.post(reverse('emt:generate_why_event'), {
            'title': 'T'
        })
        self.assertEqual(resp.status_code, 503)
        data = resp.json()
        self.assertFalse(data['ok'])
        self.assertIn('down', data['error'])

    def test_need_analysis_requires_login(self):
        self.client.logout()
        resp = self.client.post(reverse('emt:generate_need_analysis'), {})
        self.assertEqual(resp.status_code, 302)

    def test_objectives_requires_login(self):
        self.client.logout()
        resp = self.client.post(reverse('emt:generate_objectives'), {})
        self.assertEqual(resp.status_code, 302)

    def test_outcomes_requires_login(self):
        self.client.logout()
        resp = self.client.post(reverse('emt:generate_expected_outcomes'), {})
        self.assertEqual(resp.status_code, 302)

    def test_why_event_requires_login(self):
        self.client.logout()
        resp = self.client.post(reverse('emt:generate_why_event'), {})
        self.assertEqual(resp.status_code, 302)

    def test_need_analysis_get_not_allowed(self):
        resp = self.client.get(reverse('emt:generate_need_analysis'))
        self.assertEqual(resp.status_code, 405)

    def test_objectives_get_not_allowed(self):
        resp = self.client.get(reverse('emt:generate_objectives'))
        self.assertEqual(resp.status_code, 405)

    def test_outcomes_get_not_allowed(self):
        resp = self.client.get(reverse('emt:generate_expected_outcomes'))
        self.assertEqual(resp.status_code, 405)

    def test_why_event_get_not_allowed(self):
        resp = self.client.get(reverse('emt:generate_why_event'))
        self.assertEqual(resp.status_code, 405)

    def test_collect_basic_facts_filters_fields(self):
        from suite.facts import collect_basic_facts
        req = self.factory.post('/', {
            'event_title': 'T',
            'target_audience': 'Students',
            'location': 'Hall',
            'department': 'Science',
        })
        facts = collect_basic_facts(req, ['event_title', 'location'])
        self.assertEqual(facts, {'event_title': 'T', 'location': 'Hall'})
