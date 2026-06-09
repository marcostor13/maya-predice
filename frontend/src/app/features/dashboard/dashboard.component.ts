import { Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';

import { ApiService } from '../../core/services/api.service';
import { Match, Prediction, Team, TeamSimulation } from '../../core/models';
import { flag } from '../../core/util/flags';
import { fadeIn, listStagger } from '../../core/util/animations';
import { SubscribeComponent } from '../../shared/subscribe/subscribe.component';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink, SubscribeComponent],
  animations: [fadeIn, listStagger],
  template: `
    <!-- HERO -->
    <section class="hero">
      <div class="container hero-inner">
        <div class="orb a"></div>
        <div class="orb b"></div>
        <div class="copy fade-up">
          <span class="chip">⚽ Copa Mundial FIFA 2026 · 48 selecciones</span>
          <h1>Predicciones del <span class="grad">Mundial 2026</span></h1>
          <p class="muted lead">
            Un modelo estadístico Dixon-Coles entrenado con miles de partidos reales
            predice cada resultado, simula el torneo y se actualiza solo tras cada jornada.
          </p>
          <div class="cta">
            <a routerLink="/fixture" class="btn">Ver fixture &nbsp;→</a>
            <a routerLink="/simulacion" class="btn ghost">Simular torneo 🎲</a>
          </div>
        </div>
        <div class="trophy floaty">🏆</div>
      </div>
    </section>

    <div class="container">
      <!-- STATS -->
      <section class="stats" @listStagger>
        @for (s of stats(); track s.label) {
          <div class="stat card">
            <div class="num grad">{{ s.value }}</div>
            <div class="muted">{{ s.label }}</div>
          </div>
        }
      </section>

      <!-- CONTENDIENTES -->
      <section class="block">
        <div class="head">
          <h2>🔥 Favoritos al título</h2>
          <a routerLink="/simulacion" class="chip">Ver simulación completa →</a>
        </div>
        @if (loadingSim()) {
          <div class="grid-contenders">
            @for (i of [1,2,3,4,5,6]; track i) { <div class="skeleton" style="height:96px"></div> }
          </div>
        } @else if (contenders().length) {
          <div class="grid-contenders" @listStagger>
            @for (t of contenders(); track t.team_code; let i = $index) {
              <a class="contender card" [routerLink]="['/equipos', t.team_code]">
                <div class="rank">#{{ i + 1 }}</div>
                <div class="flag">{{ flag(t.team_code) }}</div>
                <div class="info">
                  <div class="tname">{{ t.team_name }}</div>
                  <div class="prob-track"><div class="prob-fill" [style.width.%]="t.champion_prob * 100"></div></div>
                </div>
                <div class="pct grad">{{ (t.champion_prob * 100).toFixed(1) }}%</div>
              </a>
            }
          </div>
        } @else {
          <div class="card empty">
            <p class="muted">Preparando las predicciones… vuelve en un momento.</p>
          </div>
        }
      </section>

      <!-- PRÓXIMOS PARTIDOS -->
      <section class="block">
        <div class="head">
          <h2>📅 Próximos partidos</h2>
          <a routerLink="/fixture" class="chip">Fixture completo →</a>
        </div>
        @if (loadingMatches()) {
          <div class="matches">
            @for (i of [1,2,3,4]; track i) { <div class="skeleton" style="height:78px"></div> }
          </div>
        } @else {
          <div class="matches" @listStagger>
            @for (m of upcoming(); track m.id) {
              <div class="match card">
                <div class="side">
                  <span class="flag">{{ flag(teamCode(m.home_team_id)) }}</span>
                  <span class="code">{{ teamCode(m.home_team_id) || m.home_placeholder }}</span>
                </div>
                <div class="center">
                  <div class="when">{{ formatDate(m.kickoff) }}</div>
                  @if (pred(m.id); as p) {
                    <div class="bars" title="Local / Empate / Visitante">
                      <span class="b home" [style.flex]="p.p_home"></span>
                      <span class="b draw" [style.flex]="p.p_draw"></span>
                      <span class="b away" [style.flex]="p.p_away"></span>
                    </div>
                    <div class="odds muted">
                      {{ (p.p_home*100).toFixed(0) }}% · {{ (p.p_draw*100).toFixed(0) }}% · {{ (p.p_away*100).toFixed(0) }}%
                    </div>
                  } @else {
                    <div class="vs">VS</div>
                  }
                </div>
                <div class="side right">
                  <span class="code">{{ teamCode(m.away_team_id) || m.away_placeholder }}</span>
                  <span class="flag">{{ flag(teamCode(m.away_team_id)) }}</span>
                </div>
              </div>
            }
          </div>
        }
      </section>

      <section class="block"><app-subscribe /></section>
    </div>
  `,
  styles: [
    `
      .hero { position: relative; overflow: hidden; padding: 40px 0 20px; }
      .hero-inner { position: relative; display: flex; align-items: center; gap: 20px; min-height: 340px; }
      .orb { position: absolute; border-radius: 50%; filter: blur(40px); opacity: .5; z-index: 0; }
      .orb.a { width: 320px; height: 320px; background: rgba(45,212,191,.4); top: -60px; left: -40px; animation: floaty 8s ease-in-out infinite; }
      .orb.b { width: 280px; height: 280px; background: rgba(167,139,250,.4); bottom: -80px; right: 10%; animation: floaty 10s ease-in-out infinite; }
      .copy { position: relative; z-index: 1; max-width: 640px; }
      h1 { font-size: clamp(2rem, 5vw, 3.4rem); font-weight: 800; line-height: 1.05; margin: 14px 0; }
      .grad { background: linear-gradient(120deg, var(--primary), var(--accent)); -webkit-background-clip: text; background-clip: text; color: transparent; }
      .lead { font-size: 1.05rem; max-width: 560px; }
      .cta { display: flex; gap: 12px; margin-top: 24px; flex-wrap: wrap; }
      .trophy { font-size: 9rem; position: relative; z-index: 1; margin-left: auto; filter: drop-shadow(0 20px 40px rgba(251,191,36,.3)); }
      @media (max-width: 820px) { .trophy { display: none; } }

      .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-top: 10px; }
      .stat { padding: 20px; text-align: center; }
      .stat .num { font-family: 'Poppins'; font-weight: 800; font-size: 1.9rem; }
      @media (max-width: 620px) { .stats { grid-template-columns: repeat(2, 1fr); } }

      .block { margin-top: 44px; }
      .head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
      .head h2 { font-size: 1.4rem; }

      .grid-contenders { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
      @media (max-width: 720px) { .grid-contenders { grid-template-columns: 1fr; } }
      .contender { display: flex; align-items: center; gap: 14px; padding: 16px; color: var(--text); transition: transform .2s ease, border-color .2s ease; }
      .contender:hover { transform: translateY(-3px); border-color: var(--primary); }
      .rank { font-family: 'Poppins'; font-weight: 800; color: var(--muted); width: 28px; }
      .contender .flag { font-size: 2rem; }
      .contender .info { flex: 1; }
      .tname { font-weight: 700; margin-bottom: 8px; }
      .pct { font-family: 'Poppins'; font-weight: 800; font-size: 1.2rem; }

      .matches { display: flex; flex-direction: column; gap: 10px; }
      .match { display: flex; align-items: center; padding: 14px 18px; gap: 12px; }
      .side { display: flex; align-items: center; gap: 10px; flex: 1; }
      .side.right { justify-content: flex-end; }
      .side .flag { font-size: 1.8rem; }
      .side .code { font-family: 'Poppins'; font-weight: 700; }
      .center { width: 180px; text-align: center; }
      .when { font-size: .8rem; color: var(--muted); margin-bottom: 6px; }
      .vs { font-family: 'Poppins'; font-weight: 800; color: var(--muted); }
      .bars { display: flex; height: 8px; border-radius: 999px; overflow: hidden; gap: 2px; }
      .b { display: block; min-width: 2px; border-radius: 999px; }
      .b.home { background: var(--primary); } .b.draw { background: var(--muted); } .b.away { background: var(--accent); }
      .odds { font-size: .72rem; margin-top: 5px; }
      .empty { padding: 30px; text-align: center; display: flex; flex-direction: column; gap: 14px; align-items: center; }
      @media (max-width: 560px) {
        .hero-inner { min-height: auto; padding: 10px 0 20px; }
        .lead { font-size: .95rem; }
        .cta { width: 100%; }
        .cta .btn { flex: 1; justify-content: center; }
        .match { padding: 12px 12px; gap: 8px; }
        .center { width: 120px; }
        .side .flag { font-size: 1.4rem; }
        .side .code { font-size: .85rem; }
        .head h2 { font-size: 1.2rem; }
      }
    `,
  ],
})
export class DashboardComponent {
  private api = inject(ApiService);
  flag = flag;

  teams = signal<Team[]>([]);
  matches = signal<Match[]>([]);
  predictions = signal<Prediction[]>([]);
  sim = signal<TeamSimulation[]>([]);
  loadingMatches = signal(true);
  loadingSim = signal(true);

  private teamById = computed(() => new Map(this.teams().map((t) => [t.id, t])));
  private predByMatch = computed(() => new Map(this.predictions().map((p) => [p.match_id, p])));

  contenders = computed(() => this.sim().slice(0, 6));
  upcoming = computed(() =>
    this.matches()
      .filter((m) => m.status === 'scheduled' && (m.home_team_id || m.home_placeholder))
      .slice(0, 6),
  );

  stats = computed(() => [
    { label: 'Selecciones', value: '48' },
    { label: 'Partidos', value: this.matches().length || '104' },
    { label: 'Grupos', value: '12' },
    { label: 'Sedes', value: '3 países' },
  ]);

  constructor() {
    forkJoin({
      teams: this.api.getTeams(),
      matches: this.api.getMatches(),
      preds: this.api.getPredictions(),
    }).subscribe({
      next: ({ teams, matches, preds }) => {
        this.teams.set(teams);
        this.matches.set(matches);
        this.predictions.set(preds);
        this.loadingMatches.set(false);
      },
      error: () => this.loadingMatches.set(false),
    });

    this.api.getSimulation().subscribe({
      next: (s) => {
        this.sim.set(s.teams);
        this.loadingSim.set(false);
      },
      error: () => this.loadingSim.set(false),
    });
  }

  teamCode(id?: number): string | undefined {
    return id ? this.teamById().get(id)?.code : undefined;
  }
  pred(matchId: number): Prediction | undefined {
    return this.predByMatch().get(matchId);
  }
  formatDate(iso?: string): string {
    if (!iso) return 'Por confirmar';
    const d = new Date(iso);
    return d.toLocaleString('es', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
  }
}
