"""Tests for stateless task-level literature metrics."""

from runtime.simflow_helpers.literature.metrics import summarize_literature_metrics


def test_metrics_aggregate_queries_dedup_corpus_full_text_and_claims():
    summary = summarize_literature_metrics(
        [
            {
                "metrics": {
                    "external_query_count": 4,
                    "metadata_query_count": 2,
                    "search_query_count": 2,
                    "graph_query_count": 0,
                    "input_observation_count": 10,
                    "unique_paper_count": 8,
                    "duplicate_count": 2,
                    "cross_checked_count": 4,
                    "local_corpus_record_count": 20,
                    "local_relevant_record_count": 10,
                }
            },
            {
                "metrics": {
                    "external_query_count": 2,
                    "metadata_query_count": 0,
                    "search_query_count": 0,
                    "graph_query_count": 2,
                    "input_observation_count": 5,
                    "unique_paper_count": 4,
                    "duplicate_count": 1,
                    "cross_checked_count": 2,
                }
            },
        ],
        full_text_results=[{"status": "success"}, {"status": "error"}],
        evidence_states=[
            {
                "claim_verifications": [
                    {"claim": "one", "verdict": "verified"},
                    {"claim": "two", "verdict": "contradicted"},
                ]
            }
        ],
    )

    assert summary["external_queries_per_task"] == 3.0
    assert summary["duplicate_rate"] == 0.2
    assert summary["cross_checked_ratio"] == 0.5
    assert summary["local_corpus_hit_rate"] == 0.5
    assert summary["full_text_acquisition_success_rate"] == 0.5
    assert summary["claim_verification_rate"] == 0.5
