import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { Match, Prediction, Team } from '../models';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);
  private base = environment.apiBaseUrl;

  // --- Teams ---
  getTeams(group?: string): Observable<Team[]> {
    const q = group ? `?group=${group}` : '';
    return this.http.get<Team[]>(`${this.base}/teams${q}`);
  }

  getTeam(id: number): Observable<Team> {
    return this.http.get<Team>(`${this.base}/teams/${id}`);
  }

  // --- Matches ---
  getMatches(params: { stage?: string; group?: string } = {}): Observable<Match[]> {
    const q = new URLSearchParams(params as Record<string, string>).toString();
    return this.http.get<Match[]>(`${this.base}/matches${q ? '?' + q : ''}`);
  }

  getMatch(id: number): Observable<Match> {
    return this.http.get<Match>(`${this.base}/matches/${id}`);
  }

  // --- Predictions ---
  getMatchPrediction(matchId: number): Observable<Prediction> {
    return this.http.get<Prediction>(`${this.base}/predictions/match/${matchId}`);
  }

  runPrediction(matchId: number): Observable<Prediction> {
    return this.http.post<Prediction>(`${this.base}/predictions/run`, { match_id: matchId });
  }
}
