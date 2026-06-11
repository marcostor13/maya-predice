import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { ConfigService } from './core/services/config.service';
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
  constructor() {
    // Carga la config pública (afiliado) una sola vez al arrancar.
    inject(ConfigService).load();
  }
}
