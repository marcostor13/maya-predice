import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';

import { environment } from '../../../environments/environment';

export interface AffiliateConfig {
  enabled: boolean;
  url: string;
  label: string;
}

/** Configuración pública del sitio (afiliado). Se carga una vez al arrancar. */
@Injectable({ providedIn: 'root' })
export class ConfigService {
  private http = inject(HttpClient);
  private base = environment.apiBaseUrl;
  affiliate = signal<AffiliateConfig | null>(null);

  load(): void {
    this.http.get<{ affiliate: AffiliateConfig }>(`${this.base}/config`).subscribe({
      next: (c) => this.affiliate.set(c.affiliate ?? null),
      error: () => this.affiliate.set(null),
    });
  }
}
