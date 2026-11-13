// Browser smoke test. Run from frontend/: npm run e2e (needs the Python venv at ../.venv
// and a Chrome/Chromium; set CHROME_PATH or let Playwright use channel "chrome").
import { spawn, execFileSync } from 'node:child_process';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { chromium } from 'playwright';

const root = new URL('../..', import.meta.url).pathname;
const python = join(root, '.venv/bin/python');
const dir = mkdtempSync(join(tmpdir(), 'snapnote-e2e-'));
const env = {
  ...process.env,
  SNAPNOTE_E2E: '1',
  SNAPNOTE_E2E_DB: join(dir, 'db.sqlite3'),
  DJANGO_SETTINGS_MODULE: 'tests.testproject.settings',
  PYTHONPATH: root,
};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let base = '';
let port = 8765;

async function startServer(extraEnv = {}) {
  const serverEnv = { ...env, ...extraEnv, SNAPNOTE_E2E_DB: join(dir, `db-${port}.sqlite3`) };
  execFileSync(python, ['-m', 'django', 'migrate', '-v0'], { env: serverEnv, cwd: root });
  const child = spawn(python, ['-m', 'django', 'runserver', `${port}`, '--noreload'], {
    env: serverEnv, cwd: root, stdio: 'ignore',
  });
  base = `http://127.0.0.1:${port}`;
  port += 1;
  for (let i = 0; i < 50; i++) {
    try { await fetch(base); break; } catch { await sleep(200); }
  }
  return child;
}

const results = [];
const check = (name, ok) => { results.push([name, ok]); console.log(`${ok ? 'PASS' : 'FAIL'} ${name}`); };

// Stubs getDisplayMedia with a canvas stream (the real share prompt can't be automated).
const STUB = `
  navigator.mediaDevices.getDisplayMedia = async () => {
    const c = document.createElement('canvas'); c.width = 640; c.height = 360;
    const x = c.getContext('2d'); x.fillStyle = '#2b6cb0'; x.fillRect(0, 0, 640, 360);
    setInterval(() => x.fillRect(0, 0, 640, 360), 50);
    return c.captureStream(20);
  };`;

async function scenario(browser, { capture, httpOnly = false }) {
  const label = (capture ? 'with capture' : 'without getDisplayMedia') + (httpOnly ? ' + HttpOnly CSRF cookie' : '');
  const context = await browser.newContext({ viewport: { width: 1000, height: 700 } });
  const page = await context.newPage();
  await page.addInitScript(capture ? STUB : "Object.defineProperty(navigator.mediaDevices, 'getDisplayMedia', { value: undefined });");
  await page.goto(`${base}/e2e-login/`);
  const fab = page.locator('#snapnote-root .snapnote-fab');
  await fab.waitFor();
  check(`${label}: button renders inside shadow DOM`, (await fab.count()) === 1);
  if (httpOnly) {
    const cookie = (await context.cookies()).find((c) => c.name === 'csrftoken');
    check(`${label}: csrftoken cookie exists and is HttpOnly`, !!cookie?.httpOnly);
    check(`${label}: JS cannot read it`, !(await page.evaluate(() => document.cookie)).includes('csrftoken'));
  }
  await fab.click();

  const title = `E2E ${label}`;
  if (capture) {
    await page.locator('.snapnote-editor').waitFor();
    const canvas = page.locator('.snapnote-editor-canvas');
    await canvas.waitFor();
    const box = await canvas.boundingBox();
    await page.mouse.move(box.x + 100, box.y + 100);
    await page.mouse.down();
    await page.mouse.move(box.x + 250, box.y + 180, { steps: 5 });
    await page.mouse.up();
    await page.getByRole('button', { name: 'Done' }).click();
    check(`${label}: file input hidden when capture worked`, (await page.locator('input[type=file]').count()) === 0);
    check(`${label}: annotations layer previewed`, (await page.locator('.snapnote-preview-annotations').count()) === 1);
  } else {
    await page.locator('input[type=file]').waitFor();
    check(`${label}: file input shown`, true);
    const { writeFileSync } = await import('node:fs');
    const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mP8z8BQz0AEYBxVSF+FABJADveWkH6oAAAAAElFTkSuQmCC', 'base64');
    const file = join(dir, 'm.png'); writeFileSync(file, png);
    await page.locator('input[type=file]').setInputFiles(file);
    await page.locator('.snapnote-editor-canvas').waitFor();
    await page.getByRole('button', { name: 'Done' }).click();
    check(`${label}: uploaded image reaches the preview`, (await page.locator('.snapnote-preview img').count()) >= 1);
  }
  await page.locator('.snapnote-field input:not([type=file])').first().fill(title);
  await page.getByRole('button', { name: 'Send' }).click();
  await page.locator('.snapnote-toast').waitFor();
  check(`${label}: success notice`, true);

  await page.goto(`${base}/snapnote/`);
  check(`${label}: ticket listed`, (await page.getByText(title).count()) === 1);
  await page.getByText(title).click();
  const imgs = await page.locator('.snapnote-shot-frame img').count();
  check(`${label}: detail shows screenshot${capture ? ' + annotations' : ''}`, imgs === (capture ? 2 : 1));
  if (capture) {
    await page.locator('#snapnote-ann-toggle').uncheck();
    check(`${label}: annotations switch hides layer`, !(await page.locator('.snapnote-annotations').isVisible()));
  }
  await context.close();
}

let browser;
let server;
try {
  browser = await chromium.launch({
    channel: process.env.CHROME_PATH ? undefined : 'chrome',
    executablePath: process.env.CHROME_PATH,
  });
  server = await startServer();
  await scenario(browser, { capture: true });
  await scenario(browser, { capture: false });
  server.kill();
  // Hardened hosts: the CSRF cookie is HttpOnly, so the token must come from the page props.
  server = await startServer({ SNAPNOTE_E2E_HTTPONLY: '1' });
  await scenario(browser, { capture: true, httpOnly: true });
} finally {
  await browser?.close();
  server?.kill();
}
process.exit(results.every(([, ok]) => ok) ? 0 : 1);
