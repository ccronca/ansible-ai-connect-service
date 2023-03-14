#!/usr/bin/env python3

import time
import uuid
from unittest.mock import patch

from ai.api.serializers import CompletionRequestSerializer
from ai.api.views import Completions
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import modify_settings
from rest_framework.response import Response
from rest_framework.test import APITestCase


class DummyMeshClient:
    def __init__(self, test, payload, response_data):
        self.test = test

        if "prompt" in payload:
            serializer = CompletionRequestSerializer()
            data = serializer.validate(payload.copy())

            view = Completions()
            data["context"], data["prompt"] = view.preprocess(
                data.get("context"), data.get("prompt")
            )

            self.expects = {
                "instances": [
                    {
                        "context": data.get("context"),
                        "prompt": data.get("prompt"),
                        "userId": payload.get("userId"),
                        "suggestionId": payload.get("suggestionId"),
                    }
                ]
            }

        self.response_data = response_data

    def infer(self, data, model_name=None):
        self.test.assertEqual(data, self.expects)
        time.sleep(0.1)  # w/o this line test_rate_limit() fails...
        # i.e., still receives 200 after 10 API calls...
        return Response(self.response_data)


class WisdomServiceAPITestCaseBase(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.username = 'u' + str(int(time.time()))
        cls.user = get_user_model().objects.create_user(
            username=cls.username,
            email='user@example.com',
            password='secret',
        )
        cls.user_id = str(uuid.uuid4())

    def setUp(self):
        cache.clear()

    def searchInLogOutput(self, s, logs):
        for log in logs:
            if s in log:
                return True
        return False

    def assertInLog(self, s, logs):
        self.assertTrue(self.searchInLogOutput(s, logs))

    def assertNotInLog(self, s, logs):
        self.assertFalse(self.searchInLogOutput(s, logs))


@modify_settings()
class TestCompletionView(WisdomServiceAPITestCaseBase):
    def test_full_payload(self):
        payload = {
            "prompt": "---\n- hosts: all\n  become: yes\n\n  tasks:\n    - name: Install Apache\n",
            "userId": self.user_id,
            "suggestionId": str(uuid.uuid4()),
        }
        response_data = {"predictions": ["      ansible.builtin.apt:\n        name: apache2"]}
        self.client.force_authenticate(user=self.user)
        with patch.object(
            apps.get_app_config('ai'),
            'model_mesh_client',
            DummyMeshClient(self, payload, response_data),
        ):
            r = self.client.post('/api/ai/completions/', payload)
            self.assertEqual(r.status_code, 200)
            self.assertIsNotNone(r.data['predictions'])

    def test_rate_limit(self):
        payload = {
            "prompt": "---\n- hosts: all\n  become: yes\n\n  tasks:\n    - name: Install Apache\n",
            "userId": self.user_id,
            "suggestionId": str(uuid.uuid4()),
        }
        response_data = {"predictions": ["      ansible.builtin.apt:\n        name: apache2"]}
        self.client.force_authenticate(user=self.user)
        with patch.object(
            apps.get_app_config('ai'),
            'model_mesh_client',
            DummyMeshClient(self, payload, response_data),
        ):
            r = self.client.post('/api/ai/completions/', payload)
            self.assertEqual(r.status_code, 200)
            self.assertIsNotNone(r.data['predictions'])
            for _ in range(10):
                r = self.client.post('/api/ai/completions/', payload)
            self.assertEqual(r.status_code, 429)

    def test_missing_prompt(self):
        payload = {
            "userId": self.user_id,
            "suggestionId": str(uuid.uuid4()),
        }
        response_data = {"predictions": ["      ansible.builtin.apt:\n        name: apache2"]}
        self.client.force_authenticate(user=self.user)
        with patch.object(
            apps.get_app_config('ai'),
            'model_mesh_client',
            DummyMeshClient(self, payload, response_data),
        ):
            r = self.client.post('/api/ai/completions/', payload)
            self.assertEqual(r.status_code, 400)

    def test_authentication_error(self):
        payload = {
            "prompt": "---\n- hosts: all\n  become: yes\n\n  tasks:\n    - name: Install Apache\n",
            "userId": self.user_id,
            "suggestionId": str(uuid.uuid4()),
        }
        response_data = {"predictions": ["      ansible.builtin.apt:\n        name: apache2"]}
        # self.client.force_authenticate(user=self.user)
        with patch.object(
            apps.get_app_config('ai'),
            'model_mesh_client',
            DummyMeshClient(self, payload, response_data),
        ):
            r = self.client.post('/api/ai/completions/', payload)
            self.assertEqual(r.status_code, 401)