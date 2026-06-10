import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';

interface LoginResponse {
  access_token: string;
  token_type: string;
  username: string;
}

@Injectable({ providedIn: 'root' })
export class AdminService {
  private http = inject(HttpClient);
  private base = environment.apiBaseUrl;
  token = signal<string>(localStorage.getItem('admin_jwt') || '');
  username = signal<string>(localStorage.getItem('admin_user') || '');

  login(username: string, password: string): Observable<LoginResponse> {
    return this.http.post<LoginResponse>(`${this.base}/admin/login`, { username, password });
  }
  setSession(r: LoginResponse): void {
    this.token.set(r.access_token);
    this.username.set(r.username);
    localStorage.setItem('admin_jwt', r.access_token);
    localStorage.setItem('admin_user', r.username);
  }
  clear(): void {
    this.token.set('');
    this.username.set('');
    localStorage.removeItem('admin_jwt');
    localStorage.removeItem('admin_user');
  }

  private opts() {
    return { headers: new HttpHeaders({ Authorization: `Bearer ${this.token()}` }) };
  }

  check(): Observable<{ ok: boolean }> {
    return this.http.get<{ ok: boolean }>(`${this.base}/admin/check`, this.opts());
  }
  status(): Observable<Record<string, unknown>> {
    return this.http.get<Record<string, unknown>>(`${this.base}/admin/status`, this.opts());
  }
  job(): Observable<Record<string, unknown>> {
    return this.http.get<Record<string, unknown>>(`${this.base}/admin/job`, this.opts());
  }
  run(path: string, method: 'post' | 'get'): Observable<Record<string, unknown>> {
    const url = `${this.base}/admin/${path}`;
    return method === 'post'
      ? this.http.post<Record<string, unknown>>(url, {}, this.opts())
      : this.http.get<Record<string, unknown>>(url, this.opts());
  }
}
