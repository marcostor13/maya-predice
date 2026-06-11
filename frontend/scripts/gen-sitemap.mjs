// Genera sitemap.xml tras el build. Incluye las rutas estáticas y, si la API
// pública responde, una entrada por selección (/equipos/:code). Si la API no
// está disponible, cae a solo las rutas estáticas (no rompe el build).
import { writeFileSync } from 'node:fs';
import { join } from 'node:path';

const SITE = 'https://mayapredice.site';
const API = process.env.SITEMAP_API_URL || 'https://apimayapredice.marcostorresalarcon.com/api/v1';
const OUT = join(process.cwd(), 'dist', 'maya-predice', 'browser', 'sitemap.xml');

const staticRoutes = [
  { loc: '/', priority: '1.0', changefreq: 'hourly' },
  { loc: '/fixture', priority: '0.9', changefreq: 'hourly' },
  { loc: '/equipos', priority: '0.8', changefreq: 'daily' },
  { loc: '/simulacion', priority: '0.9', changefreq: 'hourly' },
  { loc: '/privacidad', priority: '0.3', changefreq: 'yearly' },
];

async function teamRoutes() {
  try {
    const res = await fetch(`${API}/teams`, { signal: AbortSignal.timeout(8000) });
    if (!res.ok) return [];
    const teams = await res.json();
    return (Array.isArray(teams) ? teams : [])
      .map((t) => t.code)
      .filter(Boolean)
      .map((code) => ({ loc: `/equipos/${code}`, priority: '0.6', changefreq: 'daily' }));
  } catch {
    return [];
  }
}

const routes = [...staticRoutes, ...(await teamRoutes())];
const now = new Date().toISOString();
const urls = routes
  .map(
    (r) =>
      `  <url>\n    <loc>${SITE}${r.loc}</loc>\n    <lastmod>${now}</lastmod>\n    <changefreq>${r.changefreq}</changefreq>\n    <priority>${r.priority}</priority>\n  </url>`,
  )
  .join('\n');

const xml = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>\n`;

writeFileSync(OUT, xml);
console.log(`sitemap.xml generado con ${routes.length} URLs → ${OUT}`);
