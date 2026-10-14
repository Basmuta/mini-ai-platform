"""Focused gateway tests with an in-memory upstream; no GPU or model needed."""
import json
import unittest

import httpx
from fastapi.testclient import TestClient

from app.main import MODEL_NAME, app


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.upstream = lambda request: httpx.Response(200, json={})
        self.requests = []
        self.client = TestClient(app)
        self.client.__enter__()
        self.original_client = app.state.http_client

        def handle(request):
            self.requests.append(request)
            return self.upstream(request)

        app.state.http_client = httpx.AsyncClient(
            transport=httpx.MockTransport(handle)
        )

    def tearDown(self):
        self.client.portal.call(app.state.http_client.aclose)
        app.state.http_client = self.original_client
        self.client.__exit__(None, None, None)

    def test_chat_success_and_payload(self):
        self.upstream = lambda request: httpx.Response(200, json={
            "choices": [{"message": {"content": "Hello"}}],
            "model": MODEL_NAME,
            "usage": {"total_tokens": 12},
        })
        response = self.client.post("/chat", json={"message": "Hi"},
                                    headers={"X-Request-ID": "test-id"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["response"], "Hello")
        self.assertEqual(response.json()["usage"], {"total_tokens": 12})
        self.assertGreaterEqual(response.json()["latency_ms"], 0)
        self.assertEqual(response.headers["X-Request-ID"], "test-id")
        request = self.requests[0]
        self.assertEqual(request.url.path, "/v1/chat/completions")
        payload = json.loads(request.content)
        self.assertEqual(payload["model"], MODEL_NAME)
        self.assertEqual(payload["messages"][-1]["content"], "Hi")
        self.assertEqual(payload["max_tokens"], 128)
        self.assertEqual(payload["chat_template_kwargs"], {"enable_thinking": False})

    def test_http_failures(self):
        for status in (401, 500, 503):
            with self.subTest(status=status):
                self.upstream = lambda request: httpx.Response(status)
                self.assertEqual(self.client.post("/chat", json={"message": "Hi"}).status_code, 502)
                self.assertEqual(self.client.get("/health/ready").status_code, 503)
                self.assertEqual(self.client.get("/health/live").status_code, 200)

    def test_connection_and_timeout_failures(self):
        for error in (httpx.ConnectError, httpx.ReadTimeout):
            with self.subTest(error=error):
                def fail(request):
                    raise error("upstream unavailable", request=request)
                self.upstream = fail
                self.assertEqual(self.client.post("/chat", json={"message": "Hi"}).status_code, 502)
                self.assertEqual(self.client.get("/health/ready").status_code, 503)

    def test_malformed_upstream(self):
        bodies = ("not JSON", {}, {"choices": []},
                  {"choices": [{"message": {"content": None}}], "model": MODEL_NAME},
                  {"choices": [{"message": {"content": "Hi"}}]})
        for body in bodies:
            with self.subTest(body=body):
                self.upstream = lambda request: (httpx.Response(200, text=body)
                    if isinstance(body, str) else httpx.Response(200, json=body))
                response = self.client.post("/chat", json={"message": "Hi"})
                self.assertEqual(response.status_code, 502)
                self.assertEqual(response.json()["detail"], "Invalid inference response")

    def test_validation_does_not_call_upstream(self):
        for payload in ({}, {"message": ""}, {"message": "x" * 4001},
                        {"message": "Hi", "max_tokens": 0},
                        {"message": "Hi", "max_tokens": 513},
                        {"message": "Hi", "temperature": 3}):
            with self.subTest(payload=payload):
                self.assertEqual(self.client.post("/chat", json=payload).status_code, 422)
        self.assertEqual(self.requests, [])

    def test_readiness_and_metrics(self):
        self.assertEqual(self.client.get("/health/ready").json()["status"], "ready")
        self.assertEqual(self.requests[0].url.path, "/health")
        response = self.client.post("/chat", json={"message": ""})
        self.assertTrue(response.headers["X-Request-ID"])
        metrics = self.client.get("/metrics")
        self.assertEqual(metrics.status_code, 200)
        self.assertIn('route="/chat",status_code="422"', metrics.text)
        self.assertNotIn('route="/health/live"', metrics.text)
        self.assertNotIn('route="/health/ready"', metrics.text)
        self.assertNotIn('route="/metrics"', metrics.text)
        self.assertNotIn('request_id=', metrics.text)


if __name__ == "__main__":
    unittest.main()
