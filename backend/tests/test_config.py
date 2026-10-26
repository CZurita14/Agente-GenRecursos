import pytest
from pydantic import ValidationError

from app.config import Ajustes


def test_url_y_modelo_son_obligatorios(monkeypatch):
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    monkeypatch.setenv("LLM_MODEL", "m")
    with pytest.raises(ValidationError):
        Ajustes(_env_file=None)


def test_valores_por_defecto(monkeypatch):
    for k, v in {"DATABASE_URL": "postgresql://x", "LLM_BASE_URL": "http://h/v1", "LLM_MODEL": "m"}.items():
        monkeypatch.setenv(k, v)
    a = Ajustes(_env_file=None)
    assert (a.llm_max_concurrencia, a.llm_timeout_s, a.llm_timeout_revisor_s, a.lease_s) == (4, 120, 240, 360)
    assert a.lease_s > a.llm_timeout_revisor_s
