import re

import pytest

from app.agentes.mensajes import EstiloFacultad
from app.llm.cliente import ContextoExcedido
from app.llm.prompts import Sello, construir_prompt
from app.silabo.contexto import contexto_clase

PERSONAL = re.compile(r"[\w.]+@[\w.]+|\+?\d[\d\s-]{8,}|ORCID|\d{4}-\d{4}-\d{4}-\d{3}[\dX]")


def contar(msgs):
    return sum(len(m["content"]) for m in msgs) // 4


ESTILO = EstiloFacultad(tipos_de_caso=["caso de empresa"], software_habitual=["Python"], vocabulario="")


def _sello(ctx):
    return Sello(codigo_pf=ctx.codigo_pf, clase_id=ctx.clase_id, fecha=ctx.fecha)


def _armar(ctx, ya=(), salida=3500, instr="Genera enunciados."):
    return construir_prompt(
        sello=_sello(ctx), instrucciones=instr, contexto=ctx, estilo=ESTILO,
        ya_generado=list(ya), pedido="Genera 3 ejercicios.", salida_max=salida, contar=contar,
    )


def test_sello_primero(silabo):
    ctx = contexto_clase(silabo, "M3-S4")
    msgs = _armar(ctx)
    assert msgs[0]["role"] == "system" and msgs[1]["role"] == "user"
    assert msgs[0]["content"].startswith(
        f"[Asignatura {ctx.codigo_pf} · Clase M3-S4 · {ctx.fecha:%d/%m/%Y}]"
    )
    assert msgs[0]["content"].startswith("[Asignatura B26-SOFT-3-56146-1727 · Clase M3-S4 · ")


def test_recorta_ya_generado_antes_que_rubrica(silabo):
    ctx = contexto_clase(silabo, "M3-S4")
    ya = [f"Enunciado {i}: " + "x" * 60 for i in range(200)]
    completo = contar(_armar(ctx, ya=[]))
    msgs = _armar(ctx, ya=ya)
    assert contar(msgs) + 3500 + 300 <= 8192
    user = msgs[1]["content"]
    assert sum(f"Enunciado {i}:" in user for i in range(200)) < 200
    for fila in ctx.rubrica:
        assert fila.indicador in user
    assert completo > 0


def test_nunca_recorta_la_clase(silabo):
    ctx = contexto_clase(silabo, "M3-S4").model_copy(update={"contenidos": ["c" * 40000]})
    with pytest.raises(ContextoExcedido, match="M3-S4"):
        _armar(ctx)


def test_sin_datos_personales(silabo):
    for mom in silabo.momentos:
        for ses in mom.sesiones:
            ctx = contexto_clase(silabo, ses.id)
            sello = _sello(ctx).linea()
            for m in _armar(ctx):
                # El código del proyecto formativo del sello (B26-SOFT-3-56146-1727)
                # es institucional y casa con el patrón de teléfono; se excluye.
                texto = m["content"].replace(sello, "")
                assert not PERSONAL.search(texto), (ses.id, texto)
