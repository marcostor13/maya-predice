import { Component } from '@angular/core';
import { RouterLink, RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink],
  template: `
    <header class="topbar">
      <a routerLink="/" class="brand">⚽ maya-predice</a>
      <span class="tag">Mundial 2026</span>
    </header>
    <main class="content">
      <router-outlet />
    </main>
  `,
  styles: [
    `
      .topbar {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 16px 24px;
        background: var(--color-surface);
        border-bottom: 1px solid #2a3148;
      }
      .brand { font-weight: 700; font-size: 1.2rem; }
      .tag {
        font-size: 0.75rem;
        color: var(--color-muted);
        border: 1px solid #2a3148;
        padding: 2px 8px;
        border-radius: 999px;
      }
      .content { padding: 24px; max-width: 960px; margin: 0 auto; }
    `,
  ],
})
export class AppComponent {}
