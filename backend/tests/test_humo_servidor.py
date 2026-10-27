"""Prueba real optativa: LLM_REAL=1; usa únicamente el vLLM configurado."""
import os
import time
from pathlib import Path

import httpx
import pytest

from app.agentes.evidencia import PaqueteEvidencia
from app.agentes.facultades import cargar_catalogo, cargar_perfiles
from app.agentes.orquestador import SolicitudGeneracion, crear_asignatura, crear_trabajos, procesar_uno
from app.cola.trabajos import Ambito
from app.config import ajustes
from app.llm.cliente import ClienteVLLM
from worker import registrar_llamada

RAIZ = Path(__file__).resolve().parents[2]


@pytest.mark.servidor
@pytest.mark.skipif(os.getenv("LLM_REAL") != "1", reason="requiere LLM_REAL=1 y red UTI")
def test_humo_nucleo(silabo, conn, nueva_conexion, record_property):
    config = ajustes()
    try:
        respuesta = httpx.get(config.llm_base_url.rstrip("/") + "/models", timeout=8)
        respuesta.raise_for_status()
    except httpx.HTTPError:
        pytest.skip("servidor de IA no alcanzable desde esta red")
    modelos = respuesta.json()["data"]
    modelo = next((m for m in modelos if m["id"] == config.llm_model), None)
    assert modelo is not None, "el modelo configurado no está servido por vLLM"
    assert modelo.get("max_model_len") == 8192

    perfiles = cargar_perfiles(RAIZ / "agentes")
    aid = crear_asignatura(conn, dueno="humo@uti.edu.ec", silabo=silabo,
                           catalogo=cargar_catalogo(RAIZ / "kb/catalogo.yaml"), perfiles=perfiles)
    for clase, herramienta in (("M3-S4", "cuestionario"), ("M2-S1", "ficha_clase")):
        crear_trabajos(conn, SolicitudGeneracion(aid, Ambito("clase", clase), [herramienta], cantidad=4))

    def registrar(datos):
        c = nueva_conexion()
        try:
            registrar_llamada(c, datos)
        finally:
            c.close()

    inicio = time.monotonic()
    cliente = ClienteVLLM(config.llm_base_url, config.llm_model, config.llm_timeout_s,
                         config.llm_max_concurrencia, registrar, config.llm_api_key)
    try:
        # La prueba no espera 30-600 s de backoff: una espera queda visible como tal.
        for _ in range(2):
            assert procesar_uno(conn, cliente, perfiles, "humo-local", config.lease_s)
    finally:
        cliente.close()
    trabajos = conn.execute("select estado,error from trabajo").fetchall()
    assert all(t["estado"] in ("listo", "requiere_revision") for t in trabajos), trabajos
    recursos = conn.execute("select herramienta,estado,evidencia from recurso order by creado").fetchall()
    assert len(recursos) == 2
    llamadas = conn.execute("select * from llamada_llm").fetchall()
    assert llamadas and all(c["asignatura_id"] == aid and c["trabajo_id"] is not None for c in llamadas)
    assert all(c["tokens_entrada"] + c["tokens_salida"] <= 8192 for c in llamadas)
    segundos = round(time.monotonic() - inicio, 2)
    resumen = {"segundos": segundos, "llamadas": len(llamadas),
               "tokens_entrada": sum(c["tokens_entrada"] for c in llamadas),
               "tokens_salida": sum(c["tokens_salida"] for c in llamadas)}
    record_property("humo", resumen)
    print("HUMO_LOCAL", resumen)
    for r in recursos:
        e = PaqueteEvidencia.model_validate(r["evidencia"])
        print(r["herramienta"], r["estado"], e.resumen())
