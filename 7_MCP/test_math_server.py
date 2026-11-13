import asyncio
import unittest

from mcp import Client

from math_server import evaluate_math, mcp
from math_tools import MathInputError, evaluate_math as evaluate_math_expression


class MathToolTests(unittest.TestCase):
    def test_evaluates_arithmetic_and_symbolic_math(self) -> None:
        self.assertEqual(
            evaluate_math_expression("(12 + 8) * 3 ** 2")["result"], "180"
        )
        self.assertEqual(evaluate_math_expression("diff(x**3, x)")["result"], "3*x**2")
        self.assertEqual(
            evaluate_math_expression("solve(x**2 - 4, x)")["result"], "[-2, 2]"
        )

    def test_returns_exact_and_approximate_results(self) -> None:
        result = evaluate_math_expression("sqrt(2)")
        self.assertEqual(result["result"], "sqrt(2)")
        self.assertTrue(result["approximation"].startswith("1.41421356237"))

    def test_rejects_python_code_and_unsafe_exponents(self) -> None:
        with self.assertRaises(MathInputError):
            evaluate_math_expression("__import__('os').system('echo unsafe')")
        with self.assertRaisesRegex(MathInputError, "Exponents"):
            evaluate_math_expression("2 ** 101")

    def test_mcp_tool_returns_classified_math_errors(self) -> None:
        result = evaluate_math("1 / 0")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error_type"], "division_by_zero")

    def test_server_exposes_tools_through_mcp(self) -> None:
        async def inspect_server() -> None:
            async with Client(mcp) as client:
                listing = await client.list_tools()
                names = {tool.name for tool in listing.tools}
                self.assertEqual(
                    names, {"evaluate_math", "out_of_scope", "handle_errors"}
                )
                evaluator = next(
                    tool for tool in listing.tools if tool.name == "evaluate_math"
                )
                self.assertIn("SymPy", evaluator.description)
                self.assertIn("expression", evaluator.input_schema["properties"])
                result = await client.call_tool(
                    "evaluate_math", {"expression": "12 * 8"}
                )
                self.assertFalse(result.is_error)
                self.assertEqual(result.structured_content["result"], "96")
                failed_result = await client.call_tool(
                    "evaluate_math", {"expression": "1 / 0"}
                )
                self.assertFalse(failed_result.is_error)
                self.assertEqual(
                    failed_result.structured_content["error_type"],
                    "division_by_zero",
                )
                out_of_scope_result = await client.call_tool(
                    "out_of_scope", {"topic": "weather"}
                )
                self.assertIn(
                    "mathematics",
                    out_of_scope_result.structured_content["message"],
                )
                handled_error = await client.call_tool(
                    "handle_errors", {"error_type": "division_by_zero"}
                )
                self.assertIn(
                    "Division by zero",
                    handled_error.structured_content["message"],
                )

        asyncio.run(inspect_server())


if __name__ == "__main__":
    unittest.main()
