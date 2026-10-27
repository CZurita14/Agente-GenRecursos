"""§9.4 regla 2: si la política del momento excluye la IA en una evaluación, en ese
momento solo se ofrecen repasos de momentos anteriores.

Detección determinista sobre el texto normalizado; ante la duda, el docente ve el
motivo en el catálogo (`restringido`) y puede pedir el repaso.
"""
import re

from app.agentes.facultades import normalizar

_RESTRICTIVA = re.compile(
    r"\bSIN (?:ASISTENCIA|USO|APOYO|AYUDA) DE (?:LA )?(?:IA|INTELIGENCIA ARTIFICIAL)\b"
    r"|\bNO SE PERMITE (?:EL USO DE )?(?:LA )?(?:IA|INTELIGENCIA ARTIFICIAL)\b"
    r"|\bPROHIBIDO EL USO DE (?:LA )?(?:IA|INTELIGENCIA ARTIFICIAL)\b"
)


def excluye_ia_en_evaluacion(politica: str) -> bool:
    return bool(_RESTRICTIVA.search(normalizar(politica or "")))
