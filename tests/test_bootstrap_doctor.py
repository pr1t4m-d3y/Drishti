import json
import logging

import pytest

from drishti import bootstrap as bs


@pytest.fixture()
def clean_env(monkeypatch, tmp_path):
    for k in ("GOOGLE_API_KEY", "GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_CLOUD_PROJECT", "GOOGLE_GENAI_USE_VERTEXAI",
              "GOOGLE_CLOUD_LOCATION", "K_SERVICE"):
        monkeypatch.setenv(k, "x")  # register for restoration, so bootstrap() side effects cannot leak
        monkeypatch.delenv(k)
    monkeypatch.setattr(bs, "SECRETS", tmp_path)
    monkeypatch.setattr(bs, "SA_FILE", tmp_path / "gcp-service-account.json")
    monkeypatch.setattr(bs, "_done", False)
    return tmp_path


def test_offline_when_nothing_provided(clean_env):
    assert bs.credential_mode() == "offline"


def test_api_key_in_secrets_env_is_picked_up(clean_env):
    (clean_env / ".env").write_text("GOOGLE_API_KEY=abc123\n")
    assert bs.credential_mode() == "gemini_api"
    import os

    assert os.environ["GOOGLE_GENAI_USE_VERTEXAI"] == "false"


def test_service_account_file_sets_project_and_vertex(clean_env):
    (clean_env / "gcp-service-account.json").write_text(json.dumps({"project_id": "my-proj", "type": "service_account"}))
    assert bs.credential_mode() == "vertex"
    import os

    assert os.environ["GOOGLE_CLOUD_PROJECT"] == "my-proj" and os.environ["GOOGLE_GENAI_USE_VERTEXAI"] == "true"


def test_explicit_environment_wins_over_secrets_folder(clean_env, monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "from-env")
    (clean_env / ".env").write_text("GOOGLE_API_KEY=from-file\n")
    bs.bootstrap()
    import os

    assert os.environ["GOOGLE_API_KEY"] == "from-env"


def test_doctor_reports_each_requirement_with_a_fix():
    from drishti.doctor import checks

    rows = checks()
    names = {r[0] for r in rows}
    assert {"LLM credentials", "Dataset", "Trained model", "Customers loaded", "Policy documents"} <= names
    assert all(r[3] for r in rows)  # every row says how to fix it


def test_json_log_formatter_embeds_metrics_and_masks_pii():
    from drishti.obs.logging import JsonFormatter

    f = JsonFormatter()
    rec = logging.LogRecord("drishti.metrics", logging.INFO, "", 0, json.dumps({"latency_s": 1.2}), None, None)
    assert json.loads(f.format(rec))["metrics"]["latency_s"] == 1.2
    rec2 = logging.LogRecord("drishti.api", logging.WARNING, "", 0, "contact a.b@x.com PAN ABCDE1234F", None, None)
    out = json.loads(f.format(rec2))
    assert "[EMAIL]" in out["message"] and "[PAN]" in out["message"] and out["severity"] == "WARNING"


def test_reranker_and_embedder_auto_resolve_to_offline_without_credentials(clean_env, monkeypatch):
    monkeypatch.setenv("EMBEDDING_BACKEND", "auto")
    monkeypatch.setenv("RERANKER", "auto")
    from drishti.config import get_settings

    get_settings.cache_clear()
    from drishti.rag.embeddings import resolved_backend
    from drishti.rag.retrieval import LexicalReranker, get_reranker

    assert resolved_backend() == "hash" and isinstance(get_reranker(), LexicalReranker)
    monkeypatch.setenv("EMBEDDING_BACKEND", "hash")
    monkeypatch.setenv("RERANKER", "lexical")
    get_settings.cache_clear()
