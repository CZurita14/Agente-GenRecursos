"""Workers compartidos por herramienta (spec §3.7). Sin estado (regla A2)."""
from app.agentes.workers.base import Worker
from app.agentes.workers.cuestionario import WorkerCuestionario, WorkerSimulacro
from app.agentes.workers.ficha_clase import WorkerFichaClase

WORKERS: dict[str, Worker] = {
    "cuestionario": WorkerCuestionario(),
    "ficha_clase": WorkerFichaClase(),
    "simulacro": WorkerSimulacro(),
}

__all__ = ["WORKERS", "Worker", "WorkerCuestionario", "WorkerFichaClase", "WorkerSimulacro"]
