import asyncio
import unittest
from unittest.mock import patch

from mcp.types import CallToolResult, TextContent, Tool

from math_client import _tool_result_for_model, openai_tool_definitions, run_agent


class MathClientTests(unittest.TestCase):
    def test_converts_discovered_mcp_tool_to_openai_format(self) -> None:
        tool = Tool(
            name="evaluate_math",
            description="Evaluate a safe math expression.",
            input_schema={
                "type": "object",
                "properties": {"expression": {"type": "string"}},
            },
        )
        self.assertEqual(
            openai_tool_definitions([tool]),
            [
                {
                    "type": "function",
                    "function": {
                        "name": "evaluate_math",
                        "description": "Evaluate a safe math expression.",
                        "parameters": tool.input_schema,
                    },
                }
            ],
        )

    def test_formats_structured_and_error_mcp_results_for_the_model(self) -> None:
        structured = CallToolResult(
            content=[],
            is_error=False,
            structured_content={"ok": True, "result": 8},
        )
        self.assertEqual(
            _tool_result_for_model(structured),
            {"ok": True, "result": 8},
        )

        error = CallToolResult(
            content=[
                TextContent(type="text", text="Division by zero is undefined.")
            ],
            is_error=True,
        )
        self.assertEqual(
            _tool_result_for_model(error),
            {
                "ok": False,
                "error_type": "division_by_zero",
                "details": "Division by zero is undefined.",
            },
        )

    def test_react_loop_calls_mcp_tool_and_uses_its_result(self) -> None:
        class FakeClient:
            call: tuple[str, dict[str, str]] | None = None

            async def call_tool(
                self, name: str, arguments: dict[str, str]
            ) -> CallToolResult:
                self.call = (name, arguments)
                return CallToolResult(
                    content=[],
                    is_error=False,
                    structured_content={"ok": True, "result": 391},
                )

        fake_client = FakeClient()
        tool = Tool(
            name="evaluate_math",
            description="Evaluate a safe math expression.",
            input_schema={"type": "object"},
        )
        with patch(
            "math_client.request_completion",
            side_effect=[
                {
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "function": {
                                "name": "evaluate_math",
                                "arguments": '{"expression": "17 * 23"}',
                            },
                        }
                    ]
                },
                {"content": "17 times 23 is 391."},
            ],
        ):
            reply = asyncio.run(
                run_agent("test-key", "What is 17 times 23?", fake_client, [tool])
            )

        self.assertEqual(
            fake_client.call, ("evaluate_math", {"expression": "17 * 23"})
        )
        self.assertEqual(reply, "17 times 23 is 391.")


if __name__ == "__main__":
    unittest.main()
