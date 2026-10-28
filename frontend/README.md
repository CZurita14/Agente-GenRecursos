# Plantilla base UTI

Base reutilizable para aplicaciones frontend institucionales. Incluye React 18, TypeScript estricto, Vite 8, Tailwind CSS 4 y componentes sin dependencias de negocio.

## Arranque

Requiere Node.js 22.18 o superior; se recomienda Node.js 24 LTS.

```bash
npm ci
npm run dev
```

La aplicación muestra una página de inicio y una galería de componentes. Los ejemplos no cargan datos externos ni envían archivos a un servidor.

## Iniciar un proyecto nuevo

1. Copia el proyecto sin `node_modules`, `dist` ni `.git`. Crea un repositorio propio para la nueva aplicación.
2. Cambia el nombre de `package.json` y ejecuta `npm install --package-lock-only` para actualizar el lockfile.
3. Personaliza `BRAND_CONFIG` en `src/theme/theme.ts`: institución, título, subtítulo, versión y recursos de marca.
4. Reemplaza los recursos de `public/`. El título de la pestaña y el favicon se aplican desde la configuración al arrancar.
5. Reemplaza `src/App.tsx` con tus vistas. Puedes eliminar `src/examples/` cuando ya no necesites la galería.
6. Conserva `ThemeProvider` en `main.tsx` y usa `AppLayout` para compartir cabecera, pie, navegación y enlace para saltar al contenido.
7. Ejecuta las comprobaciones antes de publicar.

Arranque mínimo:

```tsx
import { AppLayout, Card } from './components';

export default function App() {
  return (
    <AppLayout>
      <h1 className="text-2xl font-bold">Mi aplicación</h1>
      <Card title="Inicio">Contenido de mi proyecto.</Card>
    </AppLayout>
  );
}
```

Si quitas o cambias la galería, adapta también las pruebas de navegador: verifican la demostración incluida.

## Estructura

```text
public/                         Logo y favicon
src/
  components/                   Componentes y tipos públicos
  css/styles.css                Tokens, utilidades Tailwind y estilos globales
  examples/ComponentGallery.tsx  Demostración aislada
  theme/theme.ts                Marca y lectura de colores desde JS
  theme/ThemeProvider.tsx        Estado y persistencia del tema
  utils/files.ts                Validación de selección de archivos
  App.tsx                       Punto para construir las vistas del proyecto
  main.tsx                      Inicialización de marca, tema y React
tests/
  files.test.ts                 Reglas de archivos
  type-contracts.ts             Contratos comprobados por TypeScript
  browser.test.mjs               Interacciones reales en navegador
```

## Componentes

Todos los componentes y sus tipos se exportan desde `src/components/index.ts`. Aceptan `className` y los atributos HTML pertinentes. Los controles `Button`, `Input` y `Toggle` admiten `ref`.

| Componente | Contrato principal |
| --- | --- |
| AppLayout | `children`, navegación de Navbar, `brand` y contenido opcional de `footer`. Incluye el único `main` de la página. |
| Navbar | `items`, `activeId`, `onChange`, `actions`, `brand`, `isDarkMode`, `onToggleTheme`. Menú móvil con Escape y controles accesibles. |
| Footer | `institution` o contenido propio mediante `children`. |
| Card | `title`, `description`, `icon`, `actions`, `children`. El título usa h2; organiza los encabezados de tu vista en consecuencia. |
| StatCard | `label`, `value`, `icon`, `status`, `statusTone`. |
| Button | `variant`: primary, secondary, ghost, danger. `size`: sm, md. `loading` deshabilita la acción y anuncia ocupación. |
| Input | Atributos nativos, `label`, `hint`, `error`, `containerClassName`. Relaciona ayuda y error con el campo. |
| Toggle | `checked`, `onChange(boolean)`, `label`, atributos de checkbox y estado disabled. |
| Badge | `tone`: neutral, brand, highlight, success, warning, danger, info; `icon`. |
| Alert | `tone`: success, warning, danger, info. Usa role=status; pasa role=alert si necesitas un anuncio urgente. |
| Modal | `isOpen`, `onClose`, `title`, `icon`, `footer`, `initialFocusRef`, `closeOnBackdrop` (false por defecto). |
| DropZone | `onFiles`, `onReject`, `accept`, `multiple` (false), `maxSize` en bytes, `disabled`, `title`, `hint`. |
| DataTable | `columns`, `rows`, `rowKey`, `caption` obligatorio, `loading`, `emptyMessage`, `onRowClick`, `rowActionLabel`. |

### Formularios

Button usa `type="button"` por defecto. Indica `type="submit"` para enviar un formulario.

```tsx
<Input
  label="Correo"
  name="email"
  type="email"
  autoComplete="email"
  required
  hint="Usa tu correo institucional."
  error={errors.email}
/>
<Button type="submit" loading={saving}>Guardar</Button>
```

Los errores y la validación pertenecen a cada proyecto. Si omites una etiqueta visible, proporciona `aria-label` o `aria-labelledby`. Esto también aplica a botones que solo muestran un icono y toggles sin label.

### Modal

Se basa en el diálogo nativo del navegador, se monta en un portal y bloquea el desplazamiento del fondo. Escape solicita `onClose`; el componente padre debe cambiar `isOpen` a false. Al cerrar, restaura el foco al elemento anterior.

Usa una referencia estable para elegir el foco inicial:

```tsx
const fieldRef = useRef<HTMLInputElement>(null);

<Modal isOpen={open} onClose={() => setOpen(false)}
  title="Editar" initialFocusRef={fieldRef}>
  <Input ref={fieldRef} label="Nombre" />
</Modal>
```

El contenido alto tiene desplazamiento interno. Evita abrir varios modales anidados; encadena los pasos dentro de un único diálogo.

### Archivos

```tsx
<DropZone
  accept=".pdf,image/*"
  multiple
  maxSize={2 * 1024 * 1024}
  onFiles={files => setSelectedFiles(files)}
  onReject={rejections => console.info(rejections)}
/>
```

Se aplican las mismas reglas al selector y al arrastre. Si multiple=false y llegan varios, se rechaza toda la selección. En modo múltiple se entregan los válidos y se informan los rechazados. El componente muestra los errores y permite volver a seleccionar el mismo archivo.

No realiza uploads. Al integrar un backend, valida también allí los archivos: accept y el MIME informado por el navegador no verifican su contenido.

### Tabla tipada

```tsx
interface User { id: number; name: string }
const columns: Column<User>[] = [
  { key: 'name', header: 'Nombre' },
  { key: 'actions', header: 'Código', render: user => user.id },
];
<DataTable caption="Usuarios" columns={columns} rows={users}
  rowKey={user => user.id}
  onRowClick={user => openDetail(user)}
  rowActionLabel={user => `Ver ${user.name}`} />
```

Una columna sin render exige una propiedad válida del registro. Los valores complejos requieren render. onRowClick muestra un botón “Ver detalle” por fila, accesible con teclado; no convierte toda la fila en una acción. Ordenación, filtros, paginación y obtención de datos pertenecen al proyecto.

### Navegación

Los items con `href` se muestran como enlaces; el resto son botones controlados mediante `activeId` y `onChange`. La plantilla no instala un router. Para rutas SPA, integra el router elegido y adapta Navbar cuando necesites su componente Link.

## Marca, colores y tema

La fuente única de colores es `src/css/styles.css`. Los tokens `--uti-*` usan canales RGB, y `@theme inline` los expone mediante clases semánticas como:

```text
bg-app       bg-surface     text-fg        text-muted
border-line  bg-brand-soft  text-brand
bg-highlight bg-action     text-action-ink
bg-success-soft text-success
```

Los modificadores de alfa funcionan: `bg-app/60`, `border-success/30`. No es necesario mantener un segundo objeto de colores en TypeScript. Para gráficos o integraciones JS, usa `getThemeColor('success')` después de montar el documento.

El naranja highlight conserva la identidad visual. action es un naranja más oscuro para botones con texto blanco; action-ink ajusta el texto de acento según el tema. Al cambiar la paleta, revisa el contraste de cada combinación.

```tsx
const { theme, preference, setPreference, toggleTheme } = useTheme();
setPreference('system'); // También 'light' o 'dark'
```

La preferencia sigue al sistema inicialmente, se conserva en localStorage con la clave uti-theme y se sincroniza entre pestañas. Si el almacenamiento está bloqueado, el tema continúa funcionando durante la sesión.

Tailwind se integra directamente con Vite. No se requieren tailwind.config.js ni postcss.config.js. La base está orientada a navegadores modernos: Chrome 111+, Safari 16.4+ y Firefox 128+, según los [requisitos de Tailwind 4](https://tailwindcss.com/docs/upgrade-guide#browser-requirements).

## Comprobaciones

```bash
npm run typecheck       # Tipos estrictos y contratos de componentes
npm test                # Reglas de archivos
npm run build           # Compilación de producción en dist/
npm run check           # Tipos, pruebas unitarias y compilación
npx playwright install chromium
npm run test:browser    # Móvil, teclado, modal, tema, formularios y archivos
npm audit
```

Las pruebas de navegador levantan y cierran su propio servidor en 127.0.0.1:4187. Deja ese puerto libre. Para usar Chrome instalado en Windows, ejecuta en PowerShell:

```powershell
$env:PLAYWRIGHT_CHANNEL = 'chrome'
npm run test:browser
```

Las pruebas de navegador son independientes de npm run check porque requieren un navegador instalado. No hay backend ni servicios necesarios para ejecutarlas.

## Despliegue

```bash
npm run build
npm run preview
```

Publica el contenido de dist/. Para alojar bajo una subcarpeta:

```bash
npm run build -- --base=/mi-aplicacion/
```

Los recursos configurados con import.meta.env.BASE_URL respetan esa base. Si añades un router con rutas de historial, configura el servidor para resolver las rutas de la aplicación hacia index.html.

No copies secretos al frontend. Las futuras variables VITE_* son visibles en el código entregado al navegador.

## Alcance

Esta es una plantilla para iniciar proyectos mediante copia, no una biblioteca publicada en npm. Conserva el layout y los componentes como base; incorpora rutas, servicios, autenticación, estado de negocio y pruebas propias cuando el proyecto los necesite.
