import unittest

from codex_galene_swarm.models import TaskContract
from codex_galene_swarm.providers import build_worker_prompt


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


if __name__ == "__main__":
    unittest.main()
