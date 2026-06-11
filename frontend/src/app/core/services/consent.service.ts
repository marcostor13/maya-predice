import { Injectable, computed, signal } from '@angular/core';

/**
 * Consentimiento de cookies (RGPD). Los anuncios (AdSense) solo se cargan tras
 * aceptar. La elección se persiste en localStorage.
 */
@Injectable({ providedIn: 'root' })
export class ConsentService {
  private key = 'cookie_consent_v1';
  private choice = signal<'yes' | 'no' | null>(
    (localStorage.getItem(this.key) as 'yes' | 'no' | null) ?? null,
  );

  /** El usuario aceptó cookies de personalización (anuncios). */
  accepted = computed(() => this.choice() === 'yes');
  /** Ya tomó una decisión (para ocultar el banner). */
  decided = computed(() => this.choice() !== null);

  accept(): void {
    localStorage.setItem(this.key, 'yes');
    this.choice.set('yes');
  }
  reject(): void {
    localStorage.setItem(this.key, 'no');
    this.choice.set('no');
  }
}
