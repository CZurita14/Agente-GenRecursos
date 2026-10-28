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

const MENU_ASIG = [{ numero: 2, inicio: '2026-10-12', fin: '2026-10-18', cierra_momentos: [2], clases: [
  { clase_id: 'M2-S1', numero_clase: 1, dia: 'mie', fecha: '2026-10-14', momento: 2, momento_titulo: 'Planeación',
    contenidos: ['DISTRIBUCIONES'], ra: ['RA2'], entregables: [] }] },
{ numero: 3, inicio: '2026-10-19', fin: '2026-10-25', cierra_momentos: [3], clases: [
  { clase_id: 'M3-S1', numero_clase: 2, dia: 'mie', fecha: '2026-10-21', momento: 3, momento_titulo: 'Resolución',
    contenidos: ['ESTIMACIÓN'], ra: ['RA3'], entregables: [] }] }];
const RECURSO = validado => ({ id: 'r1', trabajo_id: 't1', ambito_id: 'M2-S1', herramienta: 'cuestionario', version_silabo: '1.0',
  estado: 'requiere_revision', revision: 0, creado: '2026-10-28T10:00:00Z', silabo_actualizado: false, evidencia_vigente: true,
  validado: !!validado, validado_por: validado ? USUARIO.correo : null, validado_en: validado ? '2026-10-28T11:00:00Z' : null,
  evidencia: { borrador: true, verificaciones: { i1: [] }, veredictos: { i1: 'el revisor considera correctas las opciones 1 y 3' } },
  contenido: [{ item_id: 'i1', pregunta: '¿Qué prueba corresponde?', contexto: 'Una empresa ficticia.', correcta: 0,
    opciones: [{ texto: 'Prueba t' }, { texto: 'ANOVA' }, { texto: 'Chi cuadrado' }, { texto: 'Regresión' }] }], presentacion: [] });
// Ficha: contenido con claves internas; la vista solo usa la presentación ordenada.
const FICHA = { ...RECURSO(false), id: 'r2', herramienta: 'ficha_clase', evidencia: {},
  contenido: { aplicacion: { clase_id: 'M2-S1' }, conceptual: { numero_clase: 1 } },
  presentacion: [
    { tipo: 'lista', titulo: 'Ideas clave', items: ['Idea A', 'Idea B'], numerada: false },
    { tipo: 'grupo', titulo: 'Ejemplo resuelto', bloques: [
      { tipo: 'texto', titulo: 'Enunciado', texto: 'Una tienda mide ventas.' },
      { tipo: 'lista', titulo: 'Pasos', items: ['Calcular la media', 'Interpretar'], numerada: true }] },
    { tipo: 'tabla', titulo: 'Cómo se valora', columnas: ['Indicador', 'Qué observar'], filas: [['Precisión', 'Cálculo correcto']] }] };

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
    // --- P6b: menú, catálogo, generación, avance, recurso, validación ---
    if (ruta === '/asignaturas/a1/menu') return json(200, { id: 'a1', rol: 'dueno', version_silabo: '1.0', menu: MENU_ASIG });
    if (ruta === '/asignaturas/a1/herramientas') {
      const restringido = url.searchParams.get('id') === 'M3';
      return json(200, { ambito: url.searchParams.get('ambito'), restringido, perfil_sugerido: 'fundamentacion',
        motivo: restringido ? 'La política de IA de este momento excluye la IA en una evaluación.' : null,
        politica_ia: 'Se permite IA como asistente.',
        herramientas: restringido ? [{ id: 'autoevaluacion_rubrica', recomendada: true }]
          : [{ id: 'cuestionario', recomendada: true }, { id: 'ficha_clase', recomendada: false }] });
    }
    if (ruta === '/asignaturas/a1/generar') return json(202, { trabajos: [{ id: 't1', herramienta: 'cuestionario', estado: 'en_cola' }] });
    if (ruta === '/asignaturas/a1/trabajos') {
      estado.consultas = (estado.consultas ?? 0) + 1;
      return json(200, [{ id: 't1', herramienta: 'cuestionario', ambito_tipo: 'clase', ambito_id: 'M2-S1', lotes_total: 1,
        lotes_hechos: 1, error: null, estado: 'requiere_revision', recurso_id: 'r1' }]);
    }
    if (ruta === '/asignaturas/a1/recursos') return json(200, [{ id: 'r1', trabajo_id: 't1', ambito_id: 'M2-S1',
      herramienta: 'cuestionario', version_silabo: '1.0', estado: 'requiere_revision', revision: 0, creado: '2026-10-28T10:00:00Z' },
      { id: 'r2', trabajo_id: 't2', ambito_id: 'M2-S1', herramienta: 'ficha_clase', version_silabo: '1.0', estado: 'listo',
        revision: 0, creado: '2026-10-28T10:05:00Z' }]);
    if (ruta === '/asignaturas/a1/recursos/r2') return json(200, FICHA);
    if (ruta === '/asignaturas/a1/recursos/r1') return json(200, RECURSO(estado.validado));
    if (ruta === '/asignaturas/a1/recursos/r1/validar') { estado.validado = true; return json(200, RECURSO(true)); }
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

// --- P6b: Mis recursos ----------------------------------------------------------------

async function abrirAsignatura(page) {
  await page.getByRole('navigation', { name: 'Navegación principal' }).getByRole('button', { name: 'Mis asignaturas', exact: true }).click();
  await page.getByRole('button', { name: 'Abrir ANALISIS DE DATOS' }).click();
  await page.getByRole('heading', { name: 'ANALISIS DE DATOS' }).waitFor();
}

test('recorrido: clase → actividad → generar → avance → recurso', async () => {
  const { context, page, estado } = await abrir();
  await abrirAsignatura(page);
  await page.getByText('Semana 2 · 12/10 – 18/10').waitFor();
  await page.getByRole('button', { name: /mié 14\/10 · Clase 1/ }).click();
  await page.getByRole('heading', { name: 'Clase 1 · M2-S1' }).waitFor();
  await page.getByText('Se permite IA como asistente.').waitFor();
  await page.getByLabel('Cuestionario').check();
  await page.getByRole('button', { name: 'Generar' }).click();
  await page.getByRole('heading', { name: 'Generando herramientas' }).waitFor();
  await page.getByText('Lista · requiere tu revisión').waitFor();
  const consultas = estado.consultas;
  await page.getByRole('button', { name: 'Revisar' }).click();
  await page.getByRole('heading', { name: 'Cuestionario' }).waitFor();
  await page.waitForTimeout(4500);
  assert.equal(estado.consultas, consultas, 'la consulta de avance debe detenerse al terminar o salir');
  await context.close();
});

test('momento restringido muestra el aviso y solo lo permitido', async () => {
  const { context, page } = await abrir();
  await abrirAsignatura(page);
  await page.getByText('Cierra el Momento 3').waitFor();
  await page.getByRole('button', { name: 'Herramientas del momento' }).nth(1).click();
  await page.getByRole('alert').getByText('excluye la IA').waitFor();
  assert.equal(await page.getByRole('checkbox').count(), 1);
  assert.equal(await page.getByText('sin IA', { exact: true }).count(), 1);
  await context.close();
});

test('validar con alertas pide confirmación y habilita la descarga', async () => {
  const { context, page } = await abrir();
  await page.getByRole('navigation', { name: 'Navegación principal' }).getByRole('button', { name: 'Mis recursos', exact: true }).click();
  await page.getByRole('button', { name: 'Revisar Cuestionario' }).click();
  await page.getByText('el revisor considera correctas las opciones 1 y 3').waitFor();
  assert.equal(await page.getByRole('link', { name: 'Descargar HTML para Canvas' }).count(), 0);
  await page.getByRole('button', { name: 'Validar recurso' }).click();
  await page.getByRole('dialog').getByText('¿Validar con alertas pendientes?').waitFor();
  await page.getByRole('button', { name: 'Validar de todos modos' }).click();
  const enlace = page.getByRole('link', { name: 'Descargar HTML para Canvas' });
  await enlace.waitFor();
  assert.match(await enlace.getAttribute('href'), /\/api\/asignaturas\/a1\/recursos\/r1\/exportar\?formato=html$/);
  await context.close();
});

test('ficha: secciones en orden, con títulos legibles y sin claves internas', async () => {
  const { context, page } = await abrir();
  await page.getByRole('navigation', { name: 'Navegación principal' }).getByRole('button', { name: 'Mis recursos', exact: true }).click();
  await page.getByRole('button', { name: 'Revisar Ficha de clase' }).click();
  await page.getByRole('heading', { name: 'Ideas clave' }).waitFor();
  const titulos = await page.locator('main h3, main h4').allInnerTexts();
  assert.deepEqual(titulos.filter(t => t !== 'Paso 4 · Revisa el contenido' && !t.startsWith('Paso 5')),
    ['Ideas clave', 'Ejemplo resuelto', 'Enunciado', 'Pasos', 'Cómo se valora']);
  assert.equal(await page.locator('main ol li').count(), 2);
  await page.getByRole('columnheader', { name: 'Qué observar' }).waitFor();
  await page.getByRole('cell', { name: 'Cálculo correcto' }).waitFor();
  const texto = await page.locator('main').innerText();
  assert.ok(!/clase_id|numero_clase|Clase id|Numero clase/i.test(texto), 'no deben verse claves internas');
  await context.close();
});
