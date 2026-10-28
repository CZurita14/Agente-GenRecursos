import { AppLayout, Card } from './components';

/** Punto de entrada de las vistas; el menú se construye en las siguientes tareas. */
export default function App() {
  return <AppLayout>
    <h1 className="text-2xl font-bold">Recursos de estudio</h1>
    <Card title="En construcción">El menú principal se agrega en las siguientes tareas.</Card>
  </AppLayout>;
}
