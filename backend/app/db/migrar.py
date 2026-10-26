"""Aplicador de migraciones .sql en orden de nombre."""
from pathlib import Path

import psycopg

DIR = Path(__file__).parent / "migraciones"


def aplicar_migraciones(conn: psycopg.Connection) -> list[str]:
    """Aplica las migraciones pendientes y devuelve los nombres aplicados."""
    conn.execute(
        "create table if not exists migracion ("
        "nombre text primary key, aplicada timestamptz not null default now())"
    )
    hechas = {f["nombre"] for f in conn.execute("select nombre from migracion").fetchall()}
    aplicadas = []
    for ruta in sorted(DIR.glob("*.sql")):
        if ruta.name in hechas:
            continue
        with conn.transaction():
            conn.execute(ruta.read_text(encoding="utf-8"))
            conn.execute("insert into migracion (nombre) values (%s)", (ruta.name,))
        aplicadas.append(ruta.name)
    return aplicadas
