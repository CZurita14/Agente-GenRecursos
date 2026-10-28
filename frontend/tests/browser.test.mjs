// Pruebas reales en navegador del menú (P6a). La API se simula con page.route: sin backend.
import { before, after, test } from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { chromium } from 'playwright';

let browser;
let server;
const origin = 'http://127.0.0.1:4187';
let serverOutput = '';
before(async () => {
  server = spawn(process.execPath, ['node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', '4187', '--strictPort'], { stdio: ['ignore', 'pipe', 'pipe'] });
  server.stdout.on('data', chunk => { serverOutput += chunk; });
  server.stderr.on('data', chunk => { serverOutput += chunk; });
  let ready = false;
  for (let attempt = 0; attempt < 100; attempt++) {
    if (server.exitCode !== null) throw new Error(serverOutput);
    try { ready = (await fetch(origin)).ok; } catch { /* Esperando Vite. */ }
    if (ready) break;
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  assert.ok(ready, serverOutput || 'Vite no inició.');
  browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL || undefined });
});
after(async () => { await browser?.close(); server?.kill(); });

const USUARIO = { correo: 'docente@uti.edu.ec', rol: 'docente' };
const SUBIDO = {
  id: 'a1', agente: 'ingenierias', clases_cambiadas: [],
  menu: [{ numero: 2, inicio: '2026-10-12', fin: '2026-10-18', cierra_momentos: [2],
    clases: [{ clase_id: 'M2-S1' }, { clase_id: 'M2-S2' }] }],
};

/** API simulada: `sesion` dice si /auth/yo responde 200 o 401. */
async function abrir({ sesion = true, viewport, rutas = {} } = {}) {
  const context = await browser.newContext(viewport ? { viewport } : {});
  const page = await context.newPage();
  const estado = { sesion, llamadas: [] };
  // Solo rutas que empiezan por /api/: «**/api/**» también capturaría el módulo /src/api/cliente.ts.
  await page.route(url => url.pathname.startsWith('/api/'), async route => {
    const url = new URL(route.request().url());
    const ruta = url.pathname.replace(/^\/api/, '');
    estado.llamadas.push({ ruta, metodo: route.request().method(), tipo: route.request().headers()['content-type'] });
    if (rutas[ruta]) return rutas[ruta](route, estado);
    const json = (status, body) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
    if (ruta === '/auth/yo') return estado.sesion ? json(200, USUARIO) : json(401, { detail: 'Sesión requerida' });
    if (ruta === '/auth/codigo') return json(200, { mensaje: 'ok' });
    if (ruta === '/auth/verificar') { estado.sesion = true; return json(200, { mensaje: 'Sesión iniciada' }); }
    if (ruta === '/auth/salir') { estado.sesion = false; return json(200, { mensaje: 'Sesión cerrada' }); }
    if (ruta === '/asignaturas') return json(200, [{ id: 'a1', nombre: 'ANALISIS DE DATOS', codigo_pf: 'B26-SOFT-3', version_silabo: '1.0', agente: 'ingenierias', rol: 'dueno', dueno: USUARIO.correo }]);
    if (ruta === '/silabos') return json(201, SUBIDO);
    return json(404, { detail: 'no simulada' });
  });
  await page.goto(origin);
  // Esperar a que termine la consulta inicial de sesión (sin esto se ve «Cargando…»).
  await (sesion ? page.getByRole('heading', { name: '¿Qué quieres hacer hoy?' })
    : page.getByLabel('Correo institucional')).waitFor();
  return { context, page, estado };
}

test('ingreso en dos pasos lleva al menú', async () => {
  const { context, page } = await abrir({ sesion: false });
  await page.getByLabel('Correo institucional').fill('docente@uti.edu.ec');
  await page.getByRole('button', { name: 'Enviar código' }).click();
  await page.getByLabel('Código de acceso').fill('123456');
  await page.getByRole('button', { name: 'Ingresar' }).click();
  await page.getByRole('heading', { name: '¿Qué quieres hacer hoy?' }).waitFor();
  await context.close();
});

test('menú con tres pestañas y perfil docente en espera', async () => {
  const { context, page } = await abrir();
  const nav = page.getByRole('navigation', { name: 'Navegación principal' });
  for (const nombre of ['Inicio', 'Mis asignaturas', 'Mis recursos']) {
    assert.equal(await nav.getByRole('button', { name: nombre, exact: true }).count(), 1, nombre);
  }
  const perfil = page.locator('section[aria-labelledby="camino-perfil"]');
  assert.equal(await perfil.getAttribute('aria-disabled'), 'true');
  assert.equal(await perfil.getByRole('button').count(), 0);
  assert.equal(await perfil.getByText('En espera').count(), 1);
  await context.close();
});

test('Empezar lleva a subir el sílabo y muestra el resumen', async () => {
  const { context, page, estado } = await abrir();
  await page.getByRole('button', { name: 'Empezar' }).click();
  await page.getByRole('heading', { name: 'Generar herramientas' }).waitFor();
  await page.locator('input[type="file"]').setInputFiles({ name: 'silabo.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.4') });
  await page.getByRole('button', { name: 'Subir sílabo' }).click();
  await page.getByText('Agente asignado').waitFor();
  assert.match(await page.getByText('Agente asignado').innerText(), /1 semanas y 2 clases/);
  const subida = estado.llamadas.find(l => l.ruta === '/silabos');
  assert.equal(subida.tipo, 'application/pdf');
  await page.getByRole('button', { name: 'Ver mis asignaturas' }).click();
  await page.getByRole('table', { name: 'Mis asignaturas' }).getByText('ANALISIS DE DATOS').waitFor();
  await context.close();
});

test('un 401 a mitad del uso devuelve al ingreso', async () => {
  const { context, page, estado } = await abrir();
  estado.sesion = false;
  await page.route(url => url.pathname === '/api/asignaturas', route => route.fulfill({ status: 401, contentType: 'application/json', body: '{"detail":"Sesión requerida"}' }));
  await page.getByRole('navigation', { name: 'Navegación principal' }).getByRole('button', { name: 'Mis asignaturas', exact: true }).click();
  await page.getByLabel('Correo institucional').waitFor();
  await context.close();
});

test('error de la API con mensaje claro (422 sílabo ilegible)', async () => {
  const { context, page } = await abrir({ rutas: { '/silabos': route => route.fulfill({ status: 422, contentType: 'application/json', body: JSON.stringify({ detail: 'No se reconoce la plantilla institucional del sílabo.' }) }) } });
  await page.getByRole('button', { name: 'Empezar' }).click();
  await page.locator('input[type="file"]').setInputFiles({ name: 'otro.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.4') });
  await page.getByRole('button', { name: 'Subir sílabo' }).click();
  await page.getByRole('alert').getByText('No se reconoce la plantilla institucional').waitFor();
  await context.close();
});

test('salir cierra la sesión', async () => {
  const { context, page } = await abrir();
  await page.getByRole('button', { name: 'Salir' }).click();
  await page.getByLabel('Correo institucional').waitFor();
  await context.close();
});

test('móvil: sin desbordamiento, menú colapsado y tarjetas apiladas', async () => {
  const { context, page } = await abrir({ viewport: { width: 360, height: 760 } });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  await page.getByRole('button', { name: 'Abrir navegación' }).click();
  await page.getByRole('navigation', { name: 'Navegación móvil' }).getByRole('button', { name: 'Mis recursos', exact: true }).click();
  await page.getByRole('heading', { name: 'Mis recursos' }).waitFor();
  await context.close();
});
