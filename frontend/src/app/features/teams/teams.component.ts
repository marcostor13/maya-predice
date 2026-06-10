import { Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

import { ApiService } from '../../core/services/api.service';
import { Team } from '../../core/models';
import { FlagComponent } from '../../shared/flag/flag.component';
import { listStagger } from '../../core/util/animations';

@Component({
  selector: 'app-teams',
  standalone: true,
  imports: [CommonModule, RouterLink, FlagComponent],
  animations: [listStagger],
  template: `
    <div class="container page">
      <h1>🌍 Selecciones</h1>
      <p class="muted">Las 48 selecciones del Mundial 2026. Toca una para ver su plantilla y estado.</p>

      @if (loading()) {
        <div class="grid">
          @for (i of skeletons; track i) { <div class="skeleton" style="height:92px"></div> }
        </div>
      } @else {
        @for (g of groups(); track g) {
          <div class="block">
            <h3 class="g">{{ g === '?' ? 'Por asignar' : 'Grupo ' + g }}</h3>
            <div class="grid" @listStagger>
              @for (t of byGroup()[g]; track t.code) {
                <a class="team card" [routerLink]="['/equipos', t.code]">
                  <span class="fl"><app-flag [code]="t.code" /></span>
                  <span class="meta">
                    <span class="nm">{{ t.name }}</span>
                    <span class="conf muted">{{ t.confederation }}</span>
                  </span>
                  <span class="code chip">{{ t.code }}</span>
                </a>
              }
            </div>
          </div>
        }
      }
    </div>
  `,
  styles: [
    `
      .page { padding: 36px 20px; }
      h1 { font-size: 1.9rem; }
      .block { margin-top: 24px; }
      .g { color: var(--muted); text-transform: uppercase; letter-spacing: 1px; font-size: .95rem; margin-bottom: 10px; }
      .grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
      @media (max-width: 900px) { .grid { grid-template-columns: repeat(2, 1fr); } }
      @media (max-width: 520px) { .grid { grid-template-columns: 1fr; } }
      .team { display: flex; align-items: center; gap: 12px; padding: 14px 16px; color: var(--text); transition: transform .2s ease, border-color .2s ease; }
      .team:hover { transform: translateY(-3px); border-color: var(--primary); }
      .fl { font-size: 2.1rem; }
      .meta { display: flex; flex-direction: column; flex: 1; }
      .nm { font-weight: 700; }
      .conf { font-size: .76rem; }
    `,
  ],
})
export class TeamsComponent {
  private api = inject(ApiService);
  loading = signal(true);
  teams = signal<Team[]>([]);
  skeletons = Array.from({ length: 12 }, (_, i) => i);

  byGroup = computed(() => {
    const out: Record<string, Team[]> = {};
    for (const t of this.teams()) (out[t.group ?? '?'] ??= []).push(t);
    for (const k of Object.keys(out)) out[k].sort((a, b) => a.name.localeCompare(b.name));
    return out;
  });
  groups = computed(() => Object.keys(this.byGroup()).sort());

  constructor() {
    this.api.getTeams().subscribe({
      next: (t) => { this.teams.set(t); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }
}
