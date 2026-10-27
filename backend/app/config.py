"""Configuración del backend, leída del entorno y del `.env` en la raíz del proyecto."""
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
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
    api_origen: str = "https://localhost:5173"
    auth_secreto: SecretStr | None = Field(default=None, min_length=32)
    entorno: Literal["desarrollo", "produccion"] = "produccion"
    smtp_modo: Literal["deshabilitado", "consola", "smtp"] = "deshabilitado"
    smtp_host: str = ""
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_remitente: str = ""
    smtp_usuario: str = ""
    smtp_clave: SecretStr | None = None
    pdf_max_bytes: int = Field(default=10 * 1024 * 1024, ge=1, le=50 * 1024 * 1024)
    pdf_timeout_s: float = Field(default=20, gt=0, le=120)
    pdf_memoria_mb: int = Field(default=512, ge=128, le=2048)
    pdf_recepcion_timeout_s: float = Field(default=30, gt=0, le=120)
    api_json_max_bytes: int = Field(default=1024 * 1024, ge=1, le=4 * 1024 * 1024)
    api_json_timeout_s: float = Field(default=30, gt=0, le=120)

    @model_validator(mode="after")
    def https_en_produccion(self):
        if self.entorno == "produccion" and not self.api_origen.startswith("https://"):
            raise ValueError("API_ORIGEN requiere HTTPS en producción")
        return self

    @field_validator("api_origen")
    @classmethod
    def origen_exacto(cls, valor: str) -> str:
        url = urlsplit(valor)
        # Evaluar port también detecta números fuera de rango o no numéricos.
        url.port
        if (url.scheme not in {"http", "https"} or not url.hostname
                or url.username is not None or url.password is not None
                or url.path or url.query or url.fragment or "*" in valor):
            raise ValueError("API_ORIGEN debe ser un origen HTTP(S) exacto, sin ruta")
        return valor


@lru_cache
def ajustes() -> Ajustes:
    return Ajustes()
