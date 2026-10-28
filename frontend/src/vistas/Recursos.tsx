import { useEffect, useRef, useState } from 'react';
import { Alert, Badge, DataTable, type Column } from '../components';
import { ErrorApi, asignaturas as cargarAsignaturas, recursos as cargarRecursos } from '../api/cliente';
import type { AsignaturaResumen, RecursoResumen } from '../api/tipos';
import { nombreAmbito, nombreHerramienta } from '../api/herramientas';
import { ChatAjustes } from '../components/ChatAjustes';

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
    {aid && <DataTable caption="Recursos de la asignatura" columns={COLUMNAS} rows={filas ?? []} rowKey={r => r.id}
      loading={filas === null} emptyMessage="Aún no hay recursos. Elige una clase en «Mis asignaturas» para generarlos."
      onRowClick={r => onAbrir(aid, r.id, rol)} rowActionLabel={r => `Revisar ${nombreHerramienta(r.herramienta)}`} />}
    {aid && rol !== 'lector' && <ChatAjustes aid={aid} onSesionVencida={onSesionVencida}
      onActualizado={() => { void refrescar(aid); }} onTrabajos={ids => onTrabajos?.(aid, ids, rol)} />}
  </>;
}
