import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, forkJoin, of, switchMap } from 'rxjs';

import { Coach, Player, Position, Squad } from '../models';

/**
 * Extrae plantillas (jugadores + entrenador) con foto desde la **API de MediaWiki**
 * de Wikipedia, pasando por el proxy de Netlify (`/proxy/wiki/...`, ruta RELATIVA →
 * mismo-origen, sin CORS y sin tocar la allowlist de Coolify). Replica la lógica del
 * proveedor del backend (`app/data/players/wikipedia.py`) en TypeScript, parseando
 * las plantillas wiki `{{nat fs player}}` y las miniaturas vía `prop=pageimages`.
 *
 * Es un **fallback**: solo se usa cuando el backend no trae la plantilla. Todo el
 * parseo es defensivo; ante cualquier fallo (red, formato, o que la página use
 * tablas en vez de `{{nat fs player}}`) devuelve `null`. En `ng serve` la ruta
 * `/proxy/wiki/...` no existe → la petición falla → `null` (no rompe la UI).
 */
@Injectable({ providedIn: 'root' })
export class WikiSquadService {
  private http = inject(HttpClient);

  /** Ruta relativa: la sirve Netlify, NO el backend de Coolify. */
  private readonly api = '/proxy/wiki/w/api.php';

  /** Títulos de Wikipedia que difieren del patrón "<País> national football team". */
  private static readonly TITLE_OVERRIDES: Record<string, string> = {
    'United States': "United States men's national soccer team",
    USA: "United States men's national soccer team",
  };

  // {{nat fs player|no=1|pos=GK|name=[[X]]|club=[[Y]]|...}} (también "nat fs g player")
  private static readonly PLAYER_TPL = /\{\{\s*nat fs (?:g )?player\b([^}]*)\}\}/gi;
  private static readonly WIKILINK = /\[\[([^\]|]+)(?:\|([^\]]+))?\]\]/;
  private static readonly MANAGER =
    /\|\s*(?:manager|head[ _]coach|coach)\s*=\s*([^\n|]+)/i;

  private static readonly POS_MAP: Record<string, Position> = {
    gk: 'GK', goalkeeper: 'GK', g: 'GK', portero: 'GK',
    def: 'DEF', defender: 'DEF', defence: 'DEF', d: 'DEF', df: 'DEF',
    back: 'DEF', defensa: 'DEF', 'centre-back': 'DEF',
    mid: 'MID', midfielder: 'MID', m: 'MID', medio: 'MID', mf: 'MID', centrocampista: 'MID',
    fwd: 'FWD', forward: 'FWD', attacker: 'FWD', f: 'FWD', fw: 'FWD',
    striker: 'FWD', winger: 'FWD', delantero: 'FWD',
  };

  getSquad(teamName: string, teamCode = ''): Observable<Squad | null> {
    if (!teamName) return of(null);
    const title =
      WikiSquadService.TITLE_OVERRIDES[teamName] ??
      `${teamName} national football team`;

    return this.fetchWikitext(title).pipe(
      switchMap((wikitext) => {
        if (!wikitext) return of<Squad | null>(null);
        const { players: raw, managerTitle } = this.parseWikitext(wikitext);
        if (!raw.length) return of<Squad | null>(null);

        const photoTitles = raw.map((p) => p.title).filter((t): t is string => !!t);
        if (managerTitle?.title) photoTitles.push(managerTitle.title);

        return this.fetchPhotos(photoTitles).pipe(
          switchMap((photos) =>
            of(this.buildSquad(raw, managerTitle, photos, teamName, teamCode)),
          ),
        );
      }),
      catchError(() => of<Squad | null>(null)),
    );
  }

  // --- Red (vía proxy) ---

  private fetchWikitext(title: string): Observable<string | null> {
    const params = new HttpParams({
      fromObject: {
        action: 'query',
        prop: 'revisions',
        rvprop: 'content',
        rvslots: 'main',
        titles: title,
        redirects: '1',
        format: 'json',
        formatversion: '2',
      },
    });
    return this.http.get<WikiRevisionsResponse>(this.api, { params }).pipe(
      switchMap((data) => {
        const pages = data?.query?.pages ?? [];
        for (const page of pages) {
          const content = page?.revisions?.[0]?.slots?.main?.content;
          if (content) return of(content);
        }
        return of<string | null>(null);
      }),
      catchError(() => of<string | null>(null)),
    );
  }

  /** Miniatura por título de página, en lotes de 50 (máximo de la API). */
  private fetchPhotos(titles: string[]): Observable<Record<string, string>> {
    const unique = [...new Set(titles.filter(Boolean))];
    if (!unique.length) return of({});

    const batches: Observable<Record<string, string>>[] = [];
    for (let i = 0; i < unique.length; i += 50) {
      const chunk = unique.slice(i, i + 50);
      const params = new HttpParams({
        fromObject: {
          action: 'query',
          prop: 'pageimages',
          piprop: 'thumbnail',
          pithumbsize: '200',
          titles: chunk.join('|'),
          redirects: '1',
          format: 'json',
          formatversion: '2',
        },
      });
      batches.push(
        this.http.get<WikiPageImagesResponse>(this.api, { params }).pipe(
          switchMap((data) => {
            const out: Record<string, string> = {};
            for (const page of data?.query?.pages ?? []) {
              const thumb = page?.thumbnail?.source;
              if (page?.title && thumb) out[page.title] = thumb;
            }
            return of(out);
          }),
          catchError(() => of<Record<string, string>>({})),
        ),
      );
    }

    return forkJoin(batches).pipe(
      switchMap((results) => of(Object.assign({}, ...results) as Record<string, string>)),
      catchError(() => of<Record<string, string>>({})),
    );
  }

  // --- Parseo del wikitexto ---

  private parseWikitext(text: string): {
    players: RawPlayer[];
    managerTitle: { title: string | null; name: string | null } | null;
  } {
    const players: RawPlayer[] = [];
    const tpl = new RegExp(WikiSquadService.PLAYER_TPL.source, 'gi');
    let block: RegExpExecArray | null;
    while ((block = tpl.exec(text)) !== null) {
      const params = block[1] ?? '';
      const [title, name] = this.link(this.param(params, 'name'));
      if (!name) continue;
      const [clubTitle] = this.link(this.param(params, 'club'));
      const numRaw = this.param(params, 'no');
      players.push({
        title,
        name,
        no: numRaw && /^\d+$/.test(numRaw) ? parseInt(numRaw, 10) : null,
        pos: this.param(params, 'pos'),
        club: clubTitle,
      });
    }

    const managerMatch = WikiSquadService.MANAGER.exec(text);
    let managerTitle: { title: string | null; name: string | null } | null = null;
    if (managerMatch) {
      const [title, name] = this.link(managerMatch[1]);
      if (title || name) managerTitle = { title, name };
    }
    return { players, managerTitle };
  }

  /** Valor de un parámetro de plantilla; consume wikilinks con `|` internos. */
  private param(params: string, key: string): string | null {
    const re = new RegExp('\\|\\s*' + key + '\\s*=\\s*((?:\\[\\[[^\\]]*\\]\\]|[^|])*)');
    const m = re.exec(params);
    return m ? m[1].trim() : null;
  }

  /** Devuelve [título_de_página, texto_visible] de un wikilink, o [texto, texto]. */
  private link(value: string | null): [string | null, string | null] {
    if (!value) return [null, null];
    const m = WikiSquadService.WIKILINK.exec(value);
    if (m) {
      const target = m[1].trim();
      const display = (m[2] ?? m[1]).trim();
      return [target, display];
    }
    const clean = value.trim();
    return [clean || null, clean || null];
  }

  // --- Construcción del Squad (compatible con el modelo) ---

  private buildSquad(
    raw: RawPlayer[],
    managerTitle: { title: string | null; name: string | null } | null,
    photos: Record<string, string>,
    teamName: string,
    teamCode: string,
  ): Squad {
    const players: Player[] = raw.map((p, i) => ({
      id: -(i + 1),
      team_id: -1,
      full_name: p.name ?? '',
      position: WikiSquadService.POS_MAP[(p.pos ?? '').trim().toLowerCase()] ?? 'UNKNOWN',
      shirt_number: p.no ?? undefined,
      club: p.club ?? undefined,
      role: 'unknown',
      status: 'unknown',
      photo_url: (p.title ? photos[p.title] : undefined) ?? undefined,
      confidence: 1,
      sources_count: 1,
    }));

    let coach: Coach | undefined;
    if (managerTitle && (managerTitle.name || managerTitle.title)) {
      coach = {
        id: -1,
        team_id: -1,
        name: (managerTitle.name ?? managerTitle.title) as string,
        status: 'unknown',
        photo_url: (managerTitle.title ? photos[managerTitle.title] : undefined) ?? undefined,
        confidence: 1,
        sources_count: 1,
      };
    }

    return { team_code: teamCode, team_name: teamName, coach, players };
  }
}

// --- Tipos internos ---

interface RawPlayer {
  title: string | null;
  name: string | null;
  no: number | null;
  pos: string | null;
  club: string | null;
}

interface WikiRevisionsResponse {
  query?: {
    pages?: Array<{
      revisions?: Array<{ slots?: { main?: { content?: string } } }>;
    }>;
  };
}

interface WikiPageImagesResponse {
  query?: {
    pages?: Array<{ title?: string; thumbnail?: { source?: string } }>;
  };
}
