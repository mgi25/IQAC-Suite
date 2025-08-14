import json
from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User


class AIGenerationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('u', 'u@example.com', 'p')
        self.client.force_login(self.user)

    @patch('emt.views.requests.post')
    def test_generate_need_analysis(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'choices': [{'message': {'content': 'need text'}}]
        }
        resp = self.client.post(reverse('emt:generate_need_analysis'), {
            'title': 'T',
            'audience': 'Students'
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['text'], 'need text')

    @patch('emt.views.requests.post')
    def test_generate_objectives(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'choices': [{'message': {'content': 'obj text'}}]
        }
        resp = self.client.post(reverse('emt:generate_objectives'), {
            'title': 'T',
            'audience': 'Students'
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['text'], 'obj text')

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
