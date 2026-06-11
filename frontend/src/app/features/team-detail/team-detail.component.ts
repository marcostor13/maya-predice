import { Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { ApiService } from '../../core/services/api.service';
import { WikiSquadService } from '../../core/services/wiki-squad.service';
import { Player, Position, Squad } from '../../core/models';
import { FlagComponent } from '../../shared/flag/flag.component';
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
  imports: [CommonModule, RouterLink, FlagComponent],
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
          <div class="fl floaty"><app-flag [code]="s.team_code" /></div>
          <div class="hero-main">
            <h1>{{ s.team_name }}</h1>
            <div class="chips">
              <span class="chip">{{ s.team_code }}</span>
              <span class="chip">👥 {{ s.players.length }} jugadores</span>
              @if (fromWiki()) {
                <span class="chip wiki">Plantilla vía Wikipedia</span>
              }
            </div>
          </div>
          @if (s.coach; as c) {
            <div class="coach">
              @if (c.photo_url) {
                <img class="cphoto" [src]="c.photo_url" [alt]="c.name" loading="lazy" />
              } @else {
                <div class="cphoto ph">👔</div>
              }
              <div class="cmeta"><span class="muted">Seleccionador</span><b>{{ c.name }}</b></div>
            </div>
          }
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
                  <div class="player card" [title]="p.info || ''">
                    @if (p.photo_url) {
                      <img class="avatar" [src]="p.photo_url" [alt]="p.full_name" loading="lazy" />
                    } @else {
                      <div class="avatar ph">{{ initials(p.full_name) }}</div>
                    }
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
      .hero-main { flex: 1; }
      .chips { display: flex; gap: 8px; flex-wrap: wrap; }
      .coach { display: flex; align-items: center; gap: 12px; }
      .coach .cphoto { width: 58px; height: 58px; border-radius: 50%; object-fit: cover; border: 2px solid var(--border); }
      .coach .cphoto.ph { display: grid; place-items: center; font-size: 1.6rem; background: var(--surface-2); }
      .coach .cmeta { display: flex; flex-direction: column; }
      .coach .cmeta span { font-size: .72rem; }
      @media (max-width: 640px) { .coach .cmeta { display: none; } }
      .pos-block { margin-bottom: 24px; }
      .pos-block h3 { margin-bottom: 12px; font-size: 1.1rem; }
      .players { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
      @media (max-width: 640px) { .players { grid-template-columns: 1fr; } }
      .player { display: flex; align-items: center; gap: 14px; padding: 12px 16px; transition: transform .15s ease, border-color .2s ease; }
      .player:hover { transform: translateX(3px); border-color: var(--primary); }
      .avatar { width: 46px; height: 46px; border-radius: 50%; object-fit: cover; background: var(--surface-2); flex-shrink: 0; }
      .avatar.ph { display: grid; place-items: center; font-family: 'Poppins'; font-weight: 700; font-size: .8rem; color: var(--muted); }
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
      .chip.wiki { font-size: .72rem; opacity: .85; }
    `,
  ],
})
export class TeamDetailComponent {
  private api = inject(ApiService);
  private wiki = inject(WikiSquadService);
  private route = inject(ActivatedRoute);

  squad = signal<Squad | null>(null);
  loading = signal(true);
  fromWiki = signal(false);

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
      next: (s) => {
        this.squad.set(s);
        // Si el backend no trae jugadores, intenta Wikipedia (vía proxy de Netlify).
        if (!s?.players?.length && s?.team_name) {
          this.tryWikipedia(s.team_name, s.team_code || code);
        } else {
          this.loading.set(false);
        }
      },
      // Backend 404/caído: recupera el nombre EN por código y prueba Wikipedia.
      error: () => this.fallbackFromTeams(code),
    });
  }

  /** Sin squad del backend: obtiene el nombre en inglés desde /teams y prueba Wikipedia. */
  private fallbackFromTeams(code: string): void {
    this.api.getTeams().subscribe({
      next: (teams) => {
        const team = teams.find((t) => t.code === code);
        if (team?.name) {
          this.tryWikipedia(team.name, code);
        } else {
          this.loading.set(false);
        }
      },
      error: () => this.loading.set(false),
    });
  }

  private tryWikipedia(teamName: string, code: string): void {
    this.wiki.getSquad(teamName, code).subscribe({
      next: (w) => {
        if (w?.players?.length) {
          this.squad.set(w);
          this.fromWiki.set(true);
        }
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  statusText(p: Player) { return (STATUS[p.status] ?? STATUS['unknown']).t; }
  statusClass(p: Player) { return (STATUS[p.status] ?? STATUS['unknown']).c; }

  initials(name: string): string {
    return name.split(' ').filter(Boolean).slice(0, 2).map((w) => w[0]).join('').toUpperCase();
  }
}
