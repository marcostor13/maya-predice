import { Component, Input, computed, effect, inject } from '@angular/core';

import { environment } from '../../../environments/environment';
import { ConsentService } from '../../core/services/consent.service';

// El script de AdSense se inyecta una sola vez en toda la app.
let scriptInjected = false;

/**
 * Bloque de anuncio de Google AdSense. No renderiza nada si no hay
 * `adsenseClient` configurado o si el usuario no aceptó cookies, de modo que en
 * desarrollo (y hasta tener cuenta aprobada) el sitio queda igual que ahora.
 */
@Component({
  selector: 'app-ad-slot',
  standalone: true,
  template: `
    @if (visible()) {
      <ins class="adsbygoogle" style="display:block"
           [attr.data-ad-client]="client"
           [attr.data-ad-slot]="slot"
           data-ad-format="auto"
           data-full-width-responsive="true"></ins>
    }
  `,
  styles: [`:host { display: block; margin: 18px 0; } ins { display: block; }`],
})
export class AdSlotComponent {
  /** Id del slot creado en el panel de AdSense (opcional para auto-ads). */
  @Input() slot = '';
  private consent = inject(ConsentService);
  client = (environment as { adsenseClient?: string }).adsenseClient ?? '';

  visible = computed(() => !!this.client && this.consent.accepted());
  private pushed = false;

  constructor() {
    effect(() => {
      if (this.visible() && !this.pushed) {
        this.pushed = true;
        this.injectScript();
        // Espera a que Angular pinte el <ins> antes de pedir el anuncio.
        setTimeout(() => {
          try {
            const w = window as unknown as { adsbygoogle?: unknown[] };
            (w.adsbygoogle = w.adsbygoogle || []).push({});
          } catch {
            /* el bloqueador de anuncios o la falta de red: se ignora */
          }
        }, 0);
      }
    });
  }

  private injectScript(): void {
    if (scriptInjected) return;
    scriptInjected = true;
    // El loader ya puede venir en el <head> (index.html) para la verificación
    // del sitio y Auto ads; en ese caso no lo duplicamos.
    if (document.querySelector('script[src*="adsbygoogle.js"]')) return;
    const s = document.createElement('script');
    s.async = true;
    s.src =
      'https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=' + this.client;
    s.crossOrigin = 'anonymous';
    document.head.appendChild(s);
  }
}
