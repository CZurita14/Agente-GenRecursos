import { useEffect, useState, type ReactNode } from 'react';
import { CheckCircle2, Download, ShieldCheck } from 'lucide-react';
import { Alert, Badge, Button, Card, Modal } from '../components';
import { ErrorApi, recurso as cargarRecurso, urlExportar, validar } from '../api/cliente';
import type { Bloque, Recurso as TipoRecurso } from '../api/tipos';
import { nombreAmbito, nombreHerramienta } from '../api/herramientas';

interface RecursoProps {
  aid: string;
  rid: string;
  puedeValidar: boolean;
  onVolver: () => void;
  onSesionVencida: () => void;
}

interface Item { item_id: string; pregunta: string; contexto?: string; correcta: number; opciones: { texto: string; justificacion?: string }[] }

const esItems = (c: unknown): c is Item[] => Array.isArray(c) && c.every(i => i && typeof i === 'object' && 'opciones' in i);
/** Alertas del verificador y del revisor por ítem o sección (evidencia del coordinador). */
function alertas(r: TipoRecurso): Record<string, string[]> {
  const verificaciones = (r.evidencia.verificaciones ?? {}) as Record<string, string[]>;
  const veredictos = (r.evidencia.veredictos ?? {}) as Record<string, string>;
  const salida: Record<string, string[]> = {};
  for (const [id, fallos] of Object.entries(verificaciones)) if (fallos.length) salida[id] = [...fallos];
  for (const [id, veredicto] of Object.entries(veredictos)) if (veredicto !== 'ok') (salida[id] ??= []).push(veredicto);
  return salida;
}

/** Bloque de la presentación ordenada; el título baja de nivel dentro de un grupo (React escapa el texto). */
function VistaBloque({ b, nivel = 2 }: { b: Bloque; nivel?: number }): ReactNode {
  const Titulo = `h${Math.min(nivel + 1, 6)}` as 'h3';
  const titulo = <Titulo className={nivel === 2 ? 'font-bold' : 'text-sm font-bold'}>{b.titulo}</Titulo>;
  if (b.tipo === 'texto') return <section>{titulo}<p className="text-sm mt-1 whitespace-pre-line">{b.texto}</p></section>;
  if (b.tipo === 'lista') {
    const Lista = b.numerada ? 'ol' : 'ul';
    return <section>{titulo}<Lista className={`${b.numerada ? 'list-decimal' : 'list-disc'} pl-6 text-sm space-y-1 mt-1`}>
      {b.items.map((x, i) => <li key={i}>{x}</li>)}</Lista></section>;
  }
  if (b.tipo === 'tabla') return <section>{titulo}<div className="overflow-x-auto mt-1">
    <table className="w-full text-sm border-collapse">
      <thead><tr>{b.columnas.map((c, i) => <th key={i} scope="col" className="border border-line bg-app-soft px-2 py-1 text-left align-top">{c}</th>)}</tr></thead>
      <tbody>{b.filas.map((f, i) => <tr key={i}>{f.map((c, k) => <td key={k} className="border border-line px-2 py-1 align-top">{c}</td>)}</tr>)}</tbody>
    </table></div></section>;
  return <section className="rounded-lg border border-line p-3 space-y-3">{titulo}
    {b.bloques.map((x, i) => <VistaBloque key={i} b={x} nivel={nivel + 1} />)}</section>;
}

/** Pasos 4 y 5: revisar con las alertas, validar y descargar el HTML para Canvas. */
export function Recurso({ aid, rid, puedeValidar, onVolver, onSesionVencida }: RecursoProps) {
  const [r, setR] = useState<TipoRecurso | null>(null);
  const [error, setError] = useState('');
  const [confirmar, setConfirmar] = useState(false);
  const [validando, setValidando] = useState(false);

  const manejar = (e: unknown) => {
    if (e instanceof ErrorApi && e.estado === 401) return onSesionVencida();
    setError(e instanceof ErrorApi ? e.message : 'No hay conexión con el servidor.');
  };
  const recargar = () => cargarRecurso(aid, rid).then(setR).catch(manejar);
  useEffect(() => { recargar(); }, [aid, rid]);

  if (!r) return error ? <Alert tone="danger" role="alert">{error}</Alert> : <p className="text-muted" role="status">Cargando el recurso…</p>;

  const avisos = alertas(r);
  const cantidad = Object.keys(avisos).length;

  async function validarRecurso() {
    if (!r) return;
    setConfirmar(false);
    setValidando(true);
    setError('');
    try {
      setR(await validar(aid, r.id, r.revision));
    } catch (e) {
      if (e instanceof ErrorApi && e.estado === 409) { setError(e.message); await recargar(); } else manejar(e);
    } finally {
      setValidando(false);
    }
  }

  return <>
    <div>
      <Button variant="ghost" size="sm" onClick={onVolver}>← Volver</Button>
      <h1 className="text-2xl font-bold mt-2">{nombreHerramienta(r.herramienta)}</h1>
      <div className="flex flex-wrap items-center gap-2 mt-2">
        <Badge tone="brand">{nombreAmbito(r.ambito_id)}</Badge>
        {r.evidencia.borrador === true && <Badge tone="warning">Borrador</Badge>}
        {r.validado ? <Badge tone="success" icon={<CheckCircle2 aria-hidden="true" className="w-3 h-3" />}>Validado</Badge>
          : <Badge tone="neutral">Sin validar</Badge>}
        {cantidad > 0 && <Badge tone="warning">{cantidad} {cantidad === 1 ? 'alerta' : 'alertas'}</Badge>}
      </div>
    </div>
    {error && <Alert tone="danger" role="alert">{error}</Alert>}
    {r.silabo_actualizado && <Alert tone="info">El sílabo cambió desde que se generó este recurso.</Alert>}

    <Card title="Paso 4 · Revisa el contenido">
      {esItems(r.contenido) ? <ol className="space-y-4">{r.contenido.map((item, n) => <li key={item.item_id}
        className={`rounded-lg border p-4 ${avisos[item.item_id] ? 'border-warning bg-warning-soft' : 'border-line'}`}>
        <p className="text-xs text-muted">Pregunta {n + 1}</p>
        {item.contexto && <p className="text-sm text-muted italic mt-1">{item.contexto}</p>}
        <p className="font-medium mt-1">{item.pregunta}</p>
        <ul className="mt-2 space-y-1 text-sm">{item.opciones.map((o, k) => <li key={k}
          className={k === item.correcta ? 'font-bold text-success' : ''}>
          {String.fromCharCode(65 + k)}) {o.texto}{k === item.correcta && ' ✓ (clave)'}
        </li>)}</ul>
        {avisos[item.item_id]?.map((a, i) => <Alert key={i} tone="warning" className="mt-2">{a}</Alert>)}
      </li>)}</ol> : <>
        {Object.entries(avisos).map(([id, lista]) => lista.map((a, i) => <Alert key={`${id}${i}`} tone="warning" className="mb-2">{a}</Alert>))}
        <div className="space-y-4">{r.presentacion.map((b, i) => <VistaBloque key={i} b={b} />)}</div>
      </>}
    </Card>

    <Card title="Paso 5 · Valida y descarga para Canvas" icon={<ShieldCheck aria-hidden="true" />}>
      {r.validado ? <div className="space-y-3">
        <Alert tone="success">Validado por {r.validado_por}. Ya puedes descargarlo y subirlo a Canvas.</Alert>
        <a href={urlExportar(aid, r.id)} download
          className="inline-flex items-center gap-2 rounded-lg bg-action hover:bg-action-hover text-white px-4 py-2 font-medium">
          <Download aria-hidden="true" className="w-4 h-4" />Descargar HTML para Canvas
        </a>
      </div> : puedeValidar ? <div className="space-y-3">
        <p className="text-sm text-muted">La descarga se habilita cuando validas el recurso: confirma que lo revisaste.</p>
        <Button onClick={() => cantidad > 0 ? setConfirmar(true) : validarRecurso()} loading={validando}>Validar recurso</Button>
      </div> : <p className="text-sm text-muted">Un editor o el dueño de la asignatura debe validarlo antes de descargarlo.</p>}
    </Card>

    <Modal isOpen={confirmar} onClose={() => setConfirmar(false)} title="¿Validar con alertas pendientes?"
      footer={<div className="flex gap-2 justify-end">
        <Button variant="secondary" onClick={() => setConfirmar(false)}>Seguir revisando</Button>
        <Button onClick={validarRecurso}>Validar de todos modos</Button>
      </div>}>
      <p className="text-sm">Este recurso tiene {cantidad} {cantidad === 1 ? 'alerta' : 'alertas'} del revisor o del verificador.
        Al validarlo confirmas que lo revisaste y que puede usarse con tus estudiantes.</p>
    </Modal>
  </>;
}
