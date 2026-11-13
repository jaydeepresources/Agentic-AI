import unittest
from unittest.mock import Mock

from hr_policy_bot import PolicyChunk
from hr_policy_rag_agent import (
    RetrievedChunk,
    ensure_valid_citations,
    parse_json_object,
    rerank_candidates,
    verify_answer,
)


class RagAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.candidates = [
            RetrievedChunk(
                PolicyChunk("HR Manual.pdf", 4, 1, "Leave needs manager approval."),
                0.83,
                "S1",
            ),
            RetrievedChunk(
                PolicyChunk("HR Manual.pdf", 7, 2, "Annual leave is 20 days."),
                0.72,
                "S2",
            ),
        ]

    def test_reranker_orders_only_the_supplied_candidates(self) -> None:
        client = Mock()
        client.chat.completions.create.return_value.choices = [
            Mock(message=Mock(content='{"ranked_ids":["S2","S1"]}'))
        ]
        result = rerank_candidates(client, "How much leave?", self.candidates)
        self.assertEqual([item.evidence_id for item in result], ["S2", "S1"])

    def test_reranker_rejects_missing_or_unknown_ids(self) -> None:
        client = Mock()
        client.chat.completions.create.return_value.choices = [
            Mock(message=Mock(content='{"ranked_ids":["S1","S3"]}'))
        ]
        with self.assertRaisesRegex(ValueError, "every candidate ID"):
            rerank_candidates(client, "How much leave?", self.candidates)

    def test_verifier_requires_valid_result_fields(self) -> None:
        client = Mock()
        client.chat.completions.create.return_value.choices = [
            Mock(
                message=Mock(
                    content='{"verified":true,"answer":"Annual leave is 20 days [S2]."}'
                )
            )
        ]
        verified, answer = verify_answer(
            client,
            "How much leave?",
            "Annual leave is 20 days [S2].",
            self.candidates,
        )
        self.assertTrue(verified)
        self.assertEqual(answer, "Annual leave is 20 days [S2].")

    def test_citation_validation_rejects_unknown_evidence(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown citations"):
            ensure_valid_citations("The answer is in [S3].", self.candidates)

    def test_json_parser_accepts_fenced_json(self) -> None:
        self.assertEqual(
            parse_json_object('```json\n{"ranked_ids":["S1"]}\n```'),
            {"ranked_ids": ["S1"]},
        )


if __name__ == "__main__":
    unittest.main()
