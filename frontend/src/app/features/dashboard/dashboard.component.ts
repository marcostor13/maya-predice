import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

import { ApiService } from '../../core/services/api.service';
import { Match } from '../../core/models';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <h1>Partidos y predicciones</h1>
    <p class="muted">Predicciones del Mundial 2026 generadas con el modelo Dixon-Coles.</p>

    @if (loading()) {
      <p>Cargando partidos…</p>
    } @else if (matches().length === 0) {
      <p class="muted">Aún no hay partidos cargados. Ejecuta el seed del backend.</p>
    } @else {
      <ul class="match-list">
        @for (m of matches(); track m.id) {
          <li>
            <a [routerLink]="['/match', m.id]">
              Partido #{{ m.id }} · {{ m.stage }} {{ m.group ? '· Grupo ' + m.group : '' }}
            </a>
          </li>
        }
      </ul>
    }
  `,
  styles: [
    `
      h1 { margin-top: 0; }
      .muted { color: var(--color-muted); }
      .match-list { list-style: none; padding: 0; }
      .match-list li {
        background: var(--color-surface);
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 8px;
      }
    `,
  ],
})
export class DashboardComponent {
  private api = inject(ApiService);
  matches = signal<Match[]>([]);
  loading = signal(true);

  constructor() {
    this.api.getMatches().subscribe({
      next: (data) => {
        this.matches.set(data);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }
}
