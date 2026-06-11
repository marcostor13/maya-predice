import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-footer',
  standalone: true,
  imports: [RouterLink],
  template: `
    <footer class="footer">
      <div class="container">
        <div class="grid">
          <div>
            <div class="brand">⚽ maya<span class="accent">predice</span></div>
            <p class="muted small">
              Predicciones estadísticas del Mundial de Fútbol 2026 con un modelo
              Dixon-Coles entrenado con histórico real.
            </p>
          </div>
          <div class="author">
            <p class="muted small">Desarrollado por</p>
            <a class="name" href="https://marcostorresalarcon.com" target="_blank" rel="noopener">
              Marcos Torres
            </a>
            <div class="socials">
              <a href="https://marcostorresalarcon.com" target="_blank" rel="noopener" title="Web">🌐</a>
              <a href="https://instagram.com/marcostorresalarcon" target="_blank" rel="noopener" title="Instagram">📸</a>
              <a href="https://www.facebook.com/marcostorresalarcon" target="_blank" rel="noopener" title="Facebook">📘</a>
              <a href="https://tiktok.com/@marcostorresalarcon" target="_blank" rel="noopener" title="TikTok">🎵</a>
            </div>
            <div class="handles muted small">
              <span>IG &#64;marcostorresalarcon</span>
              <span>FB marcos torres alarcon</span>
              <span>TikTok marcostorresalarcon</span>
            </div>
          </div>
        </div>
        <p class="disclaimer muted small">
          Las predicciones son <b>estimaciones estadísticas</b>, no consejo de apuestas.
          Contenido para mayores de <b>+18</b>. Juega con responsabilidad.
        </p>
        <div class="copy muted small">
          © {{ year }} maya-predice · Hecho con ⚽ y estadística. ·
          <a routerLink="/privacidad" class="admin-link">Privacidad</a> ·
          <a routerLink="/admin" class="admin-link">Admin</a>
        </div>
      </div>
    </footer>
  `,
  styles: [
    `
      .footer { margin-top: 60px; border-top: 1px solid var(--border); padding: 40px 0 60px; background: rgba(0,0,0,.18); }
      .grid { display: flex; justify-content: space-between; gap: 30px; flex-wrap: wrap; }
      .brand { font-family: 'Poppins'; font-weight: 800; font-size: 1.2rem; margin-bottom: 8px; }
      .accent { color: var(--primary); }
      .small { font-size: .85rem; }
      .author { text-align: right; }
      .author .name {
        font-family: 'Poppins'; font-weight: 700; font-size: 1.15rem; color: var(--text);
        display: inline-block; transition: color .2s ease;
      }
      .author .name:hover { color: var(--primary); }
      .socials { display: flex; gap: 10px; justify-content: flex-end; margin: 12px 0 8px; }
      .socials a {
        width: 40px; height: 40px; display: grid; place-items: center; font-size: 1.1rem;
        background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
        transition: transform .2s ease, background .2s ease;
      }
      .socials a:hover { transform: translateY(-3px); background: var(--surface-2); }
      .handles { display: flex; flex-direction: column; gap: 2px; }
      .disclaimer { text-align: center; margin-top: 26px; padding-top: 18px; border-top: 1px solid var(--border); }
      .copy { text-align: center; margin-top: 14px; }
      .admin-link { color: var(--muted); }
      @media (max-width: 620px) { .author { text-align: left; } .socials { justify-content: flex-start; } .handles { align-items: flex-start; } }
    `,
  ],
})
export class FooterComponent {
  year = new Date().getFullYear();
}
