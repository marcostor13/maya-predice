import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

/** Política de privacidad y cookies (requisito para anuncios y afiliación). */
@Component({
  selector: 'app-privacy',
  standalone: true,
  imports: [RouterLink],
  template: `
    <div class="container page">
      <a routerLink="/" class="chip back">← Inicio</a>
      <h1>Privacidad y cookies</h1>
      <p class="muted">Última actualización: 2026</p>

      <h3>Qué es maya-predice</h3>
      <p>maya-predice ofrece <b>predicciones estadísticas</b> del Mundial 2026 calculadas
        con un modelo matemático. Las predicciones son estimaciones probabilísticas y
        <b>no constituyen consejo de apuestas</b> ni garantía de resultado.</p>

      <h3>Datos que tratamos</h3>
      <ul>
        <li><b>Suscripción por email:</b> si te suscribes, guardamos tu correo para
          enviarte el resumen de predicciones. Puedes darte de baja en cualquier
          momento con el enlace de cada email.</li>
        <li><b>Datos de navegación:</b> métricas agregadas y anónimas de uso.</li>
      </ul>

      <h3>Cookies y anuncios</h3>
      <p>Usamos cookies propias (preferencias) y, si las aceptas, de terceros para
        mostrar <b>anuncios</b> (Google AdSense) que sostienen el proyecto gratuito.
        Puedes rechazarlas en el banner; en ese caso no se cargan anuncios
        personalizados. Google puede usar cookies para personalizar anuncios según
        tu visita a este y otros sitios.</p>

      <h3>Enlaces de afiliación</h3>
      <p>Algunos enlaces salientes pueden ser de <b>afiliación</b>: si te registras a
        través de ellos podemos recibir una comisión, sin coste adicional para ti.
        Estos servicios pueden estar sujetos a regulación de juego; son solo para
        <b>mayores de 18 años</b>. Juega con responsabilidad.</p>

      <h3>Tus derechos</h3>
      <p>Puedes solicitar el acceso o la eliminación de tus datos escribiendo a
        <a href="mailto:marcostor13&#64;gmail.com">marcostor13&#64;gmail.com</a>.</p>
    </div>
  `,
  styles: [
    `
      .page { padding: 32px 20px 60px; max-width: 760px; }
      .back { display: inline-block; margin-bottom: 16px; }
      h1 { font-size: 1.9rem; margin-bottom: 6px; }
      h3 { margin: 24px 0 8px; }
      p, li { color: var(--text); line-height: 1.6; }
      ul { padding-left: 20px; }
      a { color: var(--primary); }
    `,
  ],
})
export class PrivacyComponent {}
