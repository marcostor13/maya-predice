import { CommonModule } from '@angular/common';
import { Component, DestroyRef, Input, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { catchError, forkJoin, of, switchMap, timer } from 'rxjs';

import { LiveMatch, Prediction } from '../../core/models';
import { ApiService } from '../../core/services/api.service';
import { FlagComponent } from '../flag/flag.component';

/**
 * Marcador en vivo: se auto-refresca cada 2 minutos consultando `/matches/live`
 * (y las predicciones del modelo para cada partido). Si no hay partidos en vivo
 * no renderiza nada (apto para incrustar en el home). El polling se limpia solo
 * al destruir el componente (`takeUntilDestroyed`).
 */
@Component({
  selector: 'app-live-scoreboard',
  standalone: true,
  imports: [CommonModule, RouterLink, FlagComponent],
  template: `
    @if (matches().length) {
      <section class="live-board">
        @if (title) {
          <h2 class="board-title">{{ title }}</h2>
        }
        <div class="live-grid">
          @for (m of matches(); track m.id) {
            <a class="live-match card" [routerLink]="link">
              <div class="badge">
                <span class="dot"></span> EN VIVO
                <span class="min">{{ minuteLabel(m) }}</span>
              </div>
              <div class="row">
                <div class="team">
                  <span class="flag"><app-flag [code]="codeOf(m.home_code)" /></span>
                  <span class="tname">{{ nameOf(m.home_name, m.home_code, m.home_placeholder) }}</span>
                </div>
                <div class="score">
                  <span class="g">{{ goal(m.home_goals) }}</span>
                  <span class="sep">-</span>
                  <span class="g">{{ goal(m.away_goals) }}</span>
                </div>
                <div class="team right">
                  <span class="tname">{{ nameOf(m.away_name, m.away_code, m.away_placeholder) }}</span>
                  <span class="flag"><app-flag [code]="codeOf(m.away_code)" /></span>
                </div>
              </div>
              @if (predOf(m); as p) {
                <div class="pred">
                  <div class="pred-head muted">Predicción del modelo (1·X·2)</div>
                  <div class="bars" title="Local / Empate / Visitante">
                    <span class="b home" [style.flex]="p.p_home"></span>
                    <span class="b draw" [style.flex]="p.p_draw"></span>
                    <span class="b away" [style.flex]="p.p_away"></span>
                  </div>
                  <div class="pcts">
                    <span [class.fav]="favors(p) === 'home'">{{ pct(p.p_home) }}%</span>
                    <span class="draw" [class.fav]="favors(p) === 'draw'">{{ pct(p.p_draw) }}%</span>
                    <span [class.fav]="favors(p) === 'away'">{{ pct(p.p_away) }}%</span>
                  </div>
                </div>
              }
              @if (m.stage || m.group || m.venue) {
                <div class="meta">{{ metaLabel(m) }}</div>
              }
            </a>
          }
        </div>
      </section>
    }
  `,
  styles: [
    `
      .live-board { margin-top: 24px; }
      .board-title { font-size: 1.3rem; margin-bottom: 14px; }
      .live-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
      @media (max-width: 720px) { .live-grid { grid-template-columns: 1fr; } }

      .live-match {
        display: flex; flex-direction: column; gap: 12px; padding: 18px;
        color: var(--text); text-decoration: none;
        border: 1px solid rgba(239, 68, 68, 0.4);
        transition: transform 0.2s ease, border-color 0.2s ease;
        animation: breathe 2.6s ease-in-out infinite;
      }
      .live-match:hover { transform: translateY(-3px); border-color: rgba(239, 68, 68, 0.85); }

      .badge {
        display: inline-flex; align-items: center; gap: 7px; align-self: flex-start;
        background: rgba(239, 68, 68, 0.15); color: #fca5a5;
        font-family: 'Poppins'; font-weight: 700; font-size: 0.72rem; letter-spacing: 0.04em;
        padding: 4px 12px; border-radius: 999px; border: 1px solid rgba(239, 68, 68, 0.35);
      }
      .dot {
        width: 8px; height: 8px; border-radius: 50%; background: #ef4444;
        box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);
        animation: pulse 1.4s ease-out infinite;
      }
      .badge .min { color: #fecaca; margin-left: 2px; }

      .row { display: flex; align-items: center; gap: 10px; }
      .team { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0; }
      .team.right { justify-content: flex-end; }
      .team .flag { font-size: 1.9rem; flex: none; }
      .tname { font-family: 'Poppins'; font-weight: 700; font-size: 0.95rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

      .score {
        display: flex; align-items: center; gap: 8px; flex: none;
        font-family: 'Poppins'; font-weight: 800; font-size: 1.9rem; line-height: 1;
      }
      .score .sep { color: var(--muted); font-weight: 600; }
      .score .g {
        min-width: 1.2ch; text-align: center;
        background: linear-gradient(120deg, var(--primary), var(--accent));
        -webkit-background-clip: text; background-clip: text; color: transparent;
      }

      .pred { display: flex; flex-direction: column; gap: 6px; }
      .pred-head { font-size: 0.68rem; letter-spacing: 0.03em; text-transform: uppercase; }
      .bars { display: flex; height: 8px; border-radius: 999px; overflow: hidden; gap: 2px; }
      .b { display: block; min-width: 2px; border-radius: 999px; }
      .b.home { background: var(--primary); }
      .b.draw { background: var(--muted); }
      .b.away { background: var(--accent); }
      .pcts { display: flex; justify-content: space-between; font-size: 0.74rem; color: var(--muted); }
      .pcts .fav { color: var(--text); font-weight: 700; }

      .meta { font-size: 0.74rem; color: var(--muted); text-align: center; }

      @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.6); }
        70% { box-shadow: 0 0 0 8px rgba(239, 68, 68, 0); }
        100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
      }
      @keyframes breathe {
        0%, 100% { border-color: rgba(239, 68, 68, 0.35); }
        50% { border-color: rgba(239, 68, 68, 0.7); }
      }

      @media (max-width: 480px) {
        .team .flag { font-size: 1.5rem; }
        .tname { font-size: 0.85rem; }
        .score { font-size: 1.6rem; }
      }
    `,
  ],
})
export class LiveScoreboardComponent {
  /** Encabezado opcional, p. ej. "🔴 En vivo ahora". */
  @Input() title?: string;
  /** Ruta a la que enlaza cada tarjeta. */
  @Input() link = '/en-vivo';

  private api = inject(ApiService);
  private destroyRef = inject(DestroyRef);

  matches = signal<LiveMatch[]>([]);
  private predsById = signal<Map<number, Prediction>>(new Map());

  constructor() {
    timer(0, 120_000)
      .pipe(
        switchMap(() =>
          forkJoin({
            live: this.api.getLiveMatches().pipe(catchError(() => of<LiveMatch[]>([]))),
            preds: this.api.getPredictions().pipe(catchError(() => of<Prediction[]>([]))),
          }),
        ),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe(({ live, preds }) => {
        this.matches.set(live);
        this.predsById.set(new Map(preds.map((p) => [p.match_id, p])));
      });
  }

  predOf(m: LiveMatch): Prediction | undefined {
    return this.predsById().get(m.id);
  }

  /** Resultado más probable según el modelo. */
  favors(p: Prediction): 'home' | 'draw' | 'away' {
    const max = Math.max(p.p_home, p.p_draw, p.p_away);
    return max === p.p_home ? 'home' : max === p.p_away ? 'away' : 'draw';
  }

  pct(value: number): string {
    return (value * 100).toFixed(0);
  }

  codeOf(code?: string | null): string | undefined {
    return code ?? undefined;
  }

  nameOf(name?: string | null, code?: string | null, placeholder?: string | null): string {
    return name || code || placeholder || 'Por confirmar';
  }

  goal(value?: number | null): number {
    return value ?? 0;
  }

  minuteLabel(m: LiveMatch): string {
    if (m.minute != null) return `${m.minute}'`;
    // Sin minuto pero en vivo → típicamente el descanso (HT).
    return 'Descanso';
  }

  metaLabel(m: LiveMatch): string {
    const parts: string[] = [];
    if (m.group) parts.push(`Grupo ${m.group}`);
    else if (m.stage) parts.push(m.stage);
    if (m.venue) parts.push(m.venue);
    return parts.join(' · ');
  }
}
