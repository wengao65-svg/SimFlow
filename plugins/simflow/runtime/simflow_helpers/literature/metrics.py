"""Stateless task-level metrics for literature helper results."""

from __future__ import annotations

from typing import Any, Iterable


def summarize_literature_metrics(
    results: Iterable[dict[str, Any]],
    *,
    full_text_results: Iterable[dict[str, Any]] = (),
    evidence_states: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    """Aggregate anonymous counters without creating session or project state."""
    result_items = list(results)
    full_text_items = list(full_text_results)
    evidence_items = list(evidence_states)

    observation_count = sum(
        int((item.get("metrics") or {}).get("input_observation_count") or 0)
        for item in result_items
    )
    unique_count = sum(
        int((item.get("metrics") or {}).get("unique_paper_count") or 0)
        for item in result_items
    )
    duplicate_count = sum(
        int((item.get("metrics") or {}).get("duplicate_count") or 0)
        for item in result_items
    )
    cross_checked_count = sum(
        int((item.get("metrics") or {}).get("cross_checked_count") or 0)
        for item in result_items
    )
    local_records = sum(
        int((item.get("metrics") or {}).get("local_corpus_record_count") or 0)
        for item in result_items
    )
    local_relevant = sum(
        int((item.get("metrics") or {}).get("local_relevant_record_count") or 0)
        for item in result_items
    )
    full_text_attempts = len(full_text_items)
    full_text_successes = sum(1 for item in full_text_items if item.get("status") == "success")
    claim_checks = sum(len(item.get("claim_verifications") or []) for item in evidence_items)
    verified_claims = sum(
        1
        for item in evidence_items
        for verification in item.get("claim_verifications") or []
        if verification.get("verdict") == "verified"
    )

    return {
        "task_count": len(result_items),
        "external_query_count": sum(
            int((item.get("metrics") or {}).get("external_query_count") or 0)
            for item in result_items
        ),
        "external_queries_per_task": (
            sum(
                int((item.get("metrics") or {}).get("external_query_count") or 0)
                for item in result_items
            ) / len(result_items)
            if result_items
            else 0.0
        ),
        "metadata_query_count": sum(
            int((item.get("metrics") or {}).get("metadata_query_count") or 0)
            for item in result_items
        ),
        "search_query_count": sum(
            int((item.get("metrics") or {}).get("search_query_count") or 0)
            for item in result_items
        ),
        "graph_query_count": sum(
            int((item.get("metrics") or {}).get("graph_query_count") or 0)
            for item in result_items
        ),
        "input_observation_count": observation_count,
        "unique_paper_count": unique_count,
        "duplicate_rate": duplicate_count / observation_count if observation_count else 0.0,
        "cross_checked_ratio": cross_checked_count / unique_count if unique_count else 0.0,
        "local_corpus_hit_rate": local_relevant / local_records if local_records else 0.0,
        "full_text_acquisition_attempts": full_text_attempts,
        "full_text_acquisition_success_rate": (
            full_text_successes / full_text_attempts if full_text_attempts else 0.0
        ),
        "claim_verification_attempts": claim_checks,
        "claim_verification_rate": verified_claims / claim_checks if claim_checks else 0.0,
    }


__all__ = ["summarize_literature_metrics"]
