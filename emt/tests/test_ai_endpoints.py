from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch

class AIGenerationViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    @patch('emt.views_ai.AIClient.need_analysis', return_value={'need_analysis': 'ok'})
    def test_ai_need_analysis(self, mock_ai):
        resp = self.client.post(reverse('emt:ai_need_analysis'), {'title': 'T', 'department': 'D'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get('need_analysis'), 'ok')
        mock_ai.assert_called()

    @patch('emt.views_ai.AIClient.objectives', return_value={'objectives': []})
    def test_ai_objectives(self, mock_ai):
        resp = self.client.post(reverse('emt:ai_objectives'), {'title': 'T', 'department': 'D'})
        self.assertEqual(resp.status_code, 200)
        self.assertIn('objectives', resp.json())
        mock_ai.assert_called()

    @patch('emt.views_ai.AIClient.outcomes', return_value={'outcomes': []})
    def test_ai_outcomes(self, mock_ai):
        resp = self.client.post(reverse('emt:ai_outcomes'), {'title': 'T', 'department': 'D'})
        self.assertEqual(resp.status_code, 200)
        self.assertIn('outcomes', resp.json())
        mock_ai.assert_called()

    @patch('emt.views_ai.AIClient.report', return_value={'report_markdown': 'md', 'tables': {}})
    def test_ai_report(self, mock_ai):
        resp = self.client.post(reverse('emt:ai_report'), {'title': 'T', 'department': 'D'})
        self.assertEqual(resp.status_code, 200)
        self.assertIn('report_markdown', resp.json())
        mock_ai.assert_called()
