# SEO.md — SEO, indexación y agente de crecimiento

Dominio público de producción: **https://mayapredice.site**

## 1. SEO on-page (ya implementado, Fase A)

- **`frontend/src/index.html`**: `<title>`, meta `description`, `canonical`,
  Open Graph, Twitter Card, `theme-color`, `robots`, y JSON-LD (`WebSite` +
  `SportsEvent` Mundial 2026). Incluye un hueco comentado para el meta de
  verificación de Google Search Console.
- **`SeoService`** (`core/services/seo.service.ts`) + `data.seo` por ruta en
  `app.routes.ts`: cada página fija su propio título/description/canonical/OG
  (lo aplica un listener de router en `AppComponent`).
- **`robots.txt`** (`src/static/robots.txt`): `Allow: /`, `Disallow: /admin`,
  y `Sitemap: https://mayapredice.site/sitemap.xml`.
- **`sitemap.xml`**: se genera en cada build (`scripts/gen-sitemap.mjs`, lo
  ejecuta `npm run build`). Incluye las rutas estáticas y una entrada por cada
  selección (`/equipos/:code`) leída de la API pública; si la API no responde,
  cae a solo las rutas estáticas (no rompe el build).

> **Nota CSR.** El sitio es SPA (client-side). Googlebot renderiza el JS, así que
> ve los títulos/description por ruta. El **prerender/SSG** (HTML estático para
> todos los crawlers y previews sociales por página) quedó como follow-up.

## 2. Google Analytics 4

- ID: `G-8KRF0P5NZJ`, en el `<head>` de `index.html` con **Consent Mode v2**:
  denegado por defecto, concedido cuando el usuario acepta cookies (el
  `ConsentService` propaga el consentimiento a `gtag`). Mismo patrón que AdSense.

## 3. Agente de crecimiento (cron cada 2 h) — backend, **apagado por defecto**

`backend/app/services/growth/`. Cada ciclo (`run_growth_cycle`):

1. Reúne contexto del sitio + el **historial de ideas previas** (itera y evita
   repetir — "se entrena" acumulando aprendizaje).
2. Pide a **DeepSeek** ideas de SEO / promoción / contenido / monetización (JSON).
3. Las persiste de forma auditable (`growth_runs` / `growth_insights`).
4. Ejecuta **acciones automáticas seguras** (ping IndexNow a Bing/Yandex).
5. Envía un **email-digest** al dueño con: ideas nuevas, contenido listo para
   publicar, acciones hechas, propuestas de **monetización pendientes de tu OK**
   y la configuración que falte.

**Reglas de seguridad:**
- Las ideas de **monetización** SIEMPRE requieren tu aprobación; no se ejecutan
  solas (van al email).
- Si falta `DEEPSEEK_API_KEY`, el ciclo no rompe nada: te avisa por email.
- Corre vía `start_job` (un trabajo a la vez, lock advisory de Postgres).

Disparo: scheduler (`GROWTH_AGENT_ENABLED` + `GROWTH_AGENT_MINUTES`=120) o cron
externo `python -m app.data.grow`. Panel: endpoints `/admin/growth*`.

## 4. Checklist de configuración (acción del usuario)

### Coolify (backend) — variables de entorno
| Variable | Valor | Para qué |
|---|---|---|
| `DEEPSEEK_API_KEY` | (tu key; **rótala**, viajó por chat) | Agente de crecimiento |
| `GROWTH_AGENT_ENABLED` | `true` | Activa el cron cada 2 h |
| `GROWTH_AGENT_MINUTES` | `120` | Frecuencia |
| `GROWTH_REPORT_EMAIL` | `marcostor13@gmail.com` | Destinatario del digest |
| `PUBLIC_SITE_URL` | `https://mayapredice.site` | Contexto + IndexNow |
| `INDEXNOW_KEY` | (genera una cadena hex) | Ping a Bing/Yandex |
| `SMTP_HOST/PORT/USER/PASSWORD/FROM` | (tu SMTP) | Envío de emails |
| `NOTIFICATIONS_ENABLED` | `true` | Habilita emails |
| `CORS_ORIGINS` | `https://mayapredice.site` | El frontend nuevo |
| `SITE_URL` | `https://mayapredice.site` | Enlaces en emails |

> Casi todo es editable también desde el panel ⚙️ Configuración → grupo "Crecimiento".

### Allowlist de red (Coolify)
- `api.deepseek.com`
- `api.indexnow.org`
- (ya en uso para plantillas: `en.wikipedia.org`, etc.)

### IndexNow
- Crea un fichero `<INDEXNOW_KEY>.txt` en la raíz del frontend con la propia key
  como contenido, y súbelo (Netlify). Necesario para que IndexNow valide.

### Netlify (frontend)
- Apuntar el dominio **mayapredice.site** al sitio.
- Subir **`frontend/src/assets/og-cover.png`** (1200×630) para las previews
  sociales (hoy las metas OG apuntan a esa ruta).

### Google Search Console
1. Añadir la propiedad `https://mayapredice.site` y **verificar** (DNS TXT o el
   meta `google-site-verification` que ya tiene hueco en `index.html`).
2. **Enviar el sitemap**: `https://mayapredice.site/sitemap.xml`.

## 5. Prerender por ruta (HTML estático indexable)

`scripts/prerender.mjs` corre tras `ng build` (y `gen-sitemap`): levanta un servidor
estático del `dist`, lanza **Chromium headless (Playwright)** y renderiza cada ruta
(las estáticas + las 48 selecciones `/equipos/:code`), guardando el HTML resultante
—con `title`/meta/canonical/JSON-LD ya aplicados por `SeoService` y el contenido
visible— como `…/<ruta>/index.html`. Así **todos** los crawlers y los unfurlers
sociales (que no ejecutan JS) ven HTML real por página; el SPA hidrata encima para el
usuario. Netlify sirve el estático prerenderizado y cae al `index.html` (CSR) para las
rutas sin prerender.

**Es no-fatal:** si no hay Chromium disponible, el script se omite y el sitio queda en
CSR (sin regresión). En Netlify, `netlify.toml` baja chromium con
`npx playwright install chromium || true` y `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1` evita
descargar los 3 navegadores en `npm install`. Las páginas prerenderizan con los datos
de la API **al momento del build**; el cliente los refresca en vivo.

Además: `index.html` lleva contenido crawleable dentro de `<app-root>` + `<noscript>`,
y hay JSON-LD por página (Organization, BreadcrumbList, SportsTeam, ItemList).
