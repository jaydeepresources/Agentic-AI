import unittest
from unittest.mock import patch

from math_agent import MAX_TOOL_CALLS, evaluate_math, handle_errors, run_agent


def tool_message(name: str, arguments: dict[str, str], call_id: str = "call_1") -> dict:
    import json

    return {
        "role": "assistant",
        "tool_calls": [
            {
                "id": call_id,
                "type": "function",
                "function": {
                    "name": name,
                    "arguments": json.dumps(arguments),
                },
            }
        ],
    }


class EvaluateMathTests(unittest.TestCase):
    def test_evaluates_parentheses_and_exponentiation(self) -> None:
        self.assertEqual(evaluate_math("(12 + 8) * 3 ** 2")["result"], "180")

    def test_evaluates_symbolic_calculus_and_algebra(self) -> None:
        self.assertEqual(evaluate_math("diff(x**3, x)")["result"], "3*x**2")
        self.assertEqual(evaluate_math("solve(x**2 - 4, x)")["result"], "[-2, 2]")

    def test_returns_exact_and_approximate_numeric_results(self) -> None:
        result = evaluate_math("sqrt(2)")
        self.assertEqual(result["result"], "sqrt(2)")
        self.assertTrue(result["approximation"].startswith("1.41421356237"))

    def test_rejects_python_code_instead_of_executing_it(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_math("__import__('os').system('echo unsafe')")

    def test_rejects_unreasonably_large_exponents(self) -> None:
        with self.assertRaisesRegex(ValueError, "Exponents"):
            evaluate_math("2 ** 101")

    def test_rejects_invalid_factorial_arguments(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-negative integer"):
            evaluate_math("factorial([2])")


class ToolCallingTests(unittest.TestCase):
    @patch("math_agent.request_completion")
    def test_calls_math_tool_then_returns_model_answer(self, request_completion) -> None:
        request_completion.side_effect = [
            tool_message("evaluate_math", {"expression": "17 * 23"}),
            {"role": "assistant", "content": "17 times 23 is 391."},
        ]

        self.assertEqual(run_agent("test-key", "What is 17 times 23?"), "17 times 23 is 391.")
        self.assertEqual(request_completion.call_count, 2)
        follow_up = request_completion.call_args_list[1].args[1]
        self.assertEqual(follow_up[-1]["role"], "tool")
        self.assertIn('"result": "391"', follow_up[-1]["content"])

    @patch("math_agent.request_completion")
    def test_routes_unrelated_question_to_out_of_scope(self, request_completion) -> None:
        request_completion.side_effect = [
            tool_message("out_of_scope", {"topic": "weather"}),
            {"role": "assistant", "content": "I can help with mathematics questions."},
        ]

        self.assertEqual(
            run_agent("test-key", "What is the weather?"),
            "I can help with mathematics questions.",
        )
        self.assertEqual(request_completion.call_count, 2)

    @patch("math_agent.request_completion")
    def test_routes_math_failure_to_error_handler(self, request_completion) -> None:
        request_completion.side_effect = [
            tool_message("evaluate_math", {"expression": "1 / 0"}),
            tool_message(
                "handle_errors",
                {
                    "error_type": "division_by_zero",
                    "details": "division by zero",
                },
                call_id="call_2",
            ),
            {"role": "assistant", "content": "Division by zero is undefined."},
        ]

        self.assertEqual(
            run_agent("test-key", "What is 1 divided by 0?"),
            "Division by zero is undefined.",
        )
        self.assertEqual(request_completion.call_count, 3)

    @patch("math_agent.request_completion")
    def test_stops_before_exceeding_tool_call_limit(self, request_completion) -> None:
        request_completion.return_value = {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": f"call_{index}",
                    "type": "function",
                    "function": {
                        "name": "out_of_scope",
                        "arguments": '{"topic":"other"}',
                    },
                }
                for index in range(MAX_TOOL_CALLS + 1)
            ],
        }

        result = run_agent("test-key", "Tell me about weather.")

        self.assertIn("limit of 10 tool calls", result)
        self.assertEqual(request_completion.call_count, 1)

    def test_handles_genuine_errors_with_friendly_messages(self) -> None:
        self.assertIn(
            "Division by zero",
            handle_errors("division_by_zero")["message"],
        )


if __name__ == "__main__":
    unittest.main()
