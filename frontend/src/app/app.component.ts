import { Component, inject } from '@angular/core';
import { ActivatedRoute, NavigationEnd, Router, RouterOutlet } from '@angular/router';
import { filter } from 'rxjs/operators';

import { ConfigService } from './core/services/config.service';
import { SeoData, SeoService } from './core/services/seo.service';
import { ConsentBannerComponent } from './shared/consent-banner/consent-banner.component';
import { FooterComponent } from './shared/footer/footer.component';
import { NavbarComponent } from './shared/navbar/navbar.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, NavbarComponent, FooterComponent, ConsentBannerComponent],
  template: `
    <app-navbar />
    <main>
      <router-outlet />
    </main>
    <app-footer />
    <app-consent-banner />
  `,
  styles: [`main { min-height: 70vh; }`],
})
export class AppComponent {
  private router = inject(Router);
  private route = inject(ActivatedRoute);
  private seo = inject(SeoService);

  constructor() {
    // Carga la config pública (afiliado) una sola vez al arrancar.
    inject(ConfigService).load();

    // Actualiza título/description/canonical en cada navegación (SEO por ruta).
    this.router.events
      .pipe(filter((e): e is NavigationEnd => e instanceof NavigationEnd))
      .subscribe(() => {
        let r = this.route;
        while (r.firstChild) r = r.firstChild;
        const seo = r.snapshot.data['seo'] as SeoData | undefined;
        if (seo) this.seo.update(seo);
      });
  }
}
