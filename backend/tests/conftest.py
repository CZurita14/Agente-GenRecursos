"""Fixtures compartidas de las pruebas del backend."""
import uuid

import psycopg
import pytest
from psycopg.rows import dict_row

from app.config import ajustes
from app.db.conexion import conectar
from app.db.migrar import aplicar_migraciones


@pytest.fixture(autouse=True)
def _limpiar_ajustes():
    ajustes.cache_clear()
    yield
    ajustes.cache_clear()


@pytest.fixture
def conn():
    """Conexión autocommit a un esquema temporal con las migraciones aplicadas.
    """
    esquema = f"prueba_{uuid.uuid4().hex[:8]}"
    c = conectar()
    c.autocommit = True
    c.execute(f"create schema {esquema}")
    c.execute(f"set search_path to {esquema}")
    aplicar_migraciones(c)
    c._esquema = esquema
    yield c
    c.execute(f"drop schema {esquema} cascade")
    c.close()


@pytest.fixture
def nueva_conexion(conn):
    """Fábrica de conexiones extra sobre el mismo esquema (concurrencia)."""
    abiertas: list[psycopg.Connection] = []

    def _nueva() -> psycopg.Connection:
        c = conectar()
        c.autocommit = True
        c.execute(f"set search_path to {conn._esquema}")
        abiertas.append(c)
        return c

    yield _nueva
    for c in abiertas:
        c.close()
