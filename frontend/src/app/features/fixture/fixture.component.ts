import { Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { forkJoin } from 'rxjs';

import { ApiService } from '../../core/services/api.service';
import { Match, MatchStage, Prediction, Team } from '../../core/models';
import { flag } from '../../core/util/flags';
import { listStagger } from '../../core/util/animations';

const STAGE_LABEL: Record<MatchStage, string> = {
  group: 'Fase de grupos',
  round_of_32: 'Dieciseisavos',
  round_of_16: 'Octavos',
  quarter_final: 'Cuartos',
  semi_final: 'Semifinales',
  third_place: 'Tercer puesto',
  final: 'Final',
};

@Component({
  selector: 'app-fixture',
  standalone: true,
  imports: [CommonModule],
  animations: [listStagger],
  template: `
    <div class="container page">
      <h1>📅 Fixture del Mundial 2026</h1>
      <p class="muted">104 partidos · horarios en tu zona local · resultados y pronósticos.</p>

      <div class="filters">
        <button class="chip f" [class.on]="stage() === ''" (click)="stage.set('')">Todos</button>
        @for (s of stages; track s.key) {
          <button class="chip f" [class.on]="stage() === s.key" (click)="stage.set(s.key)">{{ s.label }}</button>
        }
      </div>

      @if (loading()) {
        @for (i of [1,2,3,4,5,6]; track i) { <div class="skeleton" style="height:70px;margin-bottom:10px"></div> }
      } @else {
        @for (g of groupedKeys(); track g) {
          <div class="group-block">
            <h3 class="g-title">{{ groupTitle(g) }}</h3>
            <div class="list" @listStagger>
              @for (m of grouped()[g]; track m.id) {
                <div class="match card" [class.done]="m.status === 'finished'">
                  <div class="dt">
                    <div class="day">{{ day(m.kickoff) }}</div>
                    <div class="time muted">{{ time(m.kickoff) }}</div>
                  </div>
                  <div class="teams">
                    <div class="t">
                      <span class="fl">{{ flag(code(m.home_team_id)) }}</span>
                      <span class="nm">{{ name(m.home_team_id) || m.home_placeholder }}</span>
                    </div>
                    <div class="result">
                      @if (m.status === 'finished') {
                        <span class="score">{{ m.home_goals }} - {{ m.away_goals }}</span>
                      } @else {
                        @if (pred(m.id); as p) {
                          <div class="mini-bars">
                            <span class="b home" [style.flex]="p.p_home"></span>
                            <span class="b draw" [style.flex]="p.p_draw"></span>
                            <span class="b away" [style.flex]="p.p_away"></span>
                          </div>
                        } @else { <span class="vs muted">vs</span> }
                      }
                    </div>
                    <div class="t right">
                      <span class="nm">{{ name(m.away_team_id) || m.away_placeholder }}</span>
                      <span class="fl">{{ flag(code(m.away_team_id)) }}</span>
                    </div>
                  </div>
                  <div class="venue muted">📍 {{ m.venue || '—' }}</div>
                </div>
              }
            </div>
          </div>
        }
      }
    </div>
  `,
  styles: [
    `
      .page { padding: 36px 20px 20px; }
      h1 { font-size: 1.9rem; }
      .filters { display: flex; gap: 8px; flex-wrap: wrap; margin: 22px 0; }
      .chip.f { cursor: pointer; background: var(--surface); color: var(--muted); border: 1px solid var(--border); padding: 8px 14px; transition: all .2s ease; }
      .chip.f:hover { color: var(--text); }
      .chip.f.on { background: linear-gradient(135deg, var(--primary), var(--primary-2)); color: #04241d; border-color: transparent; font-weight: 700; }
      .group-block { margin-bottom: 26px; }
      .g-title { font-size: 1rem; color: var(--muted); margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1px; }
      .list { display: flex; flex-direction: column; gap: 9px; }
      .match { display: grid; grid-template-columns: 76px 1fr 160px; align-items: center; padding: 12px 16px; gap: 14px; transition: border-color .2s ease, transform .2s ease; }
      .match:hover { border-color: var(--primary); transform: translateX(3px); }
      .match.done { opacity: .92; }
      .dt { text-align: center; }
      .day { font-family: 'Poppins'; font-weight: 700; font-size: .92rem; }
      .time { font-size: .78rem; }
      .teams { display: grid; grid-template-columns: 1fr 86px 1fr; align-items: center; gap: 8px; }
      .t { display: flex; align-items: center; gap: 9px; }
      .t.right { justify-content: flex-end; }
      .fl { font-size: 1.6rem; }
      .nm { font-weight: 600; }
      .result { text-align: center; }
      .score { font-family: 'Poppins'; font-weight: 800; font-size: 1.15rem; color: var(--primary); }
      .mini-bars { display: flex; height: 7px; border-radius: 999px; overflow: hidden; gap: 2px; }
      .b { min-width: 2px; border-radius: 999px; } .b.home { background: var(--primary); } .b.draw { background: var(--muted); } .b.away { background: var(--accent); }
      .venue { font-size: .78rem; text-align: right; }
      @media (max-width: 720px) {
        .match { grid-template-columns: 60px 1fr; }
        .venue { display: none; }
        .nm { font-size: .85rem; }
      }
    `,
  ],
})
export class FixtureComponent {
  private api = inject(ApiService);
  flag = flag;
  stages = (Object.keys(STAGE_LABEL) as MatchStage[]).map((key) => ({ key, label: STAGE_LABEL[key] }));

  teams = signal<Team[]>([]);
  matches = signal<Match[]>([]);
  predictions = signal<Prediction[]>([]);
  loading = signal(true);
  stage = signal<MatchStage | ''>('');

  private teamById = computed(() => new Map(this.teams().map((t) => [t.id, t])));
  private predByMatch = computed(() => new Map(this.predictions().map((p) => [p.match_id, p])));

  private filtered = computed(() =>
    this.matches().filter((m) => !this.stage() || m.stage === this.stage()),
  );

  grouped = computed(() => {
    const out: Record<string, Match[]> = {};
    for (const m of this.filtered()) {
      const key = m.stage === 'group' ? `group:${m.group ?? '?'}` : `stage:${m.stage}`;
      (out[key] ??= []).push(m);
    }
    for (const k of Object.keys(out)) {
      out[k].sort((a, b) => (a.kickoff ?? '').localeCompare(b.kickoff ?? ''));
    }
    return out;
  });
  groupedKeys = computed(() => Object.keys(this.grouped()).sort());

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
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  groupTitle(key: string): string {
    if (key.startsWith('group:')) return 'Grupo ' + key.split(':')[1];
    return STAGE_LABEL[key.split(':')[1] as MatchStage] ?? key;
  }
  code(id?: number) { return id ? this.teamById().get(id)?.code : undefined; }
  name(id?: number) { return id ? this.teamById().get(id)?.name : undefined; }
  pred(id: number) { return this.predByMatch().get(id); }
  day(iso?: string) { return iso ? new Date(iso).toLocaleDateString('es', { day: '2-digit', month: 'short' }) : '—'; }
  time(iso?: string) { return iso ? new Date(iso).toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' }) : ''; }
}
