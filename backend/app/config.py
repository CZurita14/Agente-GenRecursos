"""Configuración del backend, leída del entorno y del `.env` en la raíz del proyecto."""
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

RAIZ = Path(__file__).resolve().parents[2]


class Ajustes(BaseSettings):
    model_config = SettingsConfigDict(env_file=RAIZ / ".env", extra="ignore")

    database_url: str
    # La URL y el modelo del servidor de IA solo viven en la configuración.
    llm_base_url: str
    llm_model: str
    llm_api_key: str = "no-se-necesita"
    llm_max_concurrencia: int = 4
    llm_timeout_s: float = 120
    llm_timeout_revisor_s: float = 240
    lease_s: int = 360
    agentes_dir: Path = Path("agentes")
    api_origen: str = "http://localhost:5173"

    @field_validator("api_origen")
    @classmethod
    def origen_exacto(cls, valor: str) -> str:
        url = urlsplit(valor)
        if (url.scheme not in {"http", "https"} or not url.hostname
                or url.username is not None or url.password is not None
                or url.path or url.query or url.fragment or "*" in valor):
            raise ValueError("API_ORIGEN debe ser un origen HTTP(S) exacto, sin ruta")
        return valor


@lru_cache
def ajustes() -> Ajustes:
    return Ajustes()
