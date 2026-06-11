# MONETIZATION.md — Cómo monetizar maya-predice

> Análisis de vías de ingreso para la plataforma de predicciones del Mundial 2026,
> con estimaciones, esfuerzo, plazos y consideraciones legales. Lo **implementado**
> en el código va marcado ✅; el resto es hoja de ruta.

---

## 1. Contexto y ventana de oportunidad

- **El Mundial 2026 es el evento**: el tráfico se concentra en ~6 semanas (jun–jul).
  Hay que tener la monetización **lista desde el primer partido**.
- **Coste de operación ≈ 0** (Netlify free + Coolify): casi todo ingreso es margen.
- **Activos que ya tenemos**: predicciones frescas cada hora (bueno para SEO),
  lista de **suscriptores por email** (digest diario), panel admin con
  **configuración editable en caliente** (cambiar campañas sin redeploy).
- **Audiencia**: aficionados que buscan "quién gana", cuotas y pronósticos →
  encaja con publicidad display y con afiliación de casas de apuestas.

---

## 2. Vías evaluadas (resumen)

| Vía | Ingreso potencial | Esfuerzo | Plazo | Estado |
|---|---|---|---|---|
| **Anuncios display (AdSense)** | Medio (CPM ~1–4 €/1.000 vistas) | Bajo | Días (aprobación) | ✅ integrado |
| **Afiliación de apuestas** | **Alto** (CPA ~30–200 €/registro) | Bajo-medio | Días (alta en red) | ✅ integrado (CTA editable) |
| **Suscripción premium (Stripe)** | Medio-alto recurrente | Alto (login + pagos) | 1–2 semanas | Futuro (§5) |
| **Venta de la API** | Medio recurrente, **duradero** | Medio | 1–2 semanas | Futuro (§5) |
| **Newsletter patrocinada** | Bajo-medio | Bajo (ya hay lista) | Días | Futuro (§5) |
| **Donaciones (Ko-fi)** | Bajo | Muy bajo | Horas | Futuro (§5) |
| **Widget/B2B para medios** | Medio (licencia) | Medio | Post-Mundial | Futuro (§5) |

> **Estrategia recomendada para el torneo:** combinar **AdSense** (ingreso pasivo
> por toda visita) + **afiliación de apuestas** (el mayor ingreso por usuario en
> este nicho). Tras el Mundial, la **API** es el activo que sigue generando.

---

## 3. Lo implementado en el código ✅

### 3.1 Anuncios — Google AdSense
- Componente `shared/ad-slot` que pinta un bloque de anuncio **solo si** hay
  `adsenseClient` configurado (en `environments/environment*.ts`) **y** el usuario
  aceptó cookies. Sin configurar → no carga nada (el sitio queda idéntico).
- **Banner de consentimiento** (`shared/consent-banner`) + servicio
  `core/services/consent.service.ts` (RGPD: los anuncios solo cargan tras aceptar).
- **`/privacidad`** (`features/privacy`) y enlace en el footer.
- **`ads.txt`** servido en la raíz (`frontend/src/static/ads.txt` → `angular.json`).
- Slots colocados en **dashboard** y **fixture** (ampliable a equipos/simulación).

**Para activarlo:** crea la cuenta en AdSense, espera la aprobación (días), pega tu
`pub-id` en `adsenseClient` (los dos `environment*.ts`) y en `ads.txt`. Redeploy.

### 3.2 Afiliación de apuestas — CTA editable
- Ajustes nuevos (grupo **Monetización** del panel ⚙️ Configuración):
  `affiliate_enabled`, `affiliate_url`, `affiliate_label`. Se cambian **sin
  redeploy** (overrides en `app_settings`).
- Endpoint **público** `GET /api/v1/config` → `{affiliate:{enabled,url,label}}`
  (nunca expone secretos; si está desactivado, no devuelve la URL).
- Componente `shared/affiliate-cta`: botón "Compara las cuotas en {casa}" con
  `rel="sponsored noopener nofollow"`, visible solo si está activo. Incluye el aviso
  **+18 / juego responsable**. Colocado en dashboard y fixture.
- **Cumplimiento**: disclaimer permanente en el footer ("estimaciones estadísticas,
  no consejo de apuestas; +18; juega con responsabilidad").

**Para activarlo:** date de alta en una red/programa de afiliados (ver §4), pega tu
URL con tu tag en el panel admin y actívalo. Aparece al instante.

---

## 4. Afiliación de apuestas — cómo dar de alta (acción del usuario)

1. **Elige programa según tu mercado** (España/México/LatAm): p. ej. Bet365
   Partners, Betsson Group Affiliates, Codere, Betano, redes como Income Access o
   RevenueLab. Modelos: **CPA** (pago por registro/depósito), **revenue share**
   (% de por vida) o híbrido.
2. **Regístrate**, te dan un **enlace con tu tracker** (p. ej.
   `https://casa.com/?btag=TU_ID`).
3. Pégalo en **Admin → ⚙️ Configuración → Monetización** (`affiliate_url`), pon el
   nombre (`affiliate_label`) y activa `affiliate_enabled`.
4. **Antes de activar**, revisa la **regulación de juego** del país objetivo: en
   España (DGOJ) y varios países de LatAm la publicidad de apuestas está
   **restringida** (horarios, +18, advertencias, a veces licencia del afiliado). No
   muestres el CTA donde no esté permitido.

---

## 5. Hoja de ruta de ingresos (futuro)

- **Premium con Stripe**: nivel gratis (1X2 básico) vs. pago (marcadores exactos,
  simulaciones detalladas, *picks* por email, sin anuncios). Requiere login de
  usuarios + Stripe Checkout/webhooks. El mayor ingreso **recurrente**.
- **Venta de la API**: exponer las predicciones con API keys + límites (RapidAPI o
  directo). Es el activo que **sobrevive al Mundial** y sirve para otras ligas.
- **Newsletter patrocinada**: ya hay lista de suscriptores; vender el patrocinio del
  digest a una marca.
- **Donaciones** (Ko-fi / Buy Me a Coffee): botón en el footer, ingreso modesto e
  inmediato.
- **B2B / widget**: licenciar un widget de predicciones a medios deportivos.

---

## 6. Consideraciones legales (importante)

- **Juego (+18):** la afiliación de apuestas está regulada y varía por país. Añade
  siempre +18, juego responsable y respeta restricciones locales. Ya hay disclaimer
  global; desactiva el CTA en jurisdicciones donde no proceda.
- **No es consejo de apuestas:** mantener el aviso de que son estimaciones
  estadísticas (ya en el footer y en /privacidad).
- **RGPD / cookies:** AdSense usa cookies de terceros → banner de consentimiento
  (implementado) + política de privacidad (implementada). En la UE, los anuncios no
  personalizados requieren consentimiento explícito.
- **Fiscalidad:** declara los ingresos de afiliación/publicidad según tu país.
