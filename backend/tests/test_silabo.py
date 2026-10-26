"""Contrato SilaboUTI y contexto por clase."""
import pytest
from pydantic import ValidationError

from app.silabo.contexto import contexto_clase
from app.silabo.modelo import SilaboUTI


def test_fixture_valida(silabo):
    assert silabo.proyecto_formativo.codigo == "B26-SOFT-3-56146-1727"


def test_rechaza_campos_personales(datos):
    datos["docente"] = {"correo": "x@uti.edu.ec"}
    with pytest.raises(ValidationError):
        SilaboUTI.model_validate(datos)


def test_contexto_m2_s1(silabo):
    c = contexto_clase(silabo, "M2-S1")
    assert [r.id for r in c.ra] == ["RA2"] and c.nivel == 3


def test_clases_con_mismo_contenido_difieren_en_actividades(silabo):
    a, b = contexto_clase(silabo, "M2-S1"), contexto_clase(silabo, "M2-S2")
    assert a.contenidos == b.contenidos
    assert a.actividades != b.actividades


def test_latex_se_conserva(silabo):
    c = contexto_clase(silabo, "M3-S3")
    assert "$H_0" in " ".join(c.actividades + c.contenidos)


def test_clase_inexistente(silabo):
    with pytest.raises(KeyError):
        contexto_clase(silabo, "M9-S9")


def test_modelos_inmutables(silabo):
    with pytest.raises(ValidationError):
        silabo.carrera = "OTRA"


def test_competencia_pf_vacia_aceptada(silabo):
    assert silabo.competencia_pf == ""


def test_semana_del_periodo(silabo):
    assert contexto_clase(silabo, "M3-S3").fecha.isoformat() == "2026-10-28"
    sesion = silabo.momentos[1].sesiones[2]
    assert sesion.semana_periodo == 4


def test_contexto_incluye_politica_rubrica_y_problema(silabo):
    c = contexto_clase(silabo, "M3-S4")
    assert c.politica_ia and c.rubrica and c.problema.reto
    assert c.codigo_pf == "B26-SOFT-3-56146-1727"
