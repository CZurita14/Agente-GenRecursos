import { AppLayout, Button, Card } from './components';
import { useSesion } from './sesion/useSesion';
import { Ingreso } from './vistas/Ingreso';

/** Sin sesión: ingreso. Con sesión: la aplicación (el menú llega en la T4). */
export default function App() {
  const { usuario, cargando, ingresar, salir } = useSesion();

  if (cargando) {
    return <AppLayout><p className="text-muted" role="status">Cargando…</p></AppLayout>;
  }
  if (!usuario) {
    return <AppLayout><Ingreso onIngresar={ingresar} /></AppLayout>;
  }
  return <AppLayout actions={<Button variant="ghost" size="sm" onClick={salir}>Salir</Button>}>
    <Card title="Sesión iniciada">{usuario.correo}</Card>
  </AppLayout>;
}
