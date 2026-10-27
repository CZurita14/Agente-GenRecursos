"""Generación, seguimiento y recursos, con permisos y pertenencia transaccionales."""
from contextlib import closing, contextmanager

from fastapi import HTTPException
from psycopg.types.json import Jsonb

from app.agentes.orquestador import SolicitudGeneracion, crear_trabajos
from app.agentes.planificador import perfil_por_nivel
from app.agentes.workers import WORKERS
from app.asignaturas.servicio import exigir_acceso
from app.recursos.validacion import EdicionInvalida, validar_contenido
from app.silabo.contexto import contexto_clase
from app.silabo.modelo import SilaboUTI


def _recurso(conn, aid, rid, *, editar=False):
    fila = conn.execute("select r.*,t.parametros snapshot from recurso r join trabajo t "
                        "on t.id=r.trabajo_id and t.asignatura_id=r.asignatura_id "
                        "where r.id=%s and r.asignatura_id=%s" + (" for update of r" if editar else ""),
                        (rid, aid)).fetchone()
    if fila is None:
        raise HTTPException(404, "Recurso inexistente en esta asignatura")
    return fila


def _contexto(recurso, asignatura):
    datos = recurso["snapshot"].get("silabo")
    if datos is None:
        # El número de versión no garantiza igualdad de contenido. No sustituir
        # una instantánea ausente por el sílabo actual para validar una edición.
        raise HTTPException(409, "El contexto original del recurso no está disponible")
    try:
        return contexto_clase(SilaboUTI.model_validate(datos), recurso["ambito_id"])
    except (ValueError, KeyError):
        raise HTTPException(409, "El contexto original del recurso no está disponible") from None


def _detalle(recurso, asignatura):
    campos = ("id", "trabajo_id", "asignatura_id", "ambito_id", "herramienta", "version_silabo",
              "version_esquema", "contenido", "evidencia", "estado", "revision", "creado",
              "actualizado", "verificacion_edicion")
    resultado = {k: recurso[k] for k in campos}
    resultado["evidencia_vigente"] = recurso["revision"] == 0
    actualizado = recurso["version_silabo"] != asignatura["version_silabo"]
    try:
        original = _contexto(recurso, asignatura)
        actual = contexto_clase(SilaboUTI.model_validate(asignatura["silabo"]), recurso["ambito_id"])
        actualizado = actualizado or original.model_dump(exclude={"version_silabo"}) != actual.model_dump(exclude={"version_silabo"})
    except (HTTPException, ValueError, KeyError):
        actualizado = True
    resultado["silabo_actualizado"] = actualizado
    return resultado


class ServicioRecursos:
    def __init__(self, conexion, perfiles):
        self.conexion, self.perfiles = conexion, perfiles

    @contextmanager
    def _acceso(self, aid, correo, *, editar=False):
        with closing(self.conexion()) as conn:
            conn.autocommit = True
            with conn.transaction():
                conn.execute("set local lock_timeout to '2s'")
                asignatura, _ = exigir_acceso(conn, aid, correo, editar=editar)
                yield conn, asignatura

    def catalogo(self, aid, correo, ambito):
        with self._acceso(aid, correo) as (_, a):
            silabo = SilaboUTI.model_validate(a["silabo"])
            recomendaciones = self.perfiles[a["agente"]].herramientas_recomendadas.get(ambito, [])
            disponibles = list(WORKERS) if ambito == "clase" else []
            orden = [h for h in recomendaciones if h in disponibles]
            orden += sorted(h for h in disponibles if h not in orden)
            return {"ambito": ambito, "perfil_sugerido": perfil_por_nivel(silabo.proyecto_formativo.nivel),
                    "herramientas": [{"id": h, "recomendada": h in recomendaciones} for h in orden]}

    def generar(self, aid, correo, ambito, herramientas, cantidad, instrucciones, perfil):
        with self._acceso(aid, correo, editar=True) as (conn, _):
            try:
                ids = crear_trabajos(conn, SolicitudGeneracion(aid, ambito, herramientas,
                                      cantidad=cantidad, instrucciones=instrucciones, perfil_dificultad=perfil))
            except (ValueError, KeyError):
                raise HTTPException(422, "Selección de generación no válida") from None
            return {"trabajos": [{"id": str(tid), "herramienta": h, "estado": "en_cola"}
                                 for tid, h in zip(ids, herramientas)]}

    def trabajos(self, aid, correo, limite, desde):
        with self._acceso(aid, correo) as (conn, _):
            return conn.execute(
                "select t.id,t.herramienta,t.ambito_tipo,t.ambito_id,t.estado,t.lotes_total,t.lotes_hechos,"
                "t.rondas_revision,t.tokens_entrada,t.tokens_salida,t.creado,t.actualizado,r.id recurso_id,"
                "r.estado recurso_estado,r.revision recurso_revision,"
                "case when t.estado='error' then 'No se pudo completar el trabajo' else null end error "
                "from trabajo t left join recurso r on r.trabajo_id=t.id and r.asignatura_id=t.asignatura_id "
                "where t.asignatura_id=%s order by case "
                "when t.estado in ('generando','verificando','revisando') then 0 "
                "when t.estado in ('en_cola','en_espera') then 1 else 2 end,t.creado desc,t.id limit %s offset %s",
                (aid, limite, desde)).fetchall()

    def listar(self, aid, correo, limite, desde):
        with self._acceso(aid, correo) as (conn, _):
            return conn.execute("select id,trabajo_id,ambito_id,herramienta,version_silabo,estado,revision,"
                                "creado,actualizado from recurso where asignatura_id=%s "
                                "order by creado desc,id limit %s offset %s", (aid, limite, desde)).fetchall()

    def obtener(self, aid, rid, correo):
        with self._acceso(aid, correo) as (conn, a):
            return _detalle(_recurso(conn, aid, rid), a)

    def editar(self, aid, rid, correo, revision, contenido):
        with self._acceso(aid, correo, editar=True) as (conn, a):
            r = _recurso(conn, aid, rid, editar=True)
            if r["revision"] != revision:
                raise HTTPException(409, "El recurso cambió; recárguelo antes de editar")
            try:
                canonico, verificaciones = validar_contenido(r["herramienta"], contenido, r["contenido"],
                                                            _contexto(r, a), aid)
            except EdicionInvalida:
                raise HTTPException(422, "El contenido editado no es válido") from None
            if canonico == r["contenido"]:
                # Guardar sin cambios no crea historia ni invalida la revisión original.
                return _detalle(r, a)
            nueva_revision = revision + 1
            conn.execute("insert into recurso_edicion (recurso_id,asignatura_id,usuario,revision,"
                         "contenido_anterior,contenido_nuevo,estado_anterior,verificaciones) "
                         "values (%s,%s,%s,%s,%s,%s,%s,%s)",
                         (rid, aid, correo, nueva_revision, Jsonb(r["contenido"]), Jsonb(canonico),
                          r["estado"], Jsonb(verificaciones)))
            conn.execute("update recurso set contenido=%s,revision=%s,estado='requiere_revision',"
                         "verificacion_edicion=%s,actualizado=clock_timestamp() where id=%s and asignatura_id=%s",
                         (Jsonb(canonico), nueva_revision, Jsonb(verificaciones), rid, aid))
            return _detalle(_recurso(conn, aid, rid), a)
