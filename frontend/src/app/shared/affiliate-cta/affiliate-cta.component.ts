import { Component, inject } from '@angular/core';

import { ConfigService } from '../../core/services/config.service';

/**
 * Llamada a la acción de afiliado (p. ej. casa de apuestas). Solo aparece si el
 * admin lo activó y hay URL. Incluye el aviso +18 / juego responsable y usa
 * `rel="sponsored"` (requisito de Google para enlaces de afiliación).
 */
@Component({
  selector: 'app-affiliate-cta',
  standalone: true,
  template: `
    @if (aff(); as a) {
      @if (a.enabled && a.url) {
        <a class="aff" [href]="a.url" target="_blank" rel="sponsored noopener nofollow">
          <span class="txt">📊 Compara las cuotas en <b>{{ a.label || 'la casa recomendada' }}</b></span>
          <span class="age">+18 · Juega con responsabilidad</span>
        </a>
      }
    }
  `,
  styles: [
    `
      .aff {
        display: flex; flex-direction: column; gap: 2px; align-items: center; text-align: center;
        margin: 16px 0; padding: 12px 18px; border-radius: 12px;
        background: linear-gradient(135deg, rgba(52,211,153,.16), rgba(56,189,248,.16));
        border: 1px solid var(--border); transition: transform .15s ease, border-color .2s ease;
      }
      .aff:hover { transform: translateY(-2px); border-color: var(--primary); }
      .txt { font-weight: 600; }
      .age { font-size: .68rem; color: var(--muted); }
    `,
  ],
})
export class AffiliateCtaComponent {
  private cfg = inject(ConfigService);
  aff = this.cfg.affiliate;
}
