"""Fixtures compartidas de las pruebas del backend.

Las fixtures de base de datos (`conn`, `nueva_conexion`) llegan con la Tarea 2,
cuando existan las migraciones.
"""


# --- Fixtures del sílabo (Tarea 3) -----------------------------------------
import copy  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402

_RUTA_SILABO = Path(__file__).parent / "fixtures" / "silabo_datos.json"
_DATOS_SILABO = json.loads(_RUTA_SILABO.read_text(encoding="utf-8"))


@pytest.fixture
def datos() -> dict:
    """Copia nueva de los datos del sílabo de Análisis de Datos, mutable por prueba."""
    return copy.deepcopy(_DATOS_SILABO)


@pytest.fixture
def silabo(datos):
    """Sílabo de Análisis de Datos (M2 y M3) validado."""
    from app.silabo.modelo import SilaboUTI

    return SilaboUTI.model_validate(datos)
