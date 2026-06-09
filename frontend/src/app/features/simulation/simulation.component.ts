import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

import { ApiService } from '../../core/services/api.service';
import { Simulation, TeamSimulation } from '../../core/models';
import { flag } from '../../core/util/flags';
import { listStagger } from '../../core/util/animations';

@Component({
  selector: 'app-simulation',
  standalone: true,
  imports: [CommonModule, RouterLink],
  animations: [listStagger],
  template: `
    <div class="container page">
      <header class="top">
        <div>
          <h1>🎲 Simulación del torneo</h1>
          <p class="muted">
            Miles de Mundiales simulados con el modelo (Monte Carlo): probabilidad de cada
            selección de avanzar y de levantar la copa.
          </p>
        </div>
        <button class="btn ghost" (click)="refresh()" [disabled]="running()" title="Volver a cargar">
          @if (running()) { <span class="spinner" style="width:18px;height:18px"></span> }
          @else { ↻ Actualizar }
        </button>
      </header>

      @if (sim(); as s) {
        <div class="meta chip">
          {{ s.iterations.toLocaleString('es') }} iteraciones · modelo {{ s.model_version }}
        </div>

        <!-- Podio -->
        <div class="podium">
          @for (t of top3(); track t.team_code; let i = $index) {
            <a class="pod card" [class]="'p' + (i+1)" [routerLink]="['/equipos', t.team_code]">
              <div class="medal">{{ ['🥇','🥈','🥉'][i] }}</div>
              <div class="fl floaty">{{ flag(t.team_code) }}</div>
              <div class="nm">{{ t.team_name }}</div>
              <div class="big grad">{{ (t.champion_prob * 100).toFixed(1) }}%</div>
              <div class="muted lbl">campeón</div>
            </a>
          }
        </div>

        <!-- Ranking completo -->
        <div class="table card">
          <div class="thead">
            <span>#</span><span>Selección</span><span class="r">Pasa grupo</span>
            <span class="r">Semis</span><span class="r">Final</span><span class="r">Campeón</span>
          </div>
          <div @listStagger>
            @for (t of sim()!.teams; track t.team_code; let i = $index) {
              <a class="trow" [routerLink]="['/equipos', t.team_code]">
                <span class="rk">{{ i + 1 }}</span>
                <span class="tm"><span class="fl">{{ flag(t.team_code) }}</span> {{ t.team_name }}</span>
                <span class="r">{{ pct(t.advance_prob) }}</span>
                <span class="r">{{ pct(t.semi_prob) }}</span>
                <span class="r">{{ pct(t.final_prob) }}</span>
                <span class="r champ">
                  <span class="prob-track"><span class="prob-fill" [style.width.%]="t.champion_prob * 100"></span></span>
                  <b>{{ pct(t.champion_prob) }}</b>
                </span>
              </a>
            }
          </div>
        </div>
      } @else if (loading()) {
        <div class="skeleton" style="height:200px;margin-top:20px"></div>
      } @else {
        <div class="card empty">
          <div class="dice floaty">🎲</div>
          <p class="muted">Preparando las predicciones del torneo… vuelve en un momento.</p>
        </div>
      }
    </div>
  `,
  styles: [
    `
      .page { padding: 32px 20px; }
      .top { display: flex; align-items: center; justify-content: space-between; gap: 20px; flex-wrap: wrap; }
      h1 { font-size: 1.9rem; }
      .grad { background: linear-gradient(120deg, var(--primary), var(--accent)); -webkit-background-clip: text; background-clip: text; color: transparent; }
      .meta { display: inline-block; margin: 18px 0; }
      .podium { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 24px; }
      @media (max-width: 680px) { .podium { grid-template-columns: 1fr; } }
      .pod { text-align: center; padding: 22px; color: var(--text); transition: transform .2s ease; position: relative; overflow: hidden; }
      .pod:hover { transform: translateY(-4px); }
      .pod.p1 { animation: glow 3s ease-in-out infinite; border-color: var(--gold); }
      .medal { font-size: 1.8rem; }
      .pod .fl { font-size: 3.4rem; margin: 6px 0; }
      .pod .nm { font-weight: 700; }
      .big { font-family: 'Poppins'; font-weight: 800; font-size: 2rem; margin-top: 6px; }
      .lbl { font-size: .75rem; }
      .table { padding: 8px 8px 12px; }
      .thead, .trow { display: grid; grid-template-columns: 40px 1fr 100px 80px 80px 150px; align-items: center; gap: 8px; padding: 10px 14px; }
      .thead { color: var(--muted); font-size: .78rem; text-transform: uppercase; letter-spacing: .5px; border-bottom: 1px solid var(--border); }
      .trow { color: var(--text); border-radius: 10px; transition: background .15s ease; }
      .trow:hover { background: var(--surface-2); }
      .rk { color: var(--muted); font-family: 'Poppins'; font-weight: 700; }
      .tm { display: flex; align-items: center; gap: 10px; font-weight: 600; }
      .fl { font-size: 1.4rem; }
      .r { text-align: right; font-variant-numeric: tabular-nums; }
      .r.champ { display: flex; align-items: center; gap: 8px; }
      .r.champ .prob-track { flex: 1; }
      .r.champ b { width: 46px; }
      .empty { padding: 50px; text-align: center; margin-top: 20px; }
      .dice { font-size: 4rem; }
      @media (max-width: 680px) {
        .thead, .trow { grid-template-columns: 28px 1fr 70px; }
        .thead .r:nth-child(4), .thead .r:nth-child(5), .trow .r:nth-child(4), .trow .r:nth-child(5) { display: none; }
        .r.champ { display: none; }
      }
    `,
  ],
})
export class SimulationComponent {
  private api = inject(ApiService);
  flag = flag;
  sim = signal<Simulation | null>(null);
  running = signal(false);
  loading = signal(true);

  constructor() {
    this.api.getSimulation().subscribe({
      next: (s) => { this.sim.set(s); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  // Recarga la última simulación ya calculada en el servidor (rápido, sin recomputar).
  refresh(): void {
    this.running.set(true);
    this.api.getSimulation().subscribe({
      next: (s) => { this.sim.set(s); this.running.set(false); },
      error: () => this.running.set(false),
    });
  }

  top3(): TeamSimulation[] { return this.sim()?.teams.slice(0, 3) ?? []; }
  pct(v: number): string { return (v * 100).toFixed(1) + '%'; }
}
