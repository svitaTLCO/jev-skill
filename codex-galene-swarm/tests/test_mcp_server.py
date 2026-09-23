import unittest

from mcp import Client

from codex_galene_swarm.server import mcp


class McpServerTests(unittest.IsolatedAsyncioTestCase):
    async def test_exposes_the_four_swarm_tools(self) -> None:
        async with Client(mcp) as client:
            response = await client.list_tools()
        names = {tool.name for tool in response.tools}
        self.assertEqual(
            {"swarm_start", "swarm_status", "swarm_result", "swarm_cancel"},
            names,
        )


if __name__ == "__main__":
    unittest.main()
