import unittest
from unittest.mock import patch

from langchain_core.messages import AIMessage, HumanMessage

from math_agent import (
    MAX_TOOL_CALLS,
    TOOLS,
    create_math_agent,
    evaluate_math,
    evaluate_math_tool,
    handle_errors_tool,
    out_of_scope_tool,
    run_agent,
)


class EvaluateMathTests(unittest.TestCase):
    def test_evaluates_arithmetic_and_symbolic_math(self) -> None:
        self.assertEqual(evaluate_math("(12 + 8) * 3 ** 2")["result"], "180")
        self.assertEqual(evaluate_math("diff(x**3, x)")["result"], "3*x**2")
        self.assertEqual(evaluate_math("solve(x**2 - 4, x)")["result"], "[-2, 2]")

    def test_returns_exact_and_approximate_numeric_results(self) -> None:
        result = evaluate_math("sqrt(2)")
        self.assertEqual(result["result"], "sqrt(2)")
        self.assertTrue(result["approximation"].startswith("1.41421356237"))

    def test_rejects_python_code_and_unreasonably_large_exponents(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_math("__import__('os').system('echo unsafe')")
        with self.assertRaisesRegex(ValueError, "Exponents"):
            evaluate_math("2 ** 101")

    def test_rejects_invalid_factorial_arguments(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-negative integer"):
            evaluate_math("factorial([2])")

    def test_langchain_tool_returns_a_friendly_math_error(self) -> None:
        result = evaluate_math_tool.invoke({"expression": "1 / 0"})
        self.assertEqual(result["error_type"], "division_by_zero")
        self.assertIn("details", result)

    def test_out_of_scope_and_error_tools_preserve_expected_responses(self) -> None:
        out_of_scope = out_of_scope_tool.invoke({"topic": "weather"})
        self.assertIn("mathematics", out_of_scope["message"])
        self.assertIn(
            "Division by zero",
            handle_errors_tool.invoke({"error_type": "division_by_zero"})["message"],
        )


class LangChainAgentTests(unittest.TestCase):
    @patch("math_agent.create_agent")
    @patch("math_agent.ChatOpenAI")
    def test_configures_langchain_agent_with_nvidia_and_the_tool_limit(
        self, chat_model, create_agent_mock
    ) -> None:
        create_math_agent("test-key")

        chat_model.assert_called_once()
        self.assertEqual(
            chat_model.call_args.kwargs["model"],
            "nvidia/nemotron-3.5-super-vl-120b-a12b",
        )
        self.assertEqual(chat_model.call_args.kwargs["api_key"], "test-key")
        self.assertEqual(
            create_agent_mock.call_args.kwargs["tools"],
            TOOLS,
        )
        self.assertEqual(
            create_agent_mock.call_args.kwargs["middleware"][0].run_limit,
            MAX_TOOL_CALLS,
        )
        self.assertEqual(
            create_agent_mock.call_args.kwargs["middleware"][0].exit_behavior,
            "end",
        )

    @patch("math_agent.create_math_agent")
    def test_returns_final_assistant_message(self, create_agent_mock) -> None:
        class FakeAgent:
            def invoke(self, _input):
                return {
                    "messages": [
                        HumanMessage(content="What is 17 times 23?"),
                        AIMessage(content="17 times 23 is 391."),
                    ]
                }

        create_agent_mock.return_value = FakeAgent()
        self.assertEqual(
            run_agent("test-key", "What is 17 times 23?"),
            "17 times 23 is 391.",
        )


if __name__ == "__main__":
    unittest.main()
