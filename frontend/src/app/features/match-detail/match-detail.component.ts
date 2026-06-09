import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';

import { ApiService } from '../../core/services/api.service';
import { Prediction } from '../../core/models';

@Component({
  selector: 'app-match-detail',
  standalone: true,
  imports: [CommonModule],
  template: `
    <h1>Predicción del partido #{{ matchId }}</h1>

    @if (prediction(); as p) {
      <div class="grid">
        <div class="card">
          <span class="label">Victoria local</span>
          <span class="value">{{ (p.p_home * 100).toFixed(1) }}%</span>
        </div>
        <div class="card">
          <span class="label">Empate</span>
          <span class="value">{{ (p.p_draw * 100).toFixed(1) }}%</span>
        </div>
        <div class="card">
          <span class="label">Victoria visitante</span>
          <span class="value">{{ (p.p_away * 100).toFixed(1) }}%</span>
        </div>
      </div>

      <p class="muted">
        Goles esperados: {{ p.expected_home_goals.toFixed(2) }} —
        {{ p.expected_away_goals.toFixed(2) }} · modelo {{ p.model_version }}
      </p>

      <h3>Marcadores más probables</h3>
      <ul>
        @for (s of p.scoreline_probs ?? []; track s) {
          <li>{{ s.home }}-{{ s.away }} · {{ (s.prob * 100).toFixed(1) }}%</li>
        }
      </ul>
    } @else {
      <button (click)="run()">Generar predicción</button>
      <p class="muted">{{ message() }}</p>
    }
  `,
  styles: [
    `
      .grid { display: flex; gap: 12px; flex-wrap: wrap; }
      .card {
        background: var(--color-surface);
        border-radius: 8px;
        padding: 16px;
        min-width: 140px;
        display: flex;
        flex-direction: column;
        gap: 6px;
      }
      .label { color: var(--color-muted); font-size: 0.8rem; }
      .value { font-size: 1.5rem; font-weight: 700; color: var(--color-primary); }
      .muted { color: var(--color-muted); }
      button {
        background: var(--color-primary);
        border: none;
        color: #06210f;
        font-weight: 700;
        padding: 10px 16px;
        border-radius: 8px;
        cursor: pointer;
      }
    `,
  ],
})
export class MatchDetailComponent {
  private api = inject(ApiService);
  private route = inject(ActivatedRoute);

  matchId = Number(this.route.snapshot.paramMap.get('id'));
  prediction = signal<Prediction | null>(null);
  message = signal('');

  constructor() {
    this.api.getMatchPrediction(this.matchId).subscribe({
      next: (p) => this.prediction.set(p),
      error: () => this.message.set('Sin predicción todavía. Genera una.'),
    });
  }

  run(): void {
    this.message.set('Generando…');
    this.api.runPrediction(this.matchId).subscribe({
      next: (p) => this.prediction.set(p),
      error: (err) => this.message.set('Error: ' + (err?.error?.detail ?? 'desconocido')),
    });
  }
}
