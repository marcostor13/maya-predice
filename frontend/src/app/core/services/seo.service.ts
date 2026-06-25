import { Injectable, inject } from '@angular/core';
import { Meta, Title } from '@angular/platform-browser';
import { DOCUMENT } from '@angular/common';

const SITE = 'https://mayapredice.site';
const SUFFIX = ' · maya-predice';
const DEFAULT_IMAGE = `${SITE}/assets/og-cover.png`;

export interface SeoData {
  title: string;
  description: string;
  /** Ruta absoluta sin dominio (p. ej. "/fixture"). */
  path?: string;
  /** Imagen absoluta para OG/Twitter. Por defecto la og-cover del sitio. */
  image?: string;
  /** og:type (por defecto "website"). */
  type?: string;
}

/**
 * Centraliza título, meta description y canonical/Open Graph por ruta. Como la
 * app es SPA, actualiza las etiquetas en cada navegación para que cada página
 * tenga su propio SEO (lo que Googlebot ve al renderizar y lo que se prerenderiza).
 */
@Injectable({ providedIn: 'root' })
export class SeoService {
  private title = inject(Title);
  private meta = inject(Meta);
  private doc = inject(DOCUMENT);

  update(data: SeoData): void {
    const fullTitle = data.title.includes('maya-predice') ? data.title : data.title + SUFFIX;
    const url = SITE + (data.path ?? '/');
    const image = data.image ?? DEFAULT_IMAGE;
    const type = data.type ?? 'website';

    this.title.setTitle(fullTitle);
    this.meta.updateTag({ name: 'description', content: data.description });
    this.meta.updateTag({ property: 'og:type', content: type });
    this.meta.updateTag({ property: 'og:title', content: fullTitle });
    this.meta.updateTag({ property: 'og:description', content: data.description });
    this.meta.updateTag({ property: 'og:url', content: url });
    this.meta.updateTag({ property: 'og:image', content: image });
    this.meta.updateTag({ name: 'twitter:title', content: fullTitle });
    this.meta.updateTag({ name: 'twitter:description', content: data.description });
    this.meta.updateTag({ name: 'twitter:image', content: image });
    this.setCanonical(url);
  }

  private setCanonical(url: string): void {
    let link = this.doc.head.querySelector<HTMLLinkElement>('link[rel="canonical"]');
    if (!link) {
      link = this.doc.createElement('link');
      link.setAttribute('rel', 'canonical');
      this.doc.head.appendChild(link);
    }
    link.setAttribute('href', url);
  }

  /**
   * Inserta o actualiza un bloque JSON-LD identificado por `id` en el <head>.
   * SSR/standalone-safe: usa el DOCUMENT inyectado, no el `document` global.
   */
  setJsonLd(id: string, data: object): void {
    let script = this.doc.head.querySelector<HTMLScriptElement>(
      `script[type="application/ld+json"]#${id}`,
    );
    if (!script) {
      script = this.doc.createElement('script');
      script.setAttribute('type', 'application/ld+json');
      script.setAttribute('id', id);
      this.doc.head.appendChild(script);
    }
    script.textContent = JSON.stringify(data);
  }

  /** Datos estructurados de migas de pan (BreadcrumbList) para la página actual. */
  breadcrumb(items: { name: string; path: string }[]): void {
    this.setJsonLd('bc-jsonld', {
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      itemListElement: items.map((it, i) => ({
        '@type': 'ListItem',
        position: i + 1,
        name: it.name,
        item: SITE + it.path,
      })),
    });
  }
}
