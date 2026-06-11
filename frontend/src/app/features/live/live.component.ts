import { CommonModule } from '@angular/common';
import { Component, DestroyRef, computed, effect, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { catchError, of, switchMap, timer } from 'rxjs';

import { LiveMatch } from '../../core/models';
import { ApiService } from '../../core/services/api.service';
import { SeoService } from '../../core/services/seo.service';
import { fadeIn, listStagger } from '../../core/util/animations';
import { FlagComponent } from '../../shared/flag/flag.component';
import { LiveScoreboardComponent } from '../../shared/live-scoreboard/live-scoreboard.component';

const DEFAULT_SEO = {
  title: 'Resultados en vivo del Mundial 2026 · Marcadores en directo',
  description:
    'Sigue los partidos del Mundial 2026 EN VIVO: marcador en directo minuto a minuto, resultados de hoy y predicciones del modelo. Se actualiza solo cada 2 minutos.',
  path: '/en-vivo',
};

/**
 * Página /en-vivo: resultados en directo del Mundial 2026. Hace su propio polling
 * (cada 2 min) para decidir el mensaje de "no hay partidos" y para actualizar el
 * título del documento de forma reactiva cuando hay un partido en curso.
 */
@Component({
  selector: 'app-live',
  standalone: true,
  imports: [CommonModule, FlagComponent, LiveScoreboardComponent],
  animations: [fadeIn, listStagger],
  template: `
    <div class="container">
      <header class="intro fade-up">
        <span class="chip">🔴 Directo · Copa Mundial FIFA 2026</span>
        <h1>Resultados <span class="grad">en vivo</span> del Mundial 2026</h1>
        <p class="muted lead">
          Marcadores en directo minuto a minuto: sigue todos los partidos del Mundial 2026
          en vivo, con resultados actualizados al instante y las predicciones del modelo
          estadístico. La página se refresca sola cada 2 minutos, sin recargar.
        </p>
      </header>

      @if (live().length) {
        <app-live-scoreboard link="/fixture" />
      } @else {
        <div class="card empty fade-up">
          <p class="muted">
            No hay partidos en vivo ahora mismo. Estos son los partidos de hoy:
          </p>
        </div>
      }

      <section class="block">
        <h2>📅 Partidos de hoy</h2>
        @if (loadingToday()) {
          <div class="today">
            @for (i of [1, 2, 3]; track i) { <div class="skeleton" style="height:70px"></div> }
          </div>
        } @else if (today().length) {
          <div class="today" @listStagger>
            @for (m of today(); track m.id) {
              <div class="match card" [class.is-live]="m.status === 'live'">
                <div class="side">
                  <span class="flag"><app-flag [code]="m.home_code ?? undefined" /></span>
                  <span class="code">{{ teamLabel(m.home_name, m.home_code, m.home_placeholder) }}</span>
                </div>
                <div class="center">
                  @if (m.status === 'live') {
                    <div class="big-score">{{ m.home_goals ?? 0 }} - {{ m.away_goals ?? 0 }}</div>
                    <div class="when live-tag">🔴 {{ m.minute != null ? m.minute + "'" : 'Descanso' }}</div>
                  } @else if (m.status === 'finished') {
                    <div class="big-score">{{ m.home_goals ?? 0 }} - {{ m.away_goals ?? 0 }}</div>
                    <div class="when">Final</div>
                  } @else {
                    <div class="vs">VS</div>
                    <div class="when">{{ kickoff(m.kickoff) }}</div>
                  }
                </div>
                <div class="side right">
                  <span class="code">{{ teamLabel(m.away_name, m.away_code, m.away_placeholder) }}</span>
                  <span class="flag"><app-flag [code]="m.away_code ?? undefined" /></span>
                </div>
              </div>
            }
          </div>
        } @else {
          <div class="card empty">
            <p class="muted">No hay partidos programados para hoy. Consulta el fixture completo.</p>
          </div>
        }
      </section>
    </div>
  `,
  styles: [
    `
      .intro { max-width: 720px; margin: 30px 0 8px; }
      h1 { font-size: clamp(1.8rem, 5vw, 3rem); font-weight: 800; line-height: 1.08; margin: 12px 0; }
      .grad { background: linear-gradient(120deg, var(--primary), var(--accent)); -webkit-background-clip: text; background-clip: text; color: transparent; }
      .lead { font-size: 1.02rem; }

      .empty { padding: 26px; text-align: center; margin-top: 20px; }

      .block { margin-top: 40px; }
      .block h2 { font-size: 1.4rem; margin-bottom: 16px; }

      .today { display: flex; flex-direction: column; gap: 10px; }
      .match { display: flex; align-items: center; padding: 14px 18px; gap: 12px; }
      .match.is-live { border-color: rgba(239, 68, 68, 0.45); }
      .side { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0; }
      .side.right { justify-content: flex-end; }
      .side .flag { font-size: 1.8rem; flex: none; }
      .side .code { font-family: 'Poppins'; font-weight: 700; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .center { width: 130px; text-align: center; flex: none; }
      .when { font-size: 0.78rem; color: var(--muted); margin-top: 4px; }
      .when.live-tag { color: #fca5a5; font-weight: 700; }
      .vs { font-family: 'Poppins'; font-weight: 800; color: var(--muted); }
      .big-score { font-family: 'Poppins'; font-weight: 800; font-size: 1.5rem; }

      @media (max-width: 560px) {
        .center { width: 96px; }
        .side .flag { font-size: 1.4rem; }
        .side .code { font-size: 0.85rem; }
        .big-score { font-size: 1.3rem; }
      }
    `,
  ],
})
export class LiveComponent {
  private api = inject(ApiService);
  private seo = inject(SeoService);
  private destroyRef = inject(DestroyRef);

  live = signal<LiveMatch[]>([]);
  today = signal<LiveMatch[]>([]);
  loadingToday = signal(true);

  private featured = computed<LiveMatch | undefined>(() => this.live()[0]);

  constructor() {
    timer(0, 120_000)
      .pipe(
        switchMap(() => this.api.getLiveMatches().pipe(catchError(() => of<LiveMatch[]>([])))),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((list) => this.live.set(list));

    timer(0, 120_000)
      .pipe(
        switchMap(() => this.api.getTodayMatches().pipe(catchError(() => of<LiveMatch[]>([])))),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((list) => {
        this.today.set(list);
        this.loadingToday.set(false);
      });

    // Título dinámico reactivo: cuando hay un partido en vivo, refleja el marcador.
    effect(() => {
      const m = this.featured();
      if (m) {
        const home = m.home_code || m.home_name || '???';
        const away = m.away_code || m.away_name || '???';
        const min = m.minute != null ? ` (${m.minute}')` : '';
        this.seo.update({
          ...DEFAULT_SEO,
          title: `🔴 ${home} ${m.home_goals ?? 0}-${m.away_goals ?? 0} ${away}${min} · En vivo`,
        });
      } else {
        this.seo.update(DEFAULT_SEO);
      }
    });
  }

  teamLabel(name?: string | null, code?: string | null, placeholder?: string | null): string {
    return name || code || placeholder || 'Por confirmar';
  }

  kickoff(iso?: string | null): string {
    if (!iso) return 'Por confirmar';
    return new Date(iso).toLocaleString('es', {
      hour: '2-digit',
      minute: '2-digit',
    });
  }
}
