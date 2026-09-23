import unittest
from unittest.mock import patch

from mcp import Client

from codex_galene_swarm.server import get_orchestrator, mcp, swarm_start


class McpServerTests(unittest.IsolatedAsyncioTestCase):
    async def test_exposes_the_four_swarm_tools(self) -> None:
        async with Client(mcp) as client:
            response = await client.list_tools()
        names = {tool.name for tool in response.tools}
        self.assertEqual(
            {"swarm_start", "swarm_status", "swarm_result", "swarm_cancel"},
            names,
        )

    async def test_team_policy_forces_jev_even_when_client_omits_it(self) -> None:
        with patch("codex_galene_swarm.server.get_orchestrator") as get_orchestrator:
            with patch.dict("os.environ", {"SWARM_REQUIRE_JEV": "1"}):
                swarm_start("goal", [], False)
        self.assertTrue(get_orchestrator.return_value.start.call_args.kwargs["require_jev"])

    async def test_team_policy_requires_jev_key_at_startup(self) -> None:
        get_orchestrator.cache_clear()
        with patch.dict("os.environ", {"SWARM_REQUIRE_JEV": "1"}, clear=True):
            with self.assertRaisesRegex(ValueError, "TYPESAFE_API_KEY"):
                get_orchestrator()


if __name__ == "__main__":
    unittest.main()
