"""Planificador determinista: tabla de especificaciones y lotes (sin IA).

Decide cuántos ítems hay de cada nivel cognitivo (spec §6.2), asigna a cada
ítem un foco tomado de las actividades y contenidos de la clase (§9.3) y
reparte el plan en lotes que caben en el contexto del modelo (§5.3).
No usa aleatoriedad: el mismo contexto produce siempre el mismo plan.
"""
from itertools import zip_longest

from app.agentes.mensajes import PlanItem
from app.silabo.contexto import ContextoClase

# Orden de niveles de menor a mayor; también es el desempate del mayor resto.
NIVELES = ("receptivo", "resolutivo", "reflexivo", "critico")

# Porcentajes enteros (suma 100). "Crítico/Cocreativo" se agrupa en `critico`.
PERFILES: dict[str, dict[str, float]] = {
    "fundamentacion": {"receptivo": 0.20, "resolutivo": 0.40, "reflexivo": 0.30, "critico": 0.10},
    "profesional": {"receptivo": 0.10, "resolutivo": 0.30, "reflexivo": 0.35, "critico": 0.25},
    "avanzado": {"receptivo": 0.0, "resolutivo": 0.20, "reflexivo": 0.40, "critico": 0.40},
}


def perfil_por_nivel(nivel: int, posgrado: bool = False) -> str:
    """Niveles 1-3 fundamentación, 4-7 profesional, 8 o más (o posgrado) avanzado."""
    if posgrado or nivel >= 8:
        return "avanzado"
    if nivel >= 4:
        return "profesional"
    return "fundamentacion"


def tabla_especificaciones(n: int, perfil: str) -> dict[str, int]:
    """Reparte `n` ítems entre los niveles con el método del mayor resto.

    Se usa aritmética entera (porcentajes enteros) para evitar errores de
    coma flotante. Ante restos iguales gana el nivel más bajo (orden de
    `NIVELES`). La suma siempre es `n`.
    """
    if n < 0:
        raise ValueError("n debe ser >= 0")
    porcentajes = {nv: round(PERFILES[perfil][nv] * 100) for nv in NIVELES}
    base = {nv: n * porcentajes[nv] // 100 for nv in NIVELES}
    restos = {nv: n * porcentajes[nv] % 100 for nv in NIVELES}
    faltan = n - sum(base.values())
    # sorted es estable: a igual resto se conserva el orden de NIVELES.
    for nv in sorted(NIVELES, key=lambda x: -restos[x])[:faltan]:
        base[nv] += 1
    return base


def _focos(contexto: ContextoClase) -> list[str]:
    """Actividades y contenidos intercalados (primero actividad)."""
    intercalados = [
        f.strip()
        for par in zip_longest(contexto.actividades, contexto.contenidos)
        for f in par
        if f and f.strip()
    ]
    return intercalados or [contexto.momento_titulo]


def planificar(
    contexto: ContextoClase, n: int, perfil: str, tam_lote: int = 4
) -> list[list[PlanItem]]:
    """Plan de `n` ítems `i1…in`, de menor a mayor nivel, en lotes de `tam_lote`.

    El foco de cada ítem rota por las actividades y contenidos de la clase,
    de modo que dos clases con el mismo contenido pero distintas actividades
    obtienen focos distintos.
    """
    if tam_lote < 1:
        raise ValueError("tam_lote debe ser >= 1")
    tabla = tabla_especificaciones(n, perfil)
    focos = _focos(contexto)
    niveles = [nv for nv in NIVELES for _ in range(tabla[nv])]
    items = [
        PlanItem(item_id=f"i{k + 1}", nivel=nv, foco=focos[k % len(focos)])
        for k, nv in enumerate(niveles)
    ]
    return [items[i : i + tam_lote] for i in range(0, len(items), tam_lote)]
