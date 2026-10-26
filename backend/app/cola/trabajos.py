"""Cola durable de trabajos en PostgreSQL: lease por worker y carril por asignatura.

Cada función abre su propia transacción; funciona sobre conexiones autocommit y,
dentro de una transacción externa, como savepoint.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

ACTIVOS = ("generando", "verificando", "revisando")

# Candidatos: pendientes ya disponibles, o activos con lease vencido (worker caído).
# El OR va entre paréntesis antes del NOT EXISTS. El NOT EXISTS descarta la
# asignatura si OTRO trabajo ocupa el carril, con lease vigente o no: un pendiente
# de un carril cuyo activo venció chocaría siempre con trabajo_carril y taparía la
# recuperación de ese activo.
_TOMAR = """
select t.id from trabajo t
where (
    (t.estado in ('en_cola', 'en_espera') and t.disponible_desde <= now())
    or (t.estado in ('generando', 'verificando', 'revisando')
        and coalesce(t.lease_hasta, '-infinity') < now())
  )
  and not exists (
    select 1 from trabajo o
    where o.asignatura_id = t.asignatura_id and o.id <> t.id
      and o.estado in ('generando', 'verificando', 'revisando')
  )
order by t.creado, t.id
limit 1
for update of t skip locked
"""


@dataclass(frozen=True)
class Ambito:
    tipo: Literal["clase", "momento", "asignatura"]
    id: str


@dataclass(frozen=True)
class Trabajo:
    id: UUID
    asignatura_id: UUID
    agente: str
    ambito: Ambito
    herramienta: str
    parametros: dict
    estado: str
    lotes_total: int
    lotes_hechos: int
    rondas_revision: int
    intentos: int
    worker_id: str | None
    lease_hasta: datetime | None
    disponible_desde: datetime
    tokens_entrada: int
    tokens_salida: int
    error: str | None
    creado: datetime
    actualizado: datetime


def _trabajo(f: dict) -> Trabajo:
    f = dict(f)
    ambito = Ambito(f.pop("ambito_tipo"), f.pop("ambito_id"))
    return Trabajo(ambito=ambito, **f)


def encolar(conn: psycopg.Connection, *, asignatura_id: UUID, agente: str, ambito: Ambito,
            herramienta: str, parametros: dict) -> UUID:
    with conn.transaction():
        f = conn.execute(
            "insert into trabajo (asignatura_id, agente, ambito_tipo, ambito_id, herramienta,"
            " parametros) values (%s, %s, %s, %s, %s, %s) returning id",
            (asignatura_id, agente, ambito.tipo, ambito.id, herramienta, Jsonb(parametros)),
        ).fetchone()
    return f["id"]


def tomar_siguiente(conn: psycopg.Connection, worker_id: str, lease_s: int) -> Trabajo | None:
    """Toma el trabajo más antiguo disponible y lo pasa a generando con lease nuevo.

    Devuelve None si no hay candidato o si otro worker ganó el carril a la vez
    (UniqueViolation en trabajo_carril).
    """
    try:
        with conn.transaction():
            f = conn.execute(_TOMAR).fetchone()
            if f is None:
                return None
            f = conn.execute(
                "update trabajo set estado = 'generando', worker_id = %s,"
                " lease_hasta = now() + make_interval(secs => %s), actualizado = now()"
                " where id = %s returning *",
                (worker_id, lease_s, f["id"]),
            ).fetchone()
    except psycopg.errors.UniqueViolation:
        return None
    return _trabajo(f)


def renovar_lease(conn: psycopg.Connection, trabajo_id: UUID, worker_id: str,
                  lease_s: int) -> bool:
    """Extiende el lease; False si el trabajo ya no es de este worker o no está activo."""
    with conn.transaction():
        f = conn.execute(
            "update trabajo set lease_hasta = now() + make_interval(secs => %s),"
            " actualizado = now()"
            " where id = %s and worker_id = %s and estado = any(%s) returning id",
            (lease_s, trabajo_id, worker_id, list(ACTIVOS)),
        ).fetchone()
    return f is not None


def registrar_avance(conn: psycopg.Connection, trabajo_id: UUID, *, estado: str | None = None,
                     lotes_total: int | None = None, lotes_hechos: int | None = None,
                     rondas_revision: int | None = None,
                     tokens: tuple[int, int] = (0, 0)) -> None:
    """Actualiza los campos dados (None = sin cambio) y suma los tokens."""
    with conn.transaction():
        conn.execute(
            "update trabajo set estado = coalesce(%s, estado),"
            " lotes_total = coalesce(%s, lotes_total),"
            " lotes_hechos = coalesce(%s, lotes_hechos),"
            " rondas_revision = coalesce(%s, rondas_revision),"
            " tokens_entrada = tokens_entrada + %s, tokens_salida = tokens_salida + %s,"
            " actualizado = now() where id = %s",
            (estado, lotes_total, lotes_hechos, rondas_revision, tokens[0], tokens[1],
             trabajo_id),
        )


def terminar(conn: psycopg.Connection, trabajo_id: UUID,
             estado: Literal["listo", "requiere_revision", "error"],
             error: str | None = None) -> None:
    """Fija el estado final y libera el lease (y con él el carril)."""
    with conn.transaction():
        conn.execute(
            "update trabajo set estado = %s, error = %s, worker_id = null, lease_hasta = null,"
            " actualizado = now() where id = %s",
            (estado, error, trabajo_id),
        )


def poner_en_espera(conn: psycopg.Connection, trabajo_id: UUID) -> datetime:
    """Suma un intento, libera el carril y devuelve cuándo vuelve a estar disponible.

    Espera = min(30·2^(intentos−1), 600) s con los intentos ya sumados; en el SET,
    `intentos` es el valor anterior, de ahí 2^intentos.
    """
    with conn.transaction():
        f = conn.execute(
            "update trabajo set estado = 'en_espera', intentos = intentos + 1,"
            " disponible_desde = now()"
            " + make_interval(secs => least(30 * power(2, intentos), 600)),"
            " worker_id = null, lease_hasta = null, actualizado = now()"
            " where id = %s returning disponible_desde",
            (trabajo_id,),
        ).fetchone()
    return f["disponible_desde"]


def listar(conn: psycopg.Connection, asignatura_id: UUID) -> list[Trabajo]:
    filas = conn.execute(
        "select * from trabajo where asignatura_id = %s order by creado, id", (asignatura_id,)
    ).fetchall()
    return [_trabajo(f) for f in filas]
