"""Proceso de workers: python backend/worker.py. Ctrl+C solicita un cierre ordenado."""
import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import psycopg

from app.agentes.facultades import cargar_perfiles
from app.agentes.orquestador import procesar_uno
from app.config import RAIZ, ajustes
from app.db.conexion import conectar
from app.db.migrar import aplicar_migraciones
from app.llm.cliente import ClienteVLLM

registro = logging.getLogger(__name__)


def registrar_llamada(conn, datos):
    """Registra metadatos de uso; nunca persiste prompts ni razonamiento."""
    with conn.transaction():
        conn.execute(
            "insert into llamada_llm (trabajo_id,asignatura_id,rol,tokens_entrada,tokens_salida,segundos,ok) "
            "values (%(trabajo_id)s,%(asignatura_id)s,%(rol)s,%(tokens_entrada)s,%(tokens_salida)s,%(segundos)s,%(ok)s)", datos,
        )


def main():
    config = ajustes()
    directorio = config.agentes_dir if config.agentes_dir.is_absolute() else RAIZ / config.agentes_dir
    perfiles = cargar_perfiles(directorio)
    with conectar() as conn:
        conn.autocommit = True
        aplicar_migraciones(conn)

    def registrar(datos):
        with conectar() as conn:
            registrar_llamada(conn, datos)

    cliente = ClienteVLLM(config.llm_base_url, config.llm_model, config.llm_timeout_s,
                         config.llm_max_concurrencia, registrar, config.llm_api_key)
    detener = threading.Event()

    def consumir(numero):
        # Un identificador distinto por proceso y por hilo evita confundir reinicios.
        worker_id = f"{uuid.uuid4()}-{numero}"
        while not detener.is_set():
            try:
                with conectar() as conn:
                    conn.autocommit = True
                    while not detener.is_set():
                        if not procesar_uno(conn, cliente, perfiles, worker_id, config.lease_s):
                            detener.wait(2)
            except psycopg.Error:
                registro.error("conexión de base de datos interrumpida (worker %s)", numero)
                detener.wait(2)

    pool = ThreadPoolExecutor(max_workers=config.llm_max_concurrencia)
    futuros = [pool.submit(consumir, n) for n in range(config.llm_max_concurrencia)]
    try:
        while not detener.wait(1):
            for futuro in futuros:
                if futuro.done():
                    futuro.result()  # No dejar morir un hilo silenciosamente.
    except KeyboardInterrupt:
        detener.set()
    finally:
        detener.set()
        pool.shutdown(wait=True)
        cliente.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
