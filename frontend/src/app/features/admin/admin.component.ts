import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { AdminService } from '../../core/services/admin.service';
import { listStagger } from '../../core/util/animations';

interface Command {
  key: string;
  method: 'post' | 'get';
  icon: string;
  title: string;
  desc: string;
  slow?: boolean;
}

const COMMANDS: Command[] = [
  { key: 'bootstrap', method: 'post', icon: '🚀', title: 'Carga inicial completa', slow: true,
    desc: 'Ingiere partidos, entrena el modelo, genera predicciones, simula el torneo y carga plantillas. Úsalo la primera vez o si falta algo.' },
  { key: 'recompute', method: 'post', icon: '🔄', title: 'Recalcular todo', slow: true,
    desc: 'Reingiere resultados oficiales y, si hay cambios, reentrena, regenera predicciones y vuelve a simular.' },
  { key: 'sync', method: 'post', icon: '📥', title: 'Sincronizar datos oficiales',
    desc: 'Reingiere el calendario y los resultados oficiales (openfootball) y detecta cambios.' },
  { key: 'train', method: 'post', icon: '🧠', title: 'Entrenar modelo', slow: true,
    desc: 'Reentrena el modelo Dixon-Coles con el histórico y guarda las fuerzas por equipo.' },
  { key: 'simulate', method: 'post', icon: '🎲', title: 'Simular torneo', slow: true,
    desc: 'Ejecuta la simulación Monte Carlo y guarda las probabilidades de avanzar y de ser campeón.' },
  { key: 'squads', method: 'post', icon: '👥', title: 'Sincronizar plantillas', slow: true,
    desc: 'Trae jugadores y entrenador de las fuentes configuradas (Sportmonks…), con consenso y caché.' },
  { key: 'notify', method: 'post', icon: '📧', title: 'Enviar emails',
    desc: 'Envía ahora el digest de predicciones a los suscriptores activos (requiere SMTP configurado).' },
  { key: 'backtest', method: 'get', icon: '📊', title: 'Backtest del modelo', slow: true,
    desc: 'Evalúa la precisión fuera de muestra: log-loss, Brier y accuracy frente a la línea base.' },
];

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [CommonModule, FormsModule],
  animations: [listStagger],
  template: `
    <div class="container page">
      <h1>🛠️ Panel de administración</h1>

      @if (!authed()) {
        <!-- Login -->
        <div class="card login">
          <p class="muted">Inicia sesión con tu usuario administrador.</p>
          <form (ngSubmit)="login()" class="form">
            <input type="text" [(ngModel)]="user" name="user" placeholder="Usuario" autocomplete="username" required />
            <input type="password" [(ngModel)]="pass" name="pass" placeholder="Contraseña" autocomplete="current-password" required />
            <button class="btn" type="submit" [disabled]="checking()">
              @if (checking()) { <span class="spinner" style="width:18px;height:18px"></span> } @else { Entrar }
            </button>
          </form>
          @if (loginError()) { <p class="err">{{ loginError() }}</p> }
          <p class="muted small">Crea el usuario con <code>python -m app.data.create_admin &lt;usuario&gt; &lt;contraseña&gt;</code></p>
        </div>
      } @else {
        <!-- Estado -->
        <div class="head">
          <h3>Hola, {{ adminUser() }}</h3>
          <button class="chip btn-ghost" (click)="loadStatus()">↻ Refrescar</button>
          <button class="chip btn-ghost" (click)="logout()">Salir</button>
        </div>
        @if (status(); as s) {
          <div class="stats" @listStagger>
            <div class="stat card"><b>{{ s['teams'] }}</b><span>equipos</span></div>
            <div class="stat card"><b>{{ s['matches'] }}</b><span>partidos</span></div>
            <div class="stat card"><b>{{ s['matches_finished'] }}</b><span>jugados</span></div>
            <div class="stat card"><b>{{ s['predictions'] }}</b><span>predicciones</span></div>
            <div class="stat card"><b>{{ s['subscribers_active'] }}</b><span>suscriptores</span></div>
            <div class="stat card"><b>{{ s['api_cache_rows'] }}</b><span>caché API</span></div>
          </div>
          <p class="muted small">Última simulación: {{ s['last_simulation'] || '—' }} · modelo {{ s['model_version'] }}</p>
        }

        <!-- Comandos -->
        <h3 class="cmd-title">Comandos</h3>
        <div class="commands" @listStagger>
          @for (c of commands; track c.key) {
            <div class="cmd card">
              <div class="cmd-head">
                <span class="ic">{{ c.icon }}</span>
                <span class="t">{{ c.title }}</span>
                @if (c.slow) { <span class="chip slow">puede tardar</span> }
              </div>
              <p class="desc muted">{{ c.desc }}</p>
              <button class="btn" (click)="run(c)" [disabled]="running()[c.key]">
                @if (running()[c.key]) { <span class="spinner" style="width:16px;height:16px"></span> Ejecutando… }
                @else { Ejecutar }
              </button>
              @if (result()[c.key]; as r) {
                <div class="res" [class.bad]="r.error">
                  <b>{{ r.error ? '✗ Error' : '✓ Hecho' }}</b>
                  <pre>{{ r.body | json }}</pre>
                </div>
              }
            </div>
          }
        </div>
      }
    </div>
  `,
  styles: [
    `
      .page { padding: 32px 20px 60px; }
      h1 { font-size: 1.9rem; margin-bottom: 18px; }
      .login { max-width: 460px; padding: 26px; }
      .form { display: flex; flex-direction: column; gap: 10px; margin: 14px 0; }
      .row { display: flex; gap: 10px; margin-top: 14px; }
      input { flex: 1; padding: 12px 16px; border-radius: 999px; border: 1px solid var(--border);
              background: var(--surface-2); color: var(--text); outline: none; }
      input:focus { border-color: var(--primary); }
      .err { color: var(--danger); margin-top: 10px; }
      .head { display: flex; align-items: center; gap: 10px; margin: 8px 0 14px; }
      .head h3 { flex: 1; }
      .btn-ghost { cursor: pointer; background: var(--surface); border: 1px solid var(--border); color: var(--muted); }
      .stats { display: grid; grid-template-columns: repeat(6, 1fr); gap: 10px; }
      @media (max-width: 720px) { .stats { grid-template-columns: repeat(3, 1fr); } }
      .stat { padding: 14px; text-align: center; display: flex; flex-direction: column; }
      .stat b { font-family: 'Poppins'; font-size: 1.4rem; color: var(--primary); }
      .stat span { font-size: .75rem; color: var(--muted); }
      .small { font-size: .8rem; margin-top: 8px; }
      .cmd-title { margin: 28px 0 12px; }
      .commands { display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; }
      @media (max-width: 760px) { .commands { grid-template-columns: 1fr; } }
      .cmd { padding: 18px; display: flex; flex-direction: column; gap: 10px; }
      .cmd-head { display: flex; align-items: center; gap: 10px; }
      .cmd-head .ic { font-size: 1.5rem; }
      .cmd-head .t { font-family: 'Poppins'; font-weight: 700; }
      .chip.slow { background: rgba(251,191,36,.15); color: var(--gold); border-color: transparent; font-size: .68rem; }
      .desc { font-size: .9rem; flex: 1; }
      .cmd .btn { align-self: flex-start; }
      .res { background: var(--surface-2); border-radius: 10px; padding: 10px 12px; font-size: .8rem; }
      .res.bad { background: rgba(248,113,113,.12); }
      .res pre { margin: 6px 0 0; white-space: pre-wrap; word-break: break-word; color: var(--muted); }
    `,
  ],
})
export class AdminComponent {
  private api = inject(AdminService);
  commands = COMMANDS;

  user = '';
  pass = '';
  adminUser = this.api.username;
  authed = signal(false);
  checking = signal(false);
  loginError = signal('');
  status = signal<Record<string, unknown> | null>(null);
  running = signal<Record<string, boolean>>({});
  result = signal<Record<string, { error: boolean; body: unknown }>>({});

  constructor() {
    if (this.api.token()) {
      this.api.check().subscribe({
        next: () => { this.authed.set(true); this.loadStatus(); },
        error: () => this.api.clear(),
      });
    }
  }

  login(): void {
    if (!this.user || !this.pass) return;
    this.checking.set(true);
    this.loginError.set('');
    this.api.login(this.user, this.pass).subscribe({
      next: (r) => {
        this.api.setSession(r);
        this.authed.set(true);
        this.checking.set(false);
        this.pass = '';
        this.loadStatus();
      },
      error: (e) => {
        this.checking.set(false);
        this.loginError.set(e?.error?.detail ?? 'Usuario o contraseña incorrectos.');
      },
    });
  }

  logout(): void {
    this.api.clear();
    this.authed.set(false);
    this.user = '';
    this.pass = '';
  }

  loadStatus(): void {
    this.api.status().subscribe({ next: (s) => this.status.set(s) });
  }

  run(c: Command): void {
    this.running.update((r) => ({ ...r, [c.key]: true }));
    this.api.run(c.key, c.method).subscribe({
      next: (body) => {
        this.result.update((r) => ({ ...r, [c.key]: { error: false, body } }));
        this.running.update((r) => ({ ...r, [c.key]: false }));
        this.loadStatus();
      },
      error: (e) => {
        this.result.update((r) => ({ ...r, [c.key]: { error: true, body: e?.error?.detail ?? 'Error' } }));
        this.running.update((r) => ({ ...r, [c.key]: false }));
      },
    });
  }
}
