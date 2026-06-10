import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class AdminService {
  private http = inject(HttpClient);
  private base = environment.apiBaseUrl;
  token = signal<string>(localStorage.getItem('admin_token') || '');

  setToken(t: string): void {
    this.token.set(t);
    localStorage.setItem('admin_token', t);
  }
  clear(): void {
    this.token.set('');
    localStorage.removeItem('admin_token');
  }

  private opts() {
    return { headers: new HttpHeaders({ 'X-Admin-Token': this.token() }) };
  }

  check(): Observable<{ ok: boolean }> {
    return this.http.get<{ ok: boolean }>(`${this.base}/admin/check`, this.opts());
  }
  status(): Observable<Record<string, unknown>> {
    return this.http.get<Record<string, unknown>>(`${this.base}/admin/status`, this.opts());
  }
  run(path: string, method: 'post' | 'get'): Observable<Record<string, unknown>> {
    const url = `${this.base}/admin/${path}`;
    return method === 'post'
      ? this.http.post<Record<string, unknown>>(url, {}, this.opts())
      : this.http.get<Record<string, unknown>>(url, this.opts());
  }
}
