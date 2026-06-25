// Prerender de rutas a HTML estático tras el build (mejora indexación y previews
// sociales por página). Es un paso BEST-EFFORT y NO-FATAL: si no hay navegador
// disponible (p. ej. en un entorno sin Chromium) simplemente se omite y el sitio
// queda en CSR como antes — nunca rompe el build.
//
// En el sandbox usa el Chromium pre-instalado (/opt/pw-browsers); en Netlify usa
// el que descargue Playwright. Cada ruta se renderiza en un Chromium headless y se
// guarda el HTML resultante (con su <title>/meta ya aplicados por SeoService).
import { createServer } from 'node:http';
import { readFile, writeFile, mkdir, stat } from 'node:fs/promises';
import { existsSync, readdirSync } from 'node:fs';
import { join, extname, dirname } from 'node:path';

const ROOT = join(process.cwd(), 'dist', 'maya-predice', 'browser');
const API = process.env.SITEMAP_API_URL || 'https://apimayapredice.marcostorresalarcon.com/api/v1';
const PORT = 4321;

const STATIC_ROUTES = ['/', '/en-vivo', '/fixture', '/equipos', '/simulacion', '/privacidad'];

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.webp': 'image/webp',
  '.woff2': 'font/woff2',
  '.txt': 'text/plain',
  '.xml': 'application/xml',
};

async function fail(msg, err) {
  console.warn(`[prerender] omitido: ${msg}${err ? ' — ' + (err.message || err) : ''}`);
  process.exit(0); // NO-FATAL: el build continúa con CSR.
}

if (!existsSync(join(ROOT, 'index.html'))) {
  await fail('no existe dist/maya-predice/browser/index.html');
}

// Playwright es opcional: si no está, se omite el prerender.
let chromium;
try {
  ({ chromium } = await import('playwright'));
} catch (e) {
  await fail('playwright no disponible', e);
}

// Localiza un ejecutable de Chromium pre-instalado (sandbox); en Netlify se deja
// que Playwright use el suyo (executablePath undefined).
function findPreinstalledChrome() {
  const base = process.env.PLAYWRIGHT_BROWSERS_PATH || '/opt/pw-browsers';
  try {
    if (!existsSync(base)) return undefined;
    for (const dir of readdirSync(base)) {
      if (!dir.startsWith('chromium-')) continue;
      const exe = join(base, dir, 'chrome-linux', 'chrome');
      if (existsSync(exe)) return exe;
    }
  } catch {
    /* noop */
  }
  return undefined;
}

async function teamCodes() {
  try {
    const res = await fetch(`${API}/teams`, { signal: AbortSignal.timeout(8000) });
    if (!res.ok) return [];
    const teams = await res.json();
    return (Array.isArray(teams) ? teams : []).map((t) => t.code).filter(Boolean);
  } catch {
    return [];
  }
}

// Servidor estático con fallback SPA (rutas desconocidas → index.html).
function startServer() {
  const indexHtml = join(ROOT, 'index.html');
  return new Promise((resolve) => {
    const server = createServer(async (req, res) => {
      try {
        const url = decodeURIComponent((req.url || '/').split('?')[0]);
        let filePath = join(ROOT, url);
        let isFile = false;
        try {
          isFile = (await stat(filePath)).isFile();
        } catch {
          isFile = false;
        }
        if (!isFile || extname(filePath) === '') filePath = indexHtml;
        const body = await readFile(filePath);
        res.writeHead(200, { 'Content-Type': MIME[extname(filePath)] || 'application/octet-stream' });
        res.end(body);
      } catch {
        res.writeHead(404);
        res.end('not found');
      }
    });
    server.listen(PORT, '127.0.0.1', () => resolve(server));
  });
}

async function run() {
  const routes = [...STATIC_ROUTES, ...(await teamCodes()).map((c) => `/equipos/${c}`)];
  const server = await startServer();
  const executablePath = findPreinstalledChrome();

  let browser;
  try {
    browser = await chromium.launch({
      executablePath,
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
    });
  } catch (e) {
    server.close();
    await fail('no se pudo lanzar Chromium', e);
  }

  const rendered = [];
  for (const route of routes) {
    const page = await browser.newPage();
    try {
      await page.goto(`http://127.0.0.1:${PORT}${route}`, {
        waitUntil: 'networkidle',
        timeout: 20000,
      });
      // Espera a que Angular pinte y SeoService fije el título.
      await page
        .waitForFunction(
          () => {
            const root = document.querySelector('app-root');
            return !!document.title && !!root && root.children.length > 0;
          },
          { timeout: 8000 },
        )
        .catch(() => {});
      const html = await page.content();
      if (html && html.length > 500) rendered.push({ route, html });
    } catch (e) {
      console.warn(`[prerender] ruta ${route} falló: ${e.message}`);
    } finally {
      await page.close();
    }
  }

  await browser.close();
  server.close();

  // Escribe todo al final (no modificar index.html mientras el server lo sirve).
  let written = 0;
  for (const { route, html } of rendered) {
    const out =
      route === '/' ? join(ROOT, 'index.html') : join(ROOT, route.replace(/^\//, ''), 'index.html');
    await mkdir(dirname(out), { recursive: true });
    await writeFile(out, html);
    written++;
  }
  console.log(`[prerender] ${written}/${routes.length} rutas prerenderizadas → ${ROOT}`);
}

try {
  await run();
} catch (e) {
  await fail('error inesperado', e);
}
