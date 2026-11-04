"""Corpus de entrenamiento: fragmentos académicos de los sílabos, sin datos personales.

Solo se lee `SilaboUTI`, que por construcción no tiene perfil docente ni contacto.
Como segunda barrera, se descarta todo fragmento con correos, ORCID o números largos.
Nada de este módulo imprime ni registra texto de los sílabos.
"""
import re
from dataclasses import dataclass
from pathlib import Path

from app.silabo.lector.ensamblar import leer_silabo
from app.silabo.modelo import SilaboUTI

_PERSONAL = re.compile(
    r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"      # correo
    r"|\b\d{4}-\d{4}-\d{4}-\d{3}[\dXx]\b"  # ORCID
    r"|\d{7,}"                           # teléfono, cédula u otra secuencia larga
)


@dataclass(frozen=True)
class Fragmento:
    codigo_pf: str
    facultad: str
    carrera: str
    momento: int | None
    tipo: str
    texto: str


def _limpio(texto: str) -> str | None:
    t = " ".join(texto.split())
    return t if t and not _PERSONAL.search(t) else None


def fragmentos(silabo: SilaboUTI) -> list[Fragmento]:
    """Contenidos, actividades, resultados y evidencias; sin vacíos ni repetidos."""
    base = (silabo.proyecto_formativo.codigo, silabo.facultad, silabo.carrera)
    crudos: list[tuple[int | None, str, str]] = [
        (None, "resultado", r.texto) for r in silabo.resultados_aprendizaje
    ]
    for m in silabo.momentos:
        crudos.append((m.numero, "evidencia", m.evidencia))
        for s in m.sesiones:
            crudos += [(m.numero, "contenido", c) for c in s.contenidos]
            crudos += [
                (m.numero, "actividad", t)
                for t in (s.docente.texto, s.practico.texto, s.autonomo.texto)
            ]
    vistos: set[str] = set()
    salida: list[Fragmento] = []
    for momento, tipo, texto in crudos:
        t = _limpio(texto)
        if t is None or t in vistos:
            continue
        vistos.add(t)
        salida.append(Fragmento(*base, momento, tipo, t))
    return salida


def leer_carpeta(carpeta: Path) -> tuple[list[SilaboUTI], list[str]]:
    """Lee `*.pdf` y `*.json` (un `SilaboUTI` serializado).

    Conserva una versión por código de proyecto formativo: la de `aprobado` más
    reciente y, a igualdad, la de mayor nombre de archivo. Devuelve también los
    nombres de archivo rechazados, sin el motivo, que podría contener texto.
    """
    elegidos: dict[str, tuple[tuple, SilaboUTI]] = {}
    rechazados: list[str] = []
    for ruta in sorted(Path(carpeta).iterdir()):
        if ruta.suffix.lower() not in (".pdf", ".json") or not ruta.is_file():
            continue
        try:
            datos = ruta.read_bytes()
            if ruta.suffix.lower() == ".pdf":
                silabo = leer_silabo(datos)
            else:
                silabo = SilaboUTI.model_validate_json(datos)
        except Exception:
            rechazados.append(ruta.name)
            continue
        clave = (silabo.proyecto_formativo.aprobado, ruta.name)
        codigo = silabo.proyecto_formativo.codigo
        if codigo not in elegidos or clave > elegidos[codigo][0]:
            elegidos[codigo] = (clave, silabo)
    return [s for _, s in elegidos.values()], rechazados
