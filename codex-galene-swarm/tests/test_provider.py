import unittest
import io
import json
import urllib.error
from unittest.mock import patch

from codex_galene_swarm.models import TaskContract
from codex_galene_swarm.providers import GaleneProvider, ProviderError, build_worker_prompt


class ProviderPromptTests(unittest.TestCase):
    def test_prompt_contains_boundaries(self) -> None:
        contract = TaskContract(
            task_id="core",
            role="implementer",
            objective="Implement the function",
            allowed_files=["src/core.py"],
            context="untrusted repository text",
        )
        prompt = build_worker_prompt("Overall goal", contract)
        self.assertIn("src/core.py", prompt)
        self.assertIn("<context>", prompt)
        self.assertIn("Do not invent requirements", prompt)

    def test_truncated_completion_fails_with_safe_metadata(self) -> None:
        provider = GaleneProvider(api_key="test-key", base_url="https://example.invalid/v1")
        contract = TaskContract(task_id="one", role="analyst", objective="Answer")
        payload = {
            "id": "request-1",
            "choices": [{"message": {"content": "partial"}, "finish_reason": "length"}],
            "usage": {"completion_tokens": 100},
        }
        with patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps(payload).encode())):
            with self.assertRaises(ProviderError) as raised:
                provider.generate("goal", contract)
        self.assertEqual("length", raised.exception.metadata["finish_reason"])
        self.assertEqual("request-1", raised.exception.metadata["provider_request_id"])

    def test_http_failure_retains_status_without_response_body(self) -> None:
        provider = GaleneProvider(api_key="test-key", base_url="https://example.invalid/v1")
        contract = TaskContract(task_id="one", role="analyst", objective="Answer")
        error = urllib.error.HTTPError("https://example.invalid/v1", 429, "limit", {}, None)
        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(ProviderError) as raised:
                provider.generate("goal", contract)
        self.assertEqual({"http_status": 429}, raised.exception.metadata)

    def test_requests_supported_low_reasoning_effort(self) -> None:
        provider = GaleneProvider(api_key="test-key", base_url="https://example.invalid/v1")
        contract = TaskContract(task_id="one", role="analyst", objective="Answer")
        payload = {"choices": [{"message": {"content": "answer"}, "finish_reason": "stop"}]}
        with patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps(payload).encode())) as call:
            provider.generate("goal", contract)
        request_body = json.loads(call.call_args.args[0].data)
        self.assertEqual("low", request_body["reasoning_effort"])
        self.assertFalse(request_body["enable_thinking"])
        self.assertFalse(request_body["chat_template_kwargs"]["enable_thinking"])
        self.assertNotIn("max_tokens", request_body)

    def test_explicit_large_completion_budget_reaches_provider(self) -> None:
        provider = GaleneProvider(api_key="test-key", base_url="https://example.invalid/v1")
        contract = TaskContract.from_dict({
            "task_id": "large", "role": "analyst", "objective": "Answer", "max_tokens": 16000,
        })
        payload = {"choices": [{"message": {"content": "answer"}, "finish_reason": "stop"}]}
        with patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps(payload).encode())) as call:
            provider.generate("goal", contract)
        request_body = json.loads(call.call_args.args[0].data)
        self.assertEqual(16000, request_body["max_tokens"])

    def test_research_can_disable_local_provider_timeout(self) -> None:
        provider = GaleneProvider(api_key="test-key", base_url="https://example.invalid/v1", timeout_seconds=0)
        contract = TaskContract(task_id="one", role="analyst", objective="Answer")
        payload = {"choices": [{"message": {"content": "answer"}, "finish_reason": "stop"}]}
        with patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps(payload).encode())) as call:
            provider.generate("goal", contract)
        self.assertEqual({}, call.call_args.kwargs)


if __name__ == "__main__":
    unittest.main()
