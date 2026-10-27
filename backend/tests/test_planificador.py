import pytest

from app.agentes.planificador import (
    PERFILES,
    perfil_por_nivel,
    planificar,
    tabla_especificaciones,
)
from app.silabo.contexto import contexto_clase


def test_tabla_12_fundamentacion():
    assert tabla_especificaciones(12, "fundamentacion") == {
        "receptivo": 2, "resolutivo": 5, "reflexivo": 4, "critico": 1,
    }


@pytest.mark.parametrize("perfil", list(PERFILES))
def test_suma_siempre_n(perfil):
    for n in range(1, 31):
        assert sum(tabla_especificaciones(n, perfil).values()) == n


def test_perfil_por_nivel():
    assert perfil_por_nivel(1) == "fundamentacion"
    assert perfil_por_nivel(3) == "fundamentacion"
    assert perfil_por_nivel(4) == "profesional"
    assert perfil_por_nivel(7) == "profesional"
    assert perfil_por_nivel(8) == "avanzado"
    assert perfil_por_nivel(2, posgrado=True) == "avanzado"


def test_lotes_de_4(silabo):
    ctx = contexto_clase(silabo, "M2-S1")
    lotes = planificar(ctx, 12, "fundamentacion")
    assert [len(lote) for lote in lotes] == [4, 4, 4]
    ids = [p.item_id for lote in lotes for p in lote]
    assert ids == [f"i{k}" for k in range(1, 13)]


def test_orden_de_menor_a_mayor_nivel(silabo):
    ctx = contexto_clase(silabo, "M2-S1")
    orden = ["receptivo", "resolutivo", "reflexivo", "critico"]
    niveles = [orden.index(p.nivel) for lote in planificar(ctx, 12, "profesional") for p in lote]
    assert niveles == sorted(niveles)


def test_focos_distintos_m2s1_m2s2(silabo):
    f1 = {p.foco for lote in planificar(contexto_clase(silabo, "M2-S1"), 12, "fundamentacion") for p in lote}
    f2 = {p.foco for lote in planificar(contexto_clase(silabo, "M2-S2"), 12, "fundamentacion") for p in lote}
    assert f1 != f2


def test_determinista(silabo):
    ctx = contexto_clase(silabo, "M2-S1")
    assert planificar(ctx, 10, "avanzado") == planificar(ctx, 10, "avanzado")


def _plano(lotes):
    return [p for lote in lotes for p in lote]


def test_n_pequeno_incluye_actividad_y_contenido(silabo):
    ctx = contexto_clase(silabo, "M2-S1")
    focos = {p.foco for p in _plano(planificar(ctx, 3, "fundamentacion"))}
    assert len(ctx.actividades) + len(ctx.contenidos) > 3
    assert focos & {a.strip() for a in ctx.actividades}
    assert focos & {c.strip() for c in ctx.contenidos}


def test_focos_desacoplados_de_niveles(silabo):
    plan = _plano(planificar(contexto_clase(silabo, "M2-S1"), 12, "fundamentacion"))
    for a, b in zip(plan, plan[1:]):
        assert a.foco != b.foco
    niveles_por_foco = {}
    for p in plan:
        niveles_por_foco.setdefault(p.foco, set()).add(p.nivel)
    repetidos = [n for f, n in niveles_por_foco.items() if sum(q.foco == f for q in plan) > 1]
    assert repetidos and all(len(n) > 1 for n in repetidos)


def test_perfil_desconocido():
    with pytest.raises(ValueError):
        tabla_especificaciones(5, "inexistente")


def test_n_cero_y_errores(silabo):
    ctx = contexto_clase(silabo, "M2-S1")
    assert planificar(ctx, 0, "profesional") == []
    with pytest.raises(ValueError):
        tabla_especificaciones(-1, "profesional")
    with pytest.raises(ValueError):
        planificar(ctx, 4, "profesional", tam_lote=0)


def test_ultimo_lote_parcial(silabo):
    lotes = planificar(contexto_clase(silabo, "M2-S1"), 10, "profesional")
    assert [len(lote) for lote in lotes] == [4, 4, 2]


def test_avanzado_sin_receptivo():
    assert tabla_especificaciones(10, "avanzado")["receptivo"] == 0


ESCENARIOS = ["picos de tráfico en una tienda en línea", "tiempos de respuesta de una API REST",
              "fallos de compilación en un repositorio Git", "consultas lentas en una base de datos"]


def test_casos_evitan_el_escenario_del_entregable(silabo):
    # §9.4 regla 1: el entregable de M3 habla de «picos de tráfico»; ese escenario se descarta.
    ctx = contexto_clase(silabo, "M3-S4")
    plan = [p for lote in planificar(ctx, 12, "fundamentacion", escenarios=ESCENARIOS) for p in lote]
    casos = [p.caso for p in plan]
    assert set(casos) == set(ESCENARIOS[1:])
    assert all(a != b for a, b in zip(casos, casos[1:]))
    assert planificar(ctx, 12, "fundamentacion", escenarios=ESCENARIOS) == planificar(
        ctx, 12, "fundamentacion", escenarios=ESCENARIOS)


def test_casos_varian_entre_clases(silabo):
    a, b = (contexto_clase(silabo, c) for c in ("M2-S1", "M2-S2"))
    caso = lambda ctx: planificar(ctx, 4, "fundamentacion", escenarios=ESCENARIOS[1:])[0][0].caso
    assert {caso(a), caso(b)} <= set(ESCENARIOS[1:])
    assert [p.caso for p in planificar(a, 3, "fundamentacion", escenarios=ESCENARIOS[1:])[0]] != \
           [p.caso for p in planificar(b, 3, "fundamentacion", escenarios=ESCENARIOS[1:])[0]]


def test_sin_escenarios_libres_no_se_asigna_caso(silabo):
    ctx = contexto_clase(silabo, "M3-S4")
    plan = planificar(ctx, 4, "fundamentacion", escenarios=["picos de tráfico de red"])[0]
    assert all(p.caso == "" for p in plan)
    assert all(p.caso == "" for p in planificar(ctx, 4, "fundamentacion")[0])
