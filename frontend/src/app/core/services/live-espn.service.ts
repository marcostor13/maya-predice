import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, of } from 'rxjs';

import { LiveMatch } from '../models';

/**
 * Un partido normalizado del scoreboard de ESPN (códigos FIFA de 3 letras).
 */
export interface EspnFixture {
  homeCode: string;
  awayCode: string;
  homeName: string;
  awayName: string;
  homeGoals: number;
  awayGoals: number;
  minute: number | null;
  live: boolean;
  finished: boolean;
}

/** Forma defensiva del JSON de ESPN que consumimos (parcial, todo opcional). */
interface EspnRaw {
  events?: Array<{
    competitions?: Array<{
      status?: EspnStatus;
      competitors?: Array<{
        homeAway?: string;
        score?: string | number;
        team?: { abbreviation?: string; displayName?: string };
      }>;
    }>;
  }>;
}

interface EspnStatus {
  clock?: number;
  displayClock?: string;
  type?: { state?: string; completed?: boolean };
}

/**
 * Lee el marcador en vivo del Mundial directamente desde ESPN, pasando por el
 * proxy de Netlify (`/proxy/espn/...`, ruta RELATIVA → mismo-origen, sin CORS y
 * sin tocar la allowlist de Coolify). El parseo es totalmente defensivo: ante
 * cualquier fallo de red o de formato devuelve una lista vacía.
 */
@Injectable({ providedIn: 'root' })
export class LiveEspnService {
  private http = inject(HttpClient);

  /** Ruta relativa: la sirve Netlify, NO el backend de Coolify. */
  private readonly espnUrl =
    '/proxy/espn/apis/site/v2/sports/soccer/fifa.world/scoreboard';

  getEspnLive(): Observable<EspnFixture[]> {
    return this.http.get<EspnRaw>(this.espnUrl).pipe(
      map((data) => this.parse(data)),
      catchError(() => of<EspnFixture[]>([])),
    );
  }

  private parse(data: EspnRaw): EspnFixture[] {
    const events = data?.events ?? [];
    const out: EspnFixture[] = [];

    for (const event of events) {
      const comp = event?.competitions?.[0];
      if (!comp) continue;

      const competitors = comp.competitors ?? [];
      const home = competitors.find((c) => c?.homeAway === 'home');
      const away = competitors.find((c) => c?.homeAway === 'away');
      if (!home || !away) continue;

      const homeCode = (home.team?.abbreviation ?? '').toUpperCase();
      const awayCode = (away.team?.abbreviation ?? '').toUpperCase();

      const state = comp.status?.type?.state ?? 'pre';
      const completed = comp.status?.type?.completed === true;
      const live = state === 'in';
      const finished = state === 'post' || completed;

      // Para el marcador en vivo solo interesan los partidos en curso o finalizados.
      if (!live && !finished) continue;

      out.push({
        homeCode,
        awayCode,
        homeName: home.team?.displayName ?? homeCode,
        awayName: away.team?.displayName ?? awayCode,
        homeGoals: this.toInt(home.score),
        awayGoals: this.toInt(away.score),
        minute: this.parseMinute(comp.status),
        live,
        finished,
      });
    }

    return out;
  }

  private toInt(value: string | number | undefined): number {
    if (typeof value === 'number') return Number.isFinite(value) ? value : 0;
    const n = parseInt(value ?? '', 10);
    return Number.isNaN(n) ? 0 : n;
  }

  /** Minuto desde `displayClock` ("67'") o `clock`; HT u otros no numéricos → null. */
  private parseMinute(status?: EspnStatus): number | null {
    const raw = status?.displayClock;
    if (raw) {
      const cleaned = raw.replace(/['+\s]/g, '');
      const n = parseInt(cleaned, 10);
      if (!Number.isNaN(n)) return n;
    }
    if (typeof status?.clock === 'number' && Number.isFinite(status.clock)) {
      return Math.round(status.clock);
    }
    return null;
  }

  /**
   * Mezcla el marcador en vivo: prefiere el backend (caso allowlisted); si está
   * vacío, construye los `LiveMatch` a partir de los partidos en vivo de ESPN,
   * casándolos con los de hoy por código FIFA (mayúsculas) para recuperar el `id`
   * (y con ello la predicción), nombres y metadatos. Si ESPN trae un partido que
   * no está en `today`, se crea con `id: -1` (sin predicción asociada).
   */
  static mergeLive(
    backendLive: LiveMatch[],
    espn: EspnFixture[],
    today: LiveMatch[],
  ): LiveMatch[] {
    if (backendLive.length) return backendLive;

    const liveEspn = espn.filter((e) => e.live);
    return liveEspn.map((e) => {
      const match = today.find(
        (t) =>
          (t.home_code ?? '').toUpperCase() === e.homeCode &&
          (t.away_code ?? '').toUpperCase() === e.awayCode,
      );

      if (match) {
        return {
          ...match,
          home_goals: e.homeGoals,
          away_goals: e.awayGoals,
          minute: e.minute,
          status: 'live',
        };
      }

      return {
        id: -1,
        home_code: e.homeCode,
        away_code: e.awayCode,
        home_name: e.homeName,
        away_name: e.awayName,
        home_goals: e.homeGoals,
        away_goals: e.awayGoals,
        minute: e.minute,
        status: 'live',
        stage: 'group',
      } satisfies LiveMatch;
    });
  }
}
