import { useState } from 'react';
import { BookOpen, FolderOpen, Home, LogOut } from 'lucide-react';
import { AppLayout } from './components';
import { useSesion } from './sesion/useSesion';
import { Ingreso } from './vistas/Ingreso';
import { Inicio } from './vistas/Inicio';
import { Proximamente } from './vistas/Proximamente';

type Vista = 'inicio' | 'asignaturas' | 'recursos' | 'generar';

const MENU = [
  { id: 'inicio', label: 'Inicio', icon: <Home aria-hidden="true" className="w-4 h-4" /> },
  { id: 'asignaturas', label: 'Mis asignaturas', icon: <BookOpen aria-hidden="true" className="w-4 h-4" /> },
  { id: 'recursos', label: 'Mis recursos', icon: <FolderOpen aria-hidden="true" className="w-4 h-4" /> },
];

/** Sin sesión: ingreso. Con sesión: menú principal (opción B) y sus vistas. */
export default function App() {
  const { usuario, cargando, ingresar, salir } = useSesion();
  const [vista, setVista] = useState<Vista>('inicio');

  if (cargando) {
    return <AppLayout><p className="text-muted" role="status">Cargando…</p></AppLayout>;
  }
  if (!usuario) {
    return <AppLayout><Ingreso onIngresar={async (correo, codigo) => { await ingresar(correo, codigo); setVista('inicio'); }} /></AppLayout>;
  }

  const acciones = <div className="flex items-center gap-3 text-sm">
    <span className="text-header-muted hidden sm:inline" title="Sesión iniciada">{usuario.correo}</span>
    <button type="button" onClick={salir}
      className="flex items-center gap-1 px-3 py-2 rounded-lg text-header-muted hover:bg-header-border hover:text-white">
      <LogOut aria-hidden="true" className="w-4 h-4" /><span>Salir</span>
    </button>
  </div>;

  return <AppLayout items={MENU} activeId={vista === 'generar' ? 'inicio' : vista}
    onChange={id => setVista(id as Vista)} actions={acciones}>
    {vista === 'inicio' && <Inicio onGenerar={() => setVista('generar')} />}
    {vista === 'generar' && <Proximamente titulo="Generar herramientas" descripcion="La subida del sílabo llega en la siguiente tarea." />}
    {vista === 'asignaturas' && <Proximamente titulo="Mis asignaturas" descripcion="La lista de asignaturas llega en la siguiente tarea." />}
    {vista === 'recursos' && <Proximamente titulo="Mis recursos"
      descripcion="Aquí verás, revisarás y exportarás las herramientas generadas. Llega en la siguiente entrega del frontend." />}
  </AppLayout>;
}
