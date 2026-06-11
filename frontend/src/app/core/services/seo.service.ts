import { Injectable, inject } from '@angular/core';
import { Meta, Title } from '@angular/platform-browser';
import { DOCUMENT } from '@angular/common';

const SITE = 'https://mayapredice.site';
const SUFFIX = ' · maya-predice';

export interface SeoData {
  title: string;
  description: string;
  /** Ruta absoluta sin dominio (p. ej. "/fixture"). */
  path?: string;
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

    this.title.setTitle(fullTitle);
    this.meta.updateTag({ name: 'description', content: data.description });
    this.meta.updateTag({ property: 'og:title', content: fullTitle });
    this.meta.updateTag({ property: 'og:description', content: data.description });
    this.meta.updateTag({ property: 'og:url', content: url });
    this.meta.updateTag({ name: 'twitter:title', content: fullTitle });
    this.meta.updateTag({ name: 'twitter:description', content: data.description });
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
}
