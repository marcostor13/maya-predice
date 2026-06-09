import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { ApiService } from '../../core/services/api.service';

@Component({
  selector: 'app-subscribe',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div class="subscribe card">
      <div class="glow"></div>
      <div class="content">
        <h3>📩 Recibe predicciones en tu correo</h3>
        <p class="muted">
          Suscríbete y te enviaremos los pronósticos y novedades del Mundial 2026
          actualizados tras cada jornada.
        </p>
        @if (done()) {
          <p class="ok">✅ {{ message() }}</p>
        } @else {
          <form (ngSubmit)="submit()" class="row">
            <input
              type="email"
              name="email"
              [(ngModel)]="email"
              placeholder="tu@correo.com"
              required
              [disabled]="loading()"
            />
            <button class="btn" type="submit" [disabled]="loading() || !email">
              @if (loading()) { <span class="spinner" style="width:18px;height:18px"></span> }
              @else { Suscribirme }
            </button>
          </form>
          @if (error()) { <p class="err">{{ error() }}</p> }
        }
      </div>
    </div>
  `,
  styles: [
    `
      .subscribe { position: relative; overflow: hidden; padding: 28px; }
      .glow {
        position: absolute; inset: -40% 30% auto -10%; height: 240px;
        background: radial-gradient(circle, rgba(45,212,191,.35), transparent 60%);
        animation: floaty 6s ease-in-out infinite; pointer-events: none;
      }
      .content { position: relative; }
      h3 { font-size: 1.3rem; margin-bottom: 6px; }
      .row { display: flex; gap: 10px; margin-top: 16px; flex-wrap: wrap; }
      input {
        flex: 1; min-width: 200px; padding: 13px 16px; border-radius: 999px;
        border: 1px solid var(--border); background: var(--surface-2); color: var(--text);
        font-size: 1rem; outline: none; transition: border-color .2s ease;
      }
      input:focus { border-color: var(--primary); }
      .ok { color: var(--primary-2); font-weight: 600; margin-top: 14px; }
      .err { color: var(--danger); margin-top: 10px; font-size: .9rem; }
    `,
  ],
})
export class SubscribeComponent {
  private api = inject(ApiService);
  email = '';
  loading = signal(false);
  done = signal(false);
  message = signal('');
  error = signal('');

  submit(): void {
    if (!this.email) return;
    this.loading.set(true);
    this.error.set('');
    this.api.subscribe(this.email).subscribe({
      next: (r) => {
        this.message.set(r.message);
        this.done.set(true);
        this.loading.set(false);
      },
      error: (e) => {
        this.error.set(e?.error?.detail?.[0]?.msg ?? 'No se pudo completar la suscripción.');
        this.loading.set(false);
      },
    });
  }
}
