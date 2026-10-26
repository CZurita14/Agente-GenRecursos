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
    assert [len(l) for l in lotes] == [4, 4, 4]
    ids = [p.item_id for l in lotes for p in l]
    assert ids == [f"i{k}" for k in range(1, 13)]


def test_orden_de_menor_a_mayor_nivel(silabo):
    ctx = contexto_clase(silabo, "M2-S1")
    orden = ["receptivo", "resolutivo", "reflexivo", "critico"]
    niveles = [orden.index(p.nivel) for l in planificar(ctx, 12, "profesional") for p in l]
    assert niveles == sorted(niveles)


def test_focos_distintos_m2s1_m2s2(silabo):
    f1 = {p.foco for l in planificar(contexto_clase(silabo, "M2-S1"), 12, "fundamentacion") for p in l}
    f2 = {p.foco for l in planificar(contexto_clase(silabo, "M2-S2"), 12, "fundamentacion") for p in l}
    assert f1 != f2


def test_determinista(silabo):
    ctx = contexto_clase(silabo, "M2-S1")
    assert planificar(ctx, 10, "avanzado") == planificar(ctx, 10, "avanzado")
