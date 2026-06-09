import { Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { ApiService } from '../../core/services/api.service';
import { Player, Position, Squad } from '../../core/models';
import { flag } from '../../core/util/flags';
import { fadeIn, listStagger } from '../../core/util/animations';

const POS_LABEL: Record<Position, string> = {
  GK: 'Porteros', DEF: 'Defensas', MID: 'Mediocampistas', FWD: 'Delanteros', UNKNOWN: 'Otros',
};
const STATUS: Record<string, { t: string; c: string }> = {
  available: { t: 'Disponible', c: 'ok' },
  injured: { t: 'Lesionado', c: 'bad' },
  suspended: { t: 'Sancionado', c: 'bad' },
  doubtful: { t: 'En duda', c: 'warn' },
  out: { t: 'Baja', c: 'bad' },
  unknown: { t: '—', c: 'mut' },
};

@Component({
  selector: 'app-team-detail',
  standalone: true,
  imports: [CommonModule, RouterLink],
  animations: [fadeIn, listStagger],
  template: `
    <div class="container page">
      <a routerLink="/equipos" class="chip back">← Equipos</a>

      @if (loading()) {
        <div class="skeleton" style="height:120px;margin:18px 0"></div>
        <div class="skeleton" style="height:300px"></div>
      } @else if (squad()) {
        @if (squad(); as s) {
        <header class="hero card" @fadeIn>
          <div class="fl floaty">{{ flag(s.team_code) }}</div>
          <div>
            <h1>{{ s.team_name }}</h1>
            <div class="chips">
              <span class="chip">{{ s.team_code }}</span>
              @if (s.coach) { <span class="chip">👔 DT: {{ s.coach.name }}</span> }
              <span class="chip">👥 {{ s.players.length }} jugadores</span>
            </div>
          </div>
        </header>

        @if (s.players.length === 0) {
          <div class="card empty">
            <p class="muted">Plantilla aún no disponible. Se carga del consenso de varias fuentes.</p>
          </div>
        } @else {
          @for (group of positions(); track group.key) {
            <section class="pos-block">
              <h3>{{ group.label }} <span class="muted">({{ group.players.length }})</span></h3>
              <div class="players" @listStagger>
                @for (p of group.players; track p.id) {
                  <div class="player card">
                    <div class="num">{{ p.shirt_number ?? '–' }}</div>
                    <div class="pinfo">
                      <div class="pname">{{ p.full_name }}</div>
                      <div class="club muted">{{ p.club || '—' }}</div>
                    </div>
                    <div class="status" [class]="statusClass(p)">{{ statusText(p) }}</div>
                  </div>
                }
              </div>
            </section>
          }
        }
        }
      } @else {
        <div class="card empty"><p class="muted">No se encontró la selección.</p></div>
      }
    </div>
  `,
  styles: [
    `
      .page { padding: 28px 20px; }
      .back { display: inline-block; margin-bottom: 16px; cursor: pointer; }
      .hero { display: flex; align-items: center; gap: 22px; padding: 26px; margin-bottom: 24px; }
      .hero .fl { font-size: 4.5rem; }
      .hero h1 { font-size: 2rem; margin-bottom: 10px; }
      .chips { display: flex; gap: 8px; flex-wrap: wrap; }
      .pos-block { margin-bottom: 24px; }
      .pos-block h3 { margin-bottom: 12px; font-size: 1.1rem; }
      .players { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
      @media (max-width: 640px) { .players { grid-template-columns: 1fr; } }
      .player { display: flex; align-items: center; gap: 14px; padding: 12px 16px; transition: transform .15s ease, border-color .2s ease; }
      .player:hover { transform: translateX(3px); border-color: var(--primary); }
      .num { width: 34px; height: 34px; display: grid; place-items: center; border-radius: 10px; background: var(--surface-2); font-family: 'Poppins'; font-weight: 700; }
      .pinfo { flex: 1; }
      .pname { font-weight: 600; }
      .club { font-size: .78rem; }
      .status { font-size: .74rem; font-weight: 700; padding: 4px 10px; border-radius: 999px; }
      .status.ok { color: #34d399; background: rgba(52,211,153,.12); }
      .status.bad { color: var(--danger); background: rgba(248,113,113,.12); }
      .status.warn { color: var(--gold); background: rgba(251,191,36,.12); }
      .status.mut { color: var(--muted); background: var(--surface-2); }
      .empty { padding: 30px; text-align: center; }
    `,
  ],
})
export class TeamDetailComponent {
  private api = inject(ApiService);
  private route = inject(ActivatedRoute);
  flag = flag;

  squad = signal<Squad | null>(null);
  loading = signal(true);

  positions = computed(() => {
    const s = this.squad();
    if (!s) return [];
    const order: Position[] = ['GK', 'DEF', 'MID', 'FWD', 'UNKNOWN'];
    return order
      .map((key) => ({
        key,
        label: POS_LABEL[key],
        players: s.players
          .filter((p) => p.position === key)
          .sort((a, b) => (a.shirt_number ?? 99) - (b.shirt_number ?? 99)),
      }))
      .filter((g) => g.players.length > 0);
  });

  constructor() {
    const code = this.route.snapshot.paramMap.get('code') ?? '';
    this.api.getSquad(code).subscribe({
      next: (s) => { this.squad.set(s); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  statusText(p: Player) { return (STATUS[p.status] ?? STATUS['unknown']).t; }
  statusClass(p: Player) { return (STATUS[p.status] ?? STATUS['unknown']).c; }
}
