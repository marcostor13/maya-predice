import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { ConsentService } from '../../core/services/consent.service';

/** Banner de consentimiento de cookies (RGPD). Se oculta tras decidir. */
@Component({
  selector: 'app-consent-banner',
  standalone: true,
  imports: [RouterLink],
  template: `
    @if (!consent.decided()) {
      <div class="banner">
        <p>
          Usamos cookies propias y de terceros (anuncios) para sostener el proyecto.
          Puedes aceptarlas o rechazarlas. Más info en
          <a routerLink="/privacidad">Privacidad</a>.
        </p>
        <div class="acts">
          <button class="btn ghost" (click)="consent.reject()">Rechazar</button>
          <button class="btn" (click)="consent.accept()">Aceptar</button>
        </div>
      </div>
    }
  `,
  styles: [
    `
      .banner {
        position: fixed; left: 50%; transform: translateX(-50%); bottom: 16px; z-index: 60;
        width: min(720px, calc(100% - 24px)); display: flex; align-items: center; gap: 16px;
        background: var(--surface); border: 1px solid var(--border); border-radius: 14px;
        padding: 14px 18px; box-shadow: 0 12px 40px rgba(0,0,0,.35);
      }
      p { font-size: .85rem; color: var(--muted); flex: 1; margin: 0; }
      a { color: var(--primary); }
      .acts { display: flex; gap: 8px; flex-shrink: 0; }
      .ghost { background: var(--surface-2); border: 1px solid var(--border); color: var(--text); }
      @media (max-width: 560px) { .banner { flex-direction: column; align-items: stretch; } }
    `,
  ],
})
export class ConsentBannerComponent {
  consent = inject(ConsentService);
}
