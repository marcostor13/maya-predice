import { Injectable, computed, signal } from '@angular/core';

declare global {
  interface Window {
    gtag?: (...args: unknown[]) => void;
  }
}

/**
 * Consentimiento de cookies (RGPD). Los anuncios (AdSense) y la analítica
 * (Google Analytics) solo se activan tras aceptar. La elección se persiste en
 * localStorage y se propaga al Consent Mode v2 de Google.
 */
@Injectable({ providedIn: 'root' })
export class ConsentService {
  private key = 'cookie_consent_v1';
  private choice = signal<'yes' | 'no' | null>(
    (localStorage.getItem(this.key) as 'yes' | 'no' | null) ?? null,
  );

  constructor() {
    // Si ya había una decisión previa, refléjala en Consent Mode al arrancar.
    if (this.choice() !== null) {
      this.updateConsent(this.choice() === 'yes' ? 'granted' : 'denied');
    }
  }

  /** El usuario aceptó cookies de personalización (anuncios). */
  accepted = computed(() => this.choice() === 'yes');
  /** Ya tomó una decisión (para ocultar el banner). */
  decided = computed(() => this.choice() !== null);

  accept(): void {
    localStorage.setItem(this.key, 'yes');
    this.choice.set('yes');
    this.updateConsent('granted');
  }
  reject(): void {
    localStorage.setItem(this.key, 'no');
    this.choice.set('no');
    this.updateConsent('denied');
  }

  /** Propaga la elección al Consent Mode v2 de Google (gtag), si está cargado. */
  private updateConsent(value: 'granted' | 'denied'): void {
    window.gtag?.('consent', 'update', {
      ad_storage: value,
      analytics_storage: value,
      ad_user_data: value,
      ad_personalization: value,
    });
  }
}
