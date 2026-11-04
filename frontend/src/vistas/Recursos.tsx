import { useEffect, useRef, useState } from 'react';
import { Alert, Badge, Card, DataTable, type Column } from '../components';
import { ErrorApi, asignaturas as cargarAsignaturas, recursos as cargarRecursos, trabajos as cargarTrabajos } from '../api/cliente';
import type { AsignaturaResumen, RecursoResumen, Trabajo } from '../api/tipos';
import { nombreAmbito, nombreHerramienta } from '../api/herramientas';
import { ChatAjustes } from '../components/ChatAjustes';
import { ETAPAS, FINALES, INTERVALO_MS } from './Progreso';

interface RecursosProps {
  aidInicial?: string;
  onAbrir: (aid: string, rid: string, rol: AsignaturaResumen['rol']) => void;
  onSesionVencida: () => void;
  onTrabajos?: (aid: string, ids: string[], rol: AsignaturaResumen['rol']) => void;
}

const COLUMNAS: Column<RecursoResumen>[] = [
  { key: 'herramienta', header: 'Herramienta', render: r => nombreHerramienta(r.herramienta) },
  { key: 'ambito_id', header: 'Ámbito', render: r => nombreAmbito(r.ambito_id) },
  { key: 'estado', header: 'Estado', render: r => r.estado === 'listo'
    ? <Badge tone="success">Listo</Badge> : <Badge tone="warning">Requiere revisión</Badge> },
  { key: 'creado', header: 'Creado', render: r => new Date(r.creado).toLocaleString('es-EC') },
];

/** «Mis recursos»: los recursos de una asignatura, con su estado; cada uno se abre para revisar. */
export function Recursos({ aidInicial, onAbrir, onSesionVencida, onTrabajos }: RecursosProps) {
  const [lista, setLista] = useState<AsignaturaResumen[] | null>(null);
  const [aid, setAid] = useState(aidInicial ?? '');
  const [filas, setFilas] = useState<RecursoResumen[] | null>(null);
  const [error, setError] = useState('');
  const contexto = useRef(aid);
  contexto.current = aid;
  const consulta = useRef(0);
  const montado = useRef(true);

  const manejar = (e: unknown) => {
    if (e instanceof ErrorApi && e.estado === 401) return onSesionVencida();
    setError(e instanceof ErrorApi ? e.message : 'No hay conexión con el servidor.');
  };

  useEffect(() => {
    montado.current = true;
    cargarAsignaturas().then(a => { if (montado.current) { setLista(a); if (!contexto.current && a[0]) setAid(a[0].id); } }).catch(manejar);
    return () => { montado.current = false; consulta.current++; };
  }, []);

  const refrescar = (destino: string) => {
    const turno = ++consulta.current;
    return cargarRecursos(destino).then(f => {
      if (montado.current && contexto.current === destino && turno === consulta.current) setFilas(f);
    }).catch(e => { if (montado.current && contexto.current === destino && turno === consulta.current) manejar(e); });
  };

  useEffect(() => {
    if (!aid) return;
    setFilas(null);
    void refrescar(aid);
  }, [aid]);

  // Lo que sigue generándose: se consulta mientras la vista está abierta y, al terminar algo, se recarga la tabla.
  const [activos, setActivos] = useState<Trabajo[]>([]);
  const previos = useRef(0);
  useEffect(() => {
    if (!aid) return;
    let vigente = true;
    previos.current = 0;
    setActivos([]);
    const consultar = () => cargarTrabajos(aid).then(lista => {
      if (!vigente) return;
      const enCurso = lista.filter(t => !FINALES.has(t.estado));
      if (enCurso.length < previos.current) void refrescar(aid);
      previos.current = enCurso.length;
      setActivos(enCurso);
    }).catch(e => {
      if (vigente && e instanceof ErrorApi && e.estado === 401) onSesionVencida();
    });
    void consultar();
    const temporizador = setInterval(consultar, INTERVALO_MS);
    return () => { vigente = false; clearInterval(temporizador); };
  }, [aid, onSesionVencida]);

  const rol = lista?.find(a => a.id === aid)?.rol ?? 'lector';

  return <>
    <h1 className="text-2xl font-bold">Mis recursos</h1>
    {error && <Alert tone="danger" role="alert">{error}</Alert>}
    {lista && lista.length === 0 && <Alert tone="info">Todavía no tienes asignaturas. Sube tu sílabo desde «Inicio».</Alert>}
    {lista && lista.length > 0 && <label className="block max-w-md">
      <span className="text-sm font-medium">Asignatura</span>
      <select value={aid} onChange={e => setAid(e.target.value)}
        className="mt-1 w-full rounded-lg border border-line bg-surface px-3 py-2">
        {lista.map(a => <option key={a.id} value={a.id}>{a.nombre}</option>)}
      </select>
    </label>}
    {activos.length > 0 && <Card title="En curso" description="Cada asignatura genera una herramienta a la vez; las demás esperan su turno.">
      <ul className="space-y-2">{activos.map(t => <li key={t.id} className="flex flex-wrap items-center gap-2 text-sm">
        <span className="font-medium">{nombreHerramienta(t.herramienta)}</span>
        <span className="text-muted">{nombreAmbito(t.ambito_id)}</span>
        <Badge tone={ETAPAS[t.estado].tono}>{ETAPAS[t.estado].texto}</Badge>
        {t.lotes_total > 0 && <span className="text-xs text-muted">lote {t.lotes_hechos} de {t.lotes_total}</span>}
      </li>)}</ul>
    </Card>}
    {aid && <DataTable caption="Recursos de la asignatura" columns={COLUMNAS} rows={filas ?? []} rowKey={r => r.id}
      loading={filas === null} emptyMessage="Aún no hay recursos. Elige una clase en «Mis asignaturas» para generarlos."
      onRowClick={r => onAbrir(aid, r.id, rol)} rowActionLabel={r => `Revisar ${nombreHerramienta(r.herramienta)}`} />}
    {aid && rol !== 'lector' && <ChatAjustes aid={aid} onSesionVencida={onSesionVencida}
      onActualizado={() => { void refrescar(aid); }} onTrabajos={ids => onTrabajos?.(aid, ids, rol)} />}
  </>;
}
