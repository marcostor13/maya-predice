import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { LiveMatch, Match, Prediction, Simulation, Squad, Team } from '../models';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);
  private base = environment.apiBaseUrl;

  // --- Teams ---
  getTeams(group?: string): Observable<Team[]> {
    const q = group ? `?group=${group}` : '';
    return this.http.get<Team[]>(`${this.base}/teams${q}`);
  }

  // --- Matches ---
  getMatches(params: { stage?: string; group?: string } = {}): Observable<Match[]> {
    const q = new URLSearchParams(params as Record<string, string>).toString();
    return this.http.get<Match[]>(`${this.base}/matches${q ? '?' + q : ''}`);
  }

  getMatch(id: number): Observable<Match> {
    return this.http.get<Match>(`${this.base}/matches/${id}`);
  }

  // --- Live ---
  getLiveMatches(): Observable<LiveMatch[]> {
    return this.http.get<LiveMatch[]>(`${this.base}/matches/live`);
  }

  getTodayMatches(): Observable<LiveMatch[]> {
    return this.http.get<LiveMatch[]>(`${this.base}/matches/today`);
  }

  // --- Predictions ---
  getPredictions(): Observable<Prediction[]> {
    return this.http.get<Prediction[]>(`${this.base}/predictions`);
  }

  getMatchPrediction(matchId: number): Observable<Prediction> {
    return this.http.get<Prediction>(`${this.base}/predictions/match/${matchId}`);
  }

  // --- Squads ---
  getSquad(code: string): Observable<Squad> {
    return this.http.get<Squad>(`${this.base}/squads/${code}`);
  }

  // --- Simulation ---
  getSimulation(): Observable<Simulation> {
    return this.http.get<Simulation>(`${this.base}/simulate/tournament`);
  }

  runSimulation(): Observable<Simulation> {
    return this.http.post<Simulation>(`${this.base}/simulate/run`, {});
  }

  // --- Subscribe ---
  subscribe(email: string): Observable<{ status: string; message: string }> {
    return this.http.post<{ status: string; message: string }>(
      `${this.base}/subscribers`,
      { email },
    );
  }
}
