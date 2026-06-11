import { Component, signal } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [RouterLink, RouterLinkActive],
  template: `
    <nav class="nav">
      <div class="container inner">
        <a routerLink="/" class="brand" (click)="close()">
          <span class="ball floaty">⚽</span>
          <span class="name">maya<span class="accent">predice</span></span>
          <span class="chip wc">Mundial 2026</span>
        </a>

        <!-- Botón hamburguesa (solo móvil) -->
        <button
          class="burger"
          (click)="toggle()"
          [class.open]="open()"
          [attr.aria-expanded]="open()"
          aria-label="Menú"
        >
          <span></span><span></span><span></span>
        </button>

        <!-- Enlaces -->
        <div class="links" [class.show]="open()">
          <a routerLink="/" routerLinkActive="active" [routerLinkActiveOptions]="{ exact: true }" (click)="close()">Inicio</a>
          <a routerLink="/en-vivo" routerLinkActive="active" class="live" (click)="close()">🔴 En vivo</a>
          <a routerLink="/fixture" routerLinkActive="active" (click)="close()">Fixture</a>
          <a routerLink="/equipos" routerLinkActive="active" (click)="close()">Equipos</a>
          <a routerLink="/simulacion" routerLinkActive="active" (click)="close()">Simulación</a>
        </div>
      </div>
    </nav>
  `,
  styles: [
    `
      .nav {
        position: sticky; top: 0; z-index: 50;
        background: rgba(10, 14, 26, 0.82); backdrop-filter: blur(14px);
        border-bottom: 1px solid var(--border);
      }
      .inner { display: flex; align-items: center; justify-content: space-between; height: 66px; }
      .brand { display: flex; align-items: center; gap: 10px; font-family: 'Poppins'; font-weight: 800; font-size: 1.25rem; color: var(--text); }
      .ball { font-size: 1.4rem; display: inline-block; }
      .accent { color: var(--primary); }
      .chip.wc { background: linear-gradient(135deg, rgba(167,139,250,.25), rgba(45,212,191,.25)); color: var(--text); border-color: transparent; }

      .links { display: flex; gap: 6px; align-items: center; }
      .links a {
        color: var(--muted); font-weight: 600; padding: 8px 14px; border-radius: 999px;
        transition: all .2s ease; font-size: .92rem; white-space: nowrap;
      }
      .links a:hover { color: var(--text); background: var(--surface); }
      .links a.active { color: #04241d; background: linear-gradient(135deg, var(--primary), var(--primary-2)); }
      .links a.live { color: #fca5a5; }
      .links a.live:hover { color: #fecaca; background: rgba(239, 68, 68, 0.12); }
      .links a.live.active { color: #fff; background: linear-gradient(135deg, #ef4444, #f97316); }

      /* Hamburguesa: oculta en escritorio */
      .burger {
        display: none; flex-direction: column; gap: 5px; cursor: pointer;
        background: transparent; border: 0; padding: 8px;
      }
      .burger span {
        width: 24px; height: 2px; background: var(--text); border-radius: 2px;
        transition: transform .25s ease, opacity .2s ease;
      }
      .burger.open span:nth-child(1) { transform: translateY(7px) rotate(45deg); }
      .burger.open span:nth-child(2) { opacity: 0; }
      .burger.open span:nth-child(3) { transform: translateY(-7px) rotate(-45deg); }

      /* ---- Móvil ---- */
      @media (max-width: 720px) {
        .chip.wc { display: none; }
        .burger { display: flex; }
        .links {
          position: absolute; top: 66px; left: 0; right: 0;
          flex-direction: column; align-items: stretch; gap: 4px;
          background: rgba(10, 14, 26, 0.98); backdrop-filter: blur(14px);
          border-bottom: 1px solid var(--border);
          padding: 12px 20px 18px;
          transform: translateY(-12px); opacity: 0; pointer-events: none;
          transition: transform .22s ease, opacity .22s ease;
        }
        .links.show { transform: none; opacity: 1; pointer-events: auto; }
        .links a { padding: 12px 14px; font-size: 1rem; }
      }
    `,
  ],
})
export class NavbarComponent {
  open = signal(false);
  toggle() { this.open.update((v) => !v); }
  close() { this.open.set(false); }
}
