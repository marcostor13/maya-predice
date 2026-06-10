import { Component, computed, input } from '@angular/core';

import { flagUrl } from '../../core/util/flags';

/**
 * Bandera de una selección por código FIFA, como imagen (funciona en todos los
 * sistemas, a diferencia de los emoji de bandera). Escala con el `font-size` del
 * contenedor (altura = 1em). Si el código es un placeholder, muestra ⚽.
 */
@Component({
  selector: 'app-flag',
  standalone: true,
  template: `
    @if (url(); as u) {
      <img class="flag" [src]="u" [attr.alt]="code()" loading="lazy" />
    } @else {
      <span class="fb">⚽</span>
    }
  `,
  styles: [
    `
      :host { display: inline-flex; align-items: center; line-height: 1; }
      .flag {
        height: 1em; width: 1.5em; object-fit: cover; border-radius: 3px;
        box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.3);
      }
      .fb { font-size: 0.9em; }
    `,
  ],
})
export class FlagComponent {
  code = input<string | undefined>(undefined);
  url = computed(() => flagUrl(this.code()));
}
