import unittest

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver

from math_agent import create_math_agent, evaluate_math, run_turn


class FakeModel:
    def __init__(self) -> None:
        self.messages_seen: list[list] = []

    def bind_tools(self, _tools):
        return self

    def invoke(self, messages):
        self.messages_seen.append(messages)
        if len(self.messages_seen) == 1:
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "evaluate_math",
                        "args": {"expression": "17 * 23"},
                        "id": "math-call-1",
                    }
                ],
            )
        if len(self.messages_seen) == 2:
            return AIMessage(content="17 times 23 is 391.")
        return AIMessage(content="The previous answer was 391.")


class EvaluateMathTests(unittest.TestCase):
    def test_evaluates_arithmetic_and_symbolic_math(self) -> None:
        self.assertEqual(evaluate_math("(12 + 8) * 3 ** 2")["result"], "180")
        self.assertEqual(evaluate_math("diff(x**3, x)")["result"], "3*x**2")

    def test_rejects_unsafe_code_and_large_exponents(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_math("__import__('os').system('echo unsafe')")
        with self.assertRaisesRegex(ValueError, "Exponents"):
            evaluate_math("2 ** 101")


class LangGraphAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.model = FakeModel()
        self.graph = create_math_agent(
            "test-key",
            model=self.model,
            checkpointer=InMemorySaver(),
        )

    def test_waits_for_approval_and_remembers_tool_results_between_questions(self) -> None:
        approvals: list[dict] = []

        def approve(request: dict) -> bool:
            approvals.append(request)
            return True

        first_reply = run_turn(
            self.graph,
            "What is 17 times 23?",
            "test-thread",
            approve,
        )
        self.assertEqual(first_reply, "17 times 23 is 391.")
        self.assertEqual(approvals, [{"tool_name": "evaluate_math", "arguments": {"expression": "17 * 23"}}])

        second_reply = run_turn(
            self.graph,
            "What was the answer to my previous question?",
            "test-thread",
            approve,
        )
        self.assertEqual(second_reply, "The previous answer was 391.")
        follow_up_history = self.model.messages_seen[2]
        self.assertTrue(
            any(
                isinstance(message, HumanMessage)
                and message.content == "What is 17 times 23?"
                for message in follow_up_history
            )
        )
        self.assertTrue(
            any(
                isinstance(message, ToolMessage)
                and '"result": "391"' in message.content
                for message in follow_up_history
            )
        )

    def test_rejected_tool_is_not_executed(self) -> None:
        reply = run_turn(
            self.graph,
            "Calculate 17 times 23.",
            "rejected-thread",
            lambda _request: False,
        )
        self.assertEqual(reply, "17 times 23 is 391.")
        result_message = next(
            message
            for message in self.model.messages_seen[1]
            if isinstance(message, ToolMessage)
        )
        self.assertIn("rejected", result_message.content)
        self.assertNotIn('"result": "391"', result_message.content)

    def test_reviews_each_tool_in_a_batch_individually(self) -> None:
        class MultiToolModel(FakeModel):
            def invoke(self, messages):
                self.messages_seen.append(messages)
                if len(self.messages_seen) == 1:
                    return AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": "evaluate_math",
                                "args": {"expression": "5 + 7"},
                                "id": "math-call-1",
                            },
                            {
                                "name": "out_of_scope",
                                "args": {"topic": "weather"},
                                "id": "scope-call-1",
                            },
                        ],
                    )
                return AIMessage(content="Done.")

        model = MultiToolModel()
        graph = create_math_agent("test-key", model=model, checkpointer=InMemorySaver())
        approvals: list[str] = []

        def approve(request: dict) -> bool:
            approvals.append(request["tool_name"])
            return request["tool_name"] == "evaluate_math"

        reply = run_turn(
            graph,
            "Calculate 5 + 7.",
            "multi-tool-thread",
            approve,
        )

        self.assertEqual(reply, "Done.")
        self.assertEqual(approvals, ["evaluate_math", "out_of_scope"])
        tool_results = [
            message
            for message in model.messages_seen[1]
            if isinstance(message, ToolMessage)
        ]
        self.assertEqual(len(tool_results), 2)
        self.assertIn('"result": "12"', tool_results[0].content)
        self.assertIn("rejected", tool_results[1].content)


if __name__ == "__main__":
    unittest.main()
