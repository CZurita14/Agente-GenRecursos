import { before, after, test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
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

async function gallery(options = {}) {
  const context = await browser.newContext(options);
  const page = await context.newPage();
  await page.goto(origin);
  await page.getByRole('button', { name: 'Explorar componentes' }).click();
  await page.getByRole('heading', { name: 'Galería de componentes' }).waitFor();
  return { context, page };
}
test('navegación móvil y layout sin desbordamiento en 320px', async () => {
  const { context, page } = await gallery({ viewport: { width: 320, height: 720 } });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  if (process.env.TEMPLATE_SCREENSHOTS) { await mkdir('test-results', { recursive: true }); await page.screenshot({ path: 'test-results/gallery-mobile.png', fullPage: true }); }
  await page.getByRole('button', { name: 'Abrir navegación' }).click();
  await page.getByRole('navigation', { name: 'Navegación móvil' }).getByRole('button', { name: 'Inicio', exact: true }).click();
  assert.equal(await page.getByRole('button', { name: 'Abrir navegación' }).getAttribute('aria-expanded'), 'false');
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  await context.close();
});
test('modal: foco inicial, contención con Tab, Escape y restauración', async () => {
  const { context, page } = await gallery();
  if (process.env.TEMPLATE_SCREENSHOTS) { await mkdir('test-results', { recursive: true }); await page.screenshot({ path: 'test-results/gallery-desktop.png', fullPage: true }); }
  const trigger = page.getByRole('button', { name: 'Abrir modal', exact: true });
  await trigger.click();
  await page.getByRole('dialog').waitFor();
  assert.equal(await page.getByLabel('Nombre de configuración').evaluate(node => node === document.activeElement), true);
  assert.equal(await page.evaluate(() => document.body.style.overflow), 'hidden');
  for (let i = 0; i < 8; i++) {
    await page.keyboard.press('Tab');
    assert.equal(await page.getByRole('dialog').evaluate(dialog => dialog.contains(document.activeElement)), true);
  }
  await page.keyboard.press('Shift+Tab');
  assert.equal(await page.getByRole('dialog').evaluate(dialog => dialog.contains(document.activeElement)), true);
  await page.keyboard.press('Escape');
  await page.getByRole('dialog').waitFor({ state: 'detached' });
  assert.equal(await trigger.evaluate(node => node === document.activeElement), true);
  assert.equal(await page.evaluate(() => document.body.style.overflow), '');
  await context.close();
});
test('tema: sistema, selección persistente y recuperación tras recargar', async () => {
  const { context, page } = await gallery({ colorScheme: 'dark' });
  assert.equal(await page.locator('html').evaluate(node => node.classList.contains('dark')), true);
  await page.getByLabel('Apariencia', { exact: true }).selectOption('light');
  await page.reload();
  assert.equal(await page.locator('html').evaluate(node => node.classList.contains('dark')), false);
  await page.getByRole('button', { name: 'Explorar componentes' }).click();
  await page.getByLabel('Apariencia', { exact: true }).selectOption('system');
  await page.emulateMedia({ colorScheme: 'dark' });
  await page.waitForFunction(() => document.documentElement.classList.contains('dark'));
  await page.emulateMedia({ colorScheme: 'light' });
  await page.waitForFunction(() => !document.documentElement.classList.contains('dark'));
  await context.close();
});
test('formulario: errores asociados y botón común sin envío accidental', async () => {
  const { context, page } = await gallery();
  await page.getByRole('button', { name: 'Enviar ejemplo' }).click();
  const input = page.getByRole('textbox', { name: 'Nombre', exact: true });
  assert.equal(await input.getAttribute('aria-invalid'), 'true');
  assert.ok((await input.getAttribute('aria-describedby')).includes('-error'));
  await input.fill('Ana');
  await page.getByRole('button', { name: 'Enviar ejemplo' }).click();
  await page.getByText('Formulario de ejemplo enviado por Ana.').waitFor();
  assert.equal(await page.getByRole('button', { name: 'Secundario', exact: true }).getAttribute('type'), 'button');
  assert.equal(await page.getByRole('button', { name: 'Guardando…' }).isDisabled(), true);
  await page.getByRole('button', { name: 'Ver Elemento A' }).focus();
  await page.keyboard.press('Enter');
  await page.getByRole('dialog').getByText('Elemento A: Activo').waitFor();
  await context.close();
});
test('archivos: rechazo por tipo, selección repetida y validación por arrastre', async () => {
  const { context, page } = await gallery();
  const input = page.locator('input[type=file]');
  await input.setInputFiles({ name: 'datos.txt', mimeType: 'text/plain', buffer: Buffer.from('x') });
  await page.getByText('datos.txt: Tipo de archivo no permitido.').waitFor();
  const file = { name: 'informe.pdf', mimeType: 'application/pdf', buffer: Buffer.from('pdf') };
  await input.setInputFiles(file);
  await page.getByText('Seleccionados: informe.pdf').waitFor();
  assert.equal(await input.inputValue(), '');
  await input.setInputFiles(file);
  assert.equal(await input.inputValue(), '');
  const data = await page.evaluateHandle(() => {
    const transfer = new DataTransfer();
    transfer.items.add(new File(['bad'], 'script.exe', { type: 'application/octet-stream' }));
    return transfer;
  });
  await page.getByRole('button', { name: 'Seleccionar archivos' }).locator('..').dispatchEvent('drop', { dataTransfer: data });
  await page.getByText('script.exe: Tipo de archivo no permitido.').waitFor();
  await context.close();
});
test('colores con alfa generan fondo y bordes; texto principal conserva contraste', async () => {
  const { context, page } = await gallery({ colorScheme: 'light' });
  const styles = await page.getByText('Métrica', { exact: true }).locator('..').locator('..').evaluate(node => getComputedStyle(node).backgroundColor);
  assert.match(styles, /0\.6/);
  const alert = page.getByText('Operación completada.').locator('..');
  const border = await alert.evaluate(node => getComputedStyle(node).borderTopColor);
  assert.match(border, /0\.3/);
  const color = await page.getByRole('button', { name: 'Abrir modal', exact: true }).evaluate(node => ({
    bg: getComputedStyle(node).backgroundColor, fg: getComputedStyle(node).color,
  }));
  assert.equal(color.bg, 'rgb(154, 57, 0)');
  assert.equal(color.fg, 'rgb(255, 255, 255)');
  await context.close();
});

test('producción en subcarpeta: arranque, logo y favicon sin errores', async () => {
  const build = spawn(process.execPath, ['node_modules/vite/bin/vite.js', 'build', '--base=/demo/', '--outDir=test-results/subpath-dist'], { stdio: ['ignore', 'pipe', 'pipe'] });
  let output = '';
  build.stdout.on('data', chunk => { output += chunk; });
  build.stderr.on('data', chunk => { output += chunk; });
  const exitCode = await new Promise((resolve, reject) => { build.on('error', reject); build.on('exit', resolve); });
  assert.equal(exitCode, 0, output);
  const preview = spawn(process.execPath, ['node_modules/vite/bin/vite.js', 'preview', '--host', '127.0.0.1', '--port', '4188', '--strictPort', '--base=/demo/', '--outDir=test-results/subpath-dist'], { stdio: ['ignore', 'pipe', 'pipe'] });
  let previewOutput = '';
  preview.stdout.on('data', chunk => { previewOutput += chunk; });
  preview.stderr.on('data', chunk => { previewOutput += chunk; });
  const context = await browser.newContext();
  try {
    const url = 'http://127.0.0.1:4188/demo/';
    let ready = false;
    for (let attempt = 0; attempt < 100; attempt++) {
      if (preview.exitCode !== null) throw new Error(previewOutput);
      try { ready = (await fetch(url)).ok; } catch { /* Esperando preview. */ }
      if (ready) break;
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    assert.ok(ready, previewOutput);
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(url);
    await page.getByRole('button', { name: 'Explorar componentes' }).click();
    await page.getByRole('heading', { name: 'Galería de componentes' }).waitFor();
    const logo = page.getByRole('img', { name: 'Universidad Tecnológica Indoamérica' });
    await logo.evaluate(node => node.decode());
    assert.ok((await logo.getAttribute('src')).startsWith('/demo/'));
    assert.ok((await page.locator('link[rel=icon]').getAttribute('href')).includes('/demo/favicon.svg'));
    assert.equal((await context.request.get(url + 'favicon.svg')).ok(), true);
    assert.deepEqual(errors, []);
  } finally {
    await context.close();
    preview.kill();
  }
});
