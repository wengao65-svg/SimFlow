"""Tests for legal full-text candidates and optional institutional adapters."""

from http.client import RemoteDisconnected

import pytest

from runtime.simflow_helpers.literature import fulltext
from runtime.simflow_helpers.literature.fulltext import collect_full_text_candidates, download_full_text
from runtime.simflow_helpers.literature.retry import is_retryable


def test_full_text_candidates_prefer_local_then_open_access():
    result = collect_full_text_candidates({
        "observations": [{
            "source": "local_pdf",
            "full_text": {"path": "papers/paper.pdf", "verified": True, "is_pdf": True},
        }],
        "open_access_locations": [{
            "pdf_url": "https://arxiv.org/pdf/2301.01234",
            "landing_page_url": "https://arxiv.org/abs/2301.01234",
            "is_oa": True,
            "host_type": "arXiv",
            "version": "2301.01234v2",
        }],
    })

    assert [item["access_basis"] for item in result["candidates"]] == ["user_provided", "open_access"]
    assert result["issues"] == []


def test_optional_institutional_adapter_requires_declared_entitlement():
    result = collect_full_text_candidates(
        {"observations": [], "open_access_locations": []},
        institutional_adapter=lambda paper: [{
            "url": "https://publisher.example/paper.pdf",
            "source": "publisher",
            "access_basis": "institutional_entitlement",
        }],
    )

    assert result["candidates"][0]["access_basis"] == "institutional_entitlement"


def test_scihub_and_libgen_adapter_results_are_rejected():
    result = collect_full_text_candidates(
        {"observations": [], "open_access_locations": []},
        institutional_adapter=lambda paper: [
            {"url": "https://sci-hub.example/paper", "source": "Sci-Hub", "access_basis": "institutional_entitlement"},
            {"url": "https://libgen.example/paper", "source": "LibGen", "access_basis": "publisher_api"},
        ],
    )

    assert result["candidates"] == []
    assert [issue["code"] for issue in result["issues"]] == [
        "disallowed_full_text_source",
        "disallowed_full_text_source",
    ]


def test_invalid_local_pdf_and_disallowed_oa_location_are_not_candidates():
    result = collect_full_text_candidates({
        "observations": [{
            "source": "local_pdf",
            "full_text": {"path": "papers/broken.pdf", "verified": False, "is_pdf": True},
        }],
        "open_access_locations": [{
            "pdf_url": "https://libgen.example/paper.pdf",
            "is_oa": True,
            "host_type": "LibGen",
        }],
    })

    assert result["candidates"] == []
    assert result["issues"] == [{"code": "disallowed_full_text_source", "source": "LibGen"}]


def test_downloader_rejects_user_provided_and_disallowed_remote_sources(tmp_path):
    with pytest.raises(ValueError, match="Only OA"):
        download_full_text(
            {"url": "https://example.org/paper.pdf", "access_basis": "user_provided"},
            tmp_path / "paper.pdf",
        )

    with pytest.raises(ValueError, match="disallowed"):
        download_full_text(
            {"url": "https://sci-hub.example/paper", "source": "Sci-Hub", "access_basis": "open_access"},
            tmp_path / "paper.pdf",
        )


def test_remote_disconnect_is_retryable_and_download_recovers(monkeypatch, tmp_path):
    calls = {"count": 0}

    def fake_download(url):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RemoteDisconnected("temporary disconnect")
        return b"%PDF-1.4\nfixture"

    monkeypatch.setattr(fulltext, "_download_bytes", fake_download)
    monkeypatch.setattr("runtime.simflow_helpers.literature.retry.time.sleep", lambda seconds: None)

    result = download_full_text(
        {"url": "https://example.org/paper.pdf", "source": "repository", "access_basis": "open_access"},
        tmp_path / "paper.pdf",
    )

    assert is_retryable(RemoteDisconnected("temporary")) is True
    assert calls["count"] == 2
    assert result["status"] == "success"
