"""Contexto de una clase: lo que los agentes necesitan saber de una sesión."""
from datetime import date

from app.silabo.modelo import (
    BaseInmutable,
    FilaRubrica,
    Problema,
    ResultadoAprendizaje,
    SilaboUTI,
)


class ContextoClase(BaseInmutable):
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
            # La evidencia del momento es un entregable (§9.4) aunque las sesiones no listen ninguno.
            entregables: list[str] = [momento.evidencia] if momento.evidencia.strip() else []
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
                ra=[r.model_copy(deep=True) for r in silabo.resultados_aprendizaje if r.id in momento.ra],
                # Copias profundas: `niveles` es un dict y no se comparte con el sílabo.
                rubrica=[f.model_copy(deep=True) for f in momento.rubrica],
                competencia_perfil=silabo.competencia_perfil,
                problema=silabo.problema.model_copy(deep=True),
                politica_ia=momento.politica_ia,
                entregables_momento=entregables,
            )
    raise KeyError(clase_id)
