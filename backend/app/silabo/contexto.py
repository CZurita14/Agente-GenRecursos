"""Contexto de una clase: lo que los agentes necesitan saber de una sesión."""
from datetime import date

from pydantic import BaseModel

from app.silabo.modelo import (
    FilaRubrica,
    Problema,
    ResultadoAprendizaje,
    SilaboUTI,
)


class ContextoClase(BaseModel, frozen=True):
    codigo_pf: str
    version_silabo: str
    asignatura: str
    carrera: str
    nivel: int
    clase_id: str
    fecha: date
    momento_titulo: str
    contenidos: list[str]
    actividades: list[str]
    ra: list[ResultadoAprendizaje]
    rubrica: list[FilaRubrica]
    competencia_perfil: str
    problema: Problema
    politica_ia: str
    entregables_momento: list[str]


def contexto_clase(silabo: SilaboUTI, clase_id: str) -> ContextoClase:
    """Extrae el contexto de la sesión `clase_id` (p. ej. "M2-S1").

    Lanza `KeyError` si la clase no existe.
    """
    for momento in silabo.momentos:
        for sesion in momento.sesiones:
            if sesion.id != clase_id:
                continue
            # Las actividades distinguen dos clases con el mismo contenido.
            candidatas = [
                sesion.docente.texto,
                sesion.docente.asincronica.texto if sesion.docente.asincronica else "",
                sesion.practico.texto,
                sesion.autonomo.texto,
            ]
            entregables: list[str] = []
            for s in momento.sesiones:
                for e in s.entregables:
                    if e not in entregables:
                        entregables.append(e)
            pf = silabo.proyecto_formativo
            return ContextoClase(
                codigo_pf=pf.codigo,
                version_silabo=pf.version,
                asignatura=pf.nombre,
                carrera=silabo.carrera,
                nivel=pf.nivel,
                clase_id=sesion.id,
                fecha=sesion.fecha,
                momento_titulo=momento.titulo,
                contenidos=list(sesion.contenidos),
                actividades=[t for t in candidatas if t.strip()],
                ra=[r for r in silabo.resultados_aprendizaje if r.id in momento.ra],
                rubrica=list(momento.rubrica),
                competencia_perfil=silabo.competencia_perfil,
                problema=silabo.problema,
                politica_ia=momento.politica_ia,
                entregables_momento=entregables,
            )
    raise KeyError(clase_id)
