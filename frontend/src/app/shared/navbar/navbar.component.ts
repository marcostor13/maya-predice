import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [RouterLink, RouterLinkActive],
  template: `
    <nav class="nav">
      <div class="container inner">
        <a routerLink="/" class="brand">
          <span class="ball floaty">⚽</span>
          <span class="name">maya<span class="accent">predice</span></span>
          <span class="chip wc">Mundial 2026</span>
        </a>
        <div class="links">
          <a routerLink="/" routerLinkActive="active" [routerLinkActiveOptions]="{ exact: true }">Inicio</a>
          <a routerLink="/fixture" routerLinkActive="active">Fixture</a>
          <a routerLink="/equipos" routerLinkActive="active">Equipos</a>
          <a routerLink="/simulacion" routerLinkActive="active">Simulación</a>
        </div>
      </div>
    </nav>
  `,
  styles: [
    `
      .nav {
        position: sticky; top: 0; z-index: 50;
        background: rgba(10, 14, 26, 0.72); backdrop-filter: blur(14px);
        border-bottom: 1px solid var(--border);
      }
      .inner { display: flex; align-items: center; justify-content: space-between; height: 66px; }
      .brand { display: flex; align-items: center; gap: 10px; font-family: 'Poppins'; font-weight: 800; font-size: 1.25rem; color: var(--text); }
      .ball { font-size: 1.4rem; display: inline-block; }
      .accent { color: var(--primary); }
      .chip.wc { background: linear-gradient(135deg, rgba(167,139,250,.25), rgba(45,212,191,.25)); color: var(--text); border-color: transparent; }
      .links { display: flex; gap: 6px; flex-wrap: wrap; }
      .links a {
        color: var(--muted); font-weight: 600; padding: 8px 14px; border-radius: 999px;
        transition: all .2s ease; font-size: .92rem;
      }
      .links a:hover { color: var(--text); background: var(--surface); }
      .links a.active { color: #04241d; background: linear-gradient(135deg, var(--primary), var(--primary-2)); }
      @media (max-width: 620px) {
        .chip.wc { display: none; }
        .links a { padding: 8px 10px; }
      }
    `,
  ],
})
export class NavbarComponent {}
