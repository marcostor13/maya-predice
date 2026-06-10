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
}

interface Factor { icon: string; nombre: string; desc: string; }

// Operaciones avanzadas (la principal es "Actualizar" = recompute).
const ADVANCED: Command[] = [
  { key: 'sync', method: 'post', icon: '📥', title: 'Solo sincronizar datos oficiales',
    desc: 'Reingiere el calendario y los resultados oficiales y detecta cambios (sin recalcular el modelo).' },
  { key: 'train', method: 'post', icon: '🧠', title: 'Solo reentrenar modelo',
    desc: 'Reentrena el modelo con el histórico y guarda las fuerzas por equipo.' },
  { key: 'simulate', method: 'post', icon: '🎲', title: 'Solo re-simular torneo',
    desc: 'Vuelve a correr la simulación Monte Carlo con el modelo actual.' },
  { key: 'squads', method: 'post', icon: '👥', title: 'Sincronizar plantillas',
    desc: 'Trae jugadores y entrenador de las fuentes configuradas (Sportmonks…), con consenso y caché.' },
  { key: 'notify', method: 'post', icon: '📧', title: 'Enviar emails a suscriptores',
    desc: 'Envía ahora el digest de predicciones a los suscriptores activos (requiere SMTP).' },
  { key: 'backtest', method: 'get', icon: '📈', title: 'Backtest del modelo',
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

        <!-- ACCIÓN PRINCIPAL -->
        <div class="card primary">
          <div class="p-text">
            <h2>🔄 Actualizar predicciones</h2>
            <p class="muted">
              Reingiere los resultados oficiales y <b>recalcula todo con todas las variables</b>
              (no borra nada): reentrena el modelo, regenera las predicciones de cada partido y
              vuelve a simular el torneo. Hazlo cuando termine una jornada; el modelo se vuelve
              más preciso conforme llegan resultados reales.
            </p>
          </div>
          <button class="btn big" (click)="run(primary)" [disabled]="running()['recompute']">
            @if (running()['recompute']) { <span class="spinner" style="width:18px;height:18px"></span> Actualizando… }
            @else { Actualizar ahora }
          </button>
          @if (result()['recompute']; as r) {
            <div class="res" [class.bad]="r.error"><b>{{ r.error ? '✗ Error' : '✓ Hecho' }}</b><pre>{{ r.body | json }}</pre></div>
          }
        </div>

        <!-- QUÉ SE TIENE EN CUENTA -->
        <h3 class="sec">📋 Qué se tiene en cuenta para la predicción</h3>
        @if (factors(); as f) {
          <div class="factors" @listStagger>
            @for (fac of f; track fac.nombre) {
              <div class="factor card">
                <span class="fi">{{ fac.icon }}</span>
                <div><b>{{ fac.nombre }}</b><p class="muted">{{ fac.desc }}</p></div>
              </div>
            }
          </div>
          @if (config(); as c) {
            <p class="muted small cfg">
              Config actual · histórico: {{ c['filtro_historico'] }} desde {{ c['desde_anio'] }} ·
              decaimiento ξ={{ c['decaimiento_temporal_xi'] }} · prior Elo={{ c['peso_prior_elo'] }} ·
              simulación {{ c['iteraciones_simulacion'] }} iter · fuentes: {{ asArray(c['fuentes_plantillas']).join(', ') || '—' }}
            </p>
          }
        }

        <!-- AVANZADO -->
        <button class="chip toggle" (click)="showAdv.set(!showAdv())">
          {{ showAdv() ? '▾' : '▸' }} Operaciones avanzadas
        </button>
        @if (showAdv()) {
          <div class="commands" @listStagger>
            @for (c of advanced; track c.key) {
              <div class="cmd card">
                <div class="cmd-head"><span class="ic">{{ c.icon }}</span><span class="t">{{ c.title }}</span></div>
                <p class="desc muted">{{ c.desc }}</p>
                <button class="btn ghost" (click)="run(c)" [disabled]="running()[c.key]">
                  @if (running()[c.key]) { <span class="spinner" style="width:16px;height:16px"></span> Ejecutando… }
                  @else { Ejecutar }
                </button>
                @if (result()[c.key]; as r) {
                  <div class="res" [class.bad]="r.error"><b>{{ r.error ? '✗ Error' : '✓ Hecho' }}</b><pre>{{ r.body | json }}</pre></div>
                }
              </div>
            }
          </div>
        }
      }
    </div>
  `,
  styles: [
    `
      .page { padding: 32px 20px 60px; }
      h1 { font-size: 1.9rem; margin-bottom: 18px; }
      .login { max-width: 460px; padding: 26px; }
      .form { display: flex; flex-direction: column; gap: 10px; margin: 14px 0; }
      input { padding: 12px 16px; border-radius: 999px; border: 1px solid var(--border);
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
      .primary { margin-top: 22px; padding: 26px; border: 1px solid var(--primary); }
      .primary h2 { font-size: 1.4rem; }
      .primary .p-text { margin-bottom: 16px; }
      .btn.big { font-size: 1.05rem; padding: 14px 28px; }
      .sec { margin: 30px 0 12px; }
      .factors { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
      @media (max-width: 760px) { .factors { grid-template-columns: 1fr; } }
      .factor { display: flex; gap: 12px; padding: 14px 16px; }
      .factor .fi { font-size: 1.4rem; }
      .factor p { font-size: .85rem; margin: 4px 0 0; }
      .cfg { background: var(--surface); border-radius: 10px; padding: 10px 14px; }
      .toggle { cursor: pointer; display: inline-block; margin: 26px 0 12px; background: var(--surface); border: 1px solid var(--border); color: var(--muted); }
      .commands { display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; }
      @media (max-width: 760px) { .commands { grid-template-columns: 1fr; } }
      .cmd { padding: 18px; display: flex; flex-direction: column; gap: 10px; }
      .cmd-head { display: flex; align-items: center; gap: 10px; }
      .cmd-head .ic { font-size: 1.4rem; } .cmd-head .t { font-family: 'Poppins'; font-weight: 700; }
      .desc { font-size: .88rem; flex: 1; }
      .cmd .btn { align-self: flex-start; }
      .res { background: var(--surface-2); border-radius: 10px; padding: 10px 12px; font-size: .8rem; }
      .res.bad { background: rgba(248,113,113,.12); }
      .res pre { margin: 6px 0 0; white-space: pre-wrap; word-break: break-word; color: var(--muted); }
    `,
  ],
})
export class AdminComponent {
  private api = inject(AdminService);
  advanced = ADVANCED;
  primary: Command = { key: 'recompute', method: 'post', icon: '🔄', title: 'Actualizar', desc: '' };

  user = '';
  pass = '';
  adminUser = this.api.username;
  authed = signal(false);
  checking = signal(false);
  loginError = signal('');
  status = signal<Record<string, unknown> | null>(null);
  factors = signal<Factor[] | null>(null);
  config = signal<Record<string, unknown> | null>(null);
  showAdv = signal(false);
  running = signal<Record<string, boolean>>({});
  result = signal<Record<string, { error: boolean; body: unknown }>>({});

  constructor() {
    if (this.api.token()) {
      this.api.check().subscribe({
        next: () => { this.authed.set(true); this.loadStatus(); this.loadFactors(); },
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
        this.loadFactors();
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
  loadFactors(): void {
    this.api.run('factors', 'get').subscribe({
      next: (r) => {
        this.factors.set((r['factores'] as Factor[]) ?? []);
        this.config.set((r['config'] as Record<string, unknown>) ?? null);
      },
    });
  }

  asArray(v: unknown): unknown[] {
    return Array.isArray(v) ? v : [];
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
