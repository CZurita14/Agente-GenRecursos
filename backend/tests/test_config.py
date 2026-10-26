import pytest
from pydantic import ValidationError

from app.config import Ajustes

VARS = ["DATABASE_URL", "LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY", "LLM_MAX_CONCURRENCIA",
        "LLM_TIMEOUT_S", "LLM_TIMEOUT_REVISOR_S", "LEASE_S", "AGENTES_DIR"]


def _limpiar(monkeypatch):
    for v in VARS:
        monkeypatch.delenv(v, raising=False)


def test_url_y_modelo_son_obligatorios(monkeypatch):
    _limpiar(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    monkeypatch.setenv("LLM_MODEL", "m")
    with pytest.raises(ValidationError) as exc:
        Ajustes(_env_file=None)
    assert [e["loc"] for e in exc.value.errors()] == [("llm_base_url",)]


def test_valores_por_defecto(monkeypatch):
    _limpiar(monkeypatch)
    for k, v in {"DATABASE_URL": "postgresql://x", "LLM_BASE_URL": "http://h/v1", "LLM_MODEL": "m"}.items():
        monkeypatch.setenv(k, v)
    a = Ajustes(_env_file=None)
    assert (a.llm_max_concurrencia, a.llm_timeout_s, a.llm_timeout_revisor_s, a.lease_s) == (4, 120, 240, 360)
    assert a.lease_s > a.llm_timeout_revisor_s
