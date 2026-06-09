# DEPLOYMENT.md — Despliegue en producción (Coolify + Netlify)

Guía paso a paso para poner **maya-predice** en producción:

- **Backend (FastAPI) + PostgreSQL → Coolify**
- **Frontend (Angular) → Netlify**
- **CI** (lint + tests + build) → GitHub Actions (`.github/workflows/ci.yml`)

```
   Navegador ──HTTPS──▶ Netlify (Angular)  ──HTTPS/REST──▶ Coolify (FastAPI) ──▶ PostgreSQL
```

> Nota: despliega desde tu rama de producción (p. ej. `main`). Haz merge de la
> rama de desarrollo a `main` antes de conectar los servicios, o apunta cada
> servicio a la rama que prefieras.

---

## 0. Requisitos previos

- Una instancia de **Coolify** funcionando (servidor propio o VPS) con acceso a internet.
- Cuenta de **Netlify** conectada a GitHub.
- El repositorio en GitHub (`marcostor13/maya-predice`).
- Un dominio (opcional pero recomendado), p. ej. `maya-predice.com` y `api.maya-predice.com`.
- (Opcional) credenciales SMTP para enviar emails (ver §4).

---

## 1. Backend + Base de datos en Coolify

### 1.1 Crear la base de datos PostgreSQL
1. En Coolify: **+ New → Database → PostgreSQL** (versión 16).
2. Nombre: `maya-db`. Crea la base `maya_predice`.
3. Al crearla, Coolify te da la **cadena de conexión interna**, algo como:
   `postgres://USER:PASSWORD@maya-db:5432/maya_predice`
4. Guárdala: la usarás como `DATABASE_URL` (cambiando el esquema a `postgresql+asyncpg://`).

### 1.2 Crear la aplicación backend
1. **+ New → Application → desde el repositorio Git** (`marcostor13/maya-predice`).
2. **Branch:** `main` (o tu rama de producción).
3. **Build Pack:** *Dockerfile*.
4. **Base Directory / Dockerfile location:** `backend` (el `Dockerfile` está en `backend/Dockerfile`).
5. **Puerto expuesto:** `8000`.
6. **Health check path:** `/health` (la API responde `{"status":"ok"}`).
7. **Watch Paths (importante):** en la app → *General/Advanced* pon `backend/**`.
   Así Coolify **solo redepliega el backend cuando cambian archivos de `backend/`**
   (no en pushes que solo tocan el frontend). Activa también **Auto Deploy**.

> El `Dockerfile` ya ejecuta `alembic upgrade head` antes de arrancar Gunicorn,
> así que **las migraciones se aplican solas** en cada despliegue.

### 1.3 Variables de entorno del backend
En la app de Coolify → **Environment Variables**, añade:

```bash
# Base de datos (driver async). Usa el host interno de tu PostgreSQL de Coolify.
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@maya-db:5432/maya_predice

ENV=production
# Orígenes permitidos: la URL pública de tu frontend en Netlify (sin / final)
CORS_ORIGINS=https://maya-predice.netlify.app

# Modelo / entrenamiento
MODEL_VERSION=dixon-coles-v1
HISTORY_TEAM_FILTER=both        # both = rápido; any = más datos
ELO_PRIOR_WEIGHT=0.5

# Verificación diaria y actualización en vivo
ENABLE_SCHEDULER=true
SYNC_HOUR_UTC=6                 # refresco completo diario (UTC)
ENABLE_LIVE_UPDATES=true
LIVE_POLL_MINUTES=30            # durante el torneo, recálculo cada 30 min

# Fuentes de plantillas (consenso). Requieren claves; ver más abajo.
PLAYER_SOURCES=apifootball,thesportsdb,wikidata
APIFOOTBALL_KEY=tu_api_key
THESPORTSDB_KEY=3

# Email a suscriptores (ver §4). Déjalo en false hasta configurar SMTP.
NOTIFICATIONS_ENABLED=false
SITE_URL=https://maya-predice.netlify.app
```

> **Internet saliente:** la instancia de Coolify tiene salida a internet normal,
> así que las fuentes (openfootball, martj42, API-Football, TheSportsDB, Wikidata)
> son accesibles con solo poner sus claves. Si tu servidor tiene firewall de
> salida, permite esos hosts. (El sandbox de desarrollo sí tenía allowlist; producción no.)

### 1.4 Dominio y HTTPS
1. En la app → **Domains**: añade `https://api.maya-predice.com` (o usa el dominio
   que Coolify asigna). Coolify gestiona el certificado TLS (Let's Encrypt).
2. Apunta el DNS `api` (registro A/CNAME) al servidor de Coolify.

### 1.5 Desplegar y verificar
1. Pulsa **Deploy**. Espera a que el build termine y el health check quede verde.
2. Comprueba:
   ```bash
   curl https://api.maya-predice.com/health
   # {"status":"ok","env":"production","model_version":"dixon-coles-v1"}
   curl https://api.maya-predice.com/docs   # Swagger UI
   ```

### 1.6 Carga inicial de datos (una sola vez)
Abre la **terminal** de la app en Coolify (o un *Command/Exec*) y ejecuta:
```bash
python -m app.data.seed          # crea el torneo + las 48 selecciones
python -m app.data.sync          # ingiere los 104 partidos oficiales
python -m app.data.sync_squads   # plantillas (consenso de las fuentes activas)
python -m app.data.train         # entrena el modelo y guarda fuerzas
# Genera la primera simulación (o llama al endpoint):
curl -X POST https://api.maya-predice.com/api/v1/simulate/run
```
A partir de aquí, el **scheduler interno** mantiene todo al día (refresco diario +
recálculo en vivo cada `LIVE_POLL_MINUTES`). No necesitas cron externo.

> Alternativa con cron externo: pon `ENABLE_SCHEDULER=false` y programa en Coolify
> `python -m app.data.recompute` (cada 30 min) y `python -m app.data.sync_squads`
> + `python -m app.data.notify` (1×/día).

---

## 2. Frontend en Netlify

### 2.1 Apuntar el frontend al backend
Edita `frontend/src/environments/environment.prod.ts` y pon la URL pública del backend:
```ts
export const environment = {
  production: true,
  apiBaseUrl: 'https://api.maya-predice.com/api/v1',
};
```
Commit y push (Netlify reconstruye al detectar el cambio).

### 2.2 Crear el sitio en Netlify
1. **Add new site → Import an existing project → GitHub** → `marcostor13/maya-predice`.
2. Netlify detecta `frontend/netlify.toml`, que ya define:
   - **Base directory:** `frontend/`
   - **Build command:** `npm install --no-audit --no-fund && npm run build`
   - **Publish directory:** `dist/maya-predice/browser`
   - Redirección SPA a `index.html` (rutas de Angular).
   - **`ignore`:** cancela el build si el push **no tocó `frontend/`** (despliega
     el frontend solo cuando hay cambios de frontend).
3. **Branch to deploy:** `main`.
4. Pulsa **Deploy**. Netlify te da una URL `https://<algo>.netlify.app`.

### 2.3 Dominio
- En Netlify → **Domain settings**: añade tu dominio (`maya-predice.com`) y sigue
  las instrucciones de DNS. Netlify emite el certificado TLS automáticamente.

### 2.4 Cerrar el círculo con CORS
- Asegúrate de que `CORS_ORIGINS` en el backend (Coolify) incluye **exactamente**
  la URL del frontend (con `https://`, sin `/` final). Si usas varios dominios,
  sepáralos por coma. Re-despliega el backend tras cambiarlo.

---

## 3. CI/CD (integración y despliegue continuos)

**Despliegue por rutas (clave):** cada push a `main` despliega **solo lo que
cambió** — el frontend a Netlify solo si hubo cambios en `frontend/`, y el backend
a Coolify solo si hubo cambios en `backend/`.

### CI — GitHub Actions (filtrado por rutas)
Dos workflows independientes, cada uno con `paths`:
- `.github/workflows/backend.yml` → corre **solo si cambia `backend/**`**: `ruff` + `pytest`.
- `.github/workflows/frontend.yml` → corre **solo si cambia `frontend/**`**: `npm install` + `build`.

### CD — automático por Git (filtrado por rutas)
- **Coolify (backend):** **Auto Deploy** + **Watch Paths = `backend/**`** → solo
  redepliega cuando cambian archivos del backend.
- **Netlify (frontend):** el `ignore` de `netlify.toml`
  (`git diff --quiet HEAD^ HEAD -- .`) **cancela el build si el push no tocó
  `frontend/`**; despliega solo ante cambios de frontend.

Flujo recomendado: trabajar en una rama → PR (los checks que aplican validan) →
merge a `main` → cada servicio despliega solo si le corresponde.

---

## 4. Emails a suscriptores (SMTP)

El envío está implementado (`services/notifications.py`): tras el refresco diario,
si hubo resultados, manda un *digest* (resultados, favoritos al título y próximos
partidos con pronóstico) a los suscriptores activos.

1. Elige un proveedor SMTP. Opciones:
   - **Resend / SendGrid / Mailgun / Brevo** (recomendado en producción).
   - **Gmail** con *App Password* (para pruebas/bajo volumen).
2. En el backend (Coolify) añade:
   ```bash
   NOTIFICATIONS_ENABLED=true
   SMTP_HOST=smtp.tu-proveedor.com
   SMTP_PORT=587
   SMTP_USER=tu_usuario_o_apikey
   SMTP_PASSWORD=tu_password_o_apikey
   SMTP_FROM=maya-predice <no-reply@tudominio.com>
   SMTP_START_TLS=true     # puerto 587 (STARTTLS)
   SMTP_USE_TLS=false      # pon true y SMTP_PORT=465 si tu proveedor usa SSL directo
   SITE_URL=https://maya-predice.com
   ```
3. Re-despliega. Prueba el envío manual desde la terminal de Coolify:
   ```bash
   python -m app.data.notify --force
   ```
4. **Entregabilidad:** configura SPF/DKIM del dominio en tu proveedor para no caer
   en spam. Usa un `SMTP_FROM` con tu dominio verificado.

---

## 5. Checklist de salida a producción

- [ ] PostgreSQL creado en Coolify; `DATABASE_URL` con `postgresql+asyncpg://`.
- [ ] Backend desplegado; `/health` y `/docs` responden por HTTPS.
- [ ] Carga inicial ejecutada (seed, sync, squads, train, simulate).
- [ ] `CORS_ORIGINS` = URL del frontend; backend re-desplegado.
- [ ] `environment.prod.ts` apunta a la URL del backend; frontend desplegado.
- [ ] Claves de fuentes (`APIFOOTBALL_KEY`…) cargadas; `PLAYER_SOURCES` activo.
- [ ] `LIVE_POLL_MINUTES` ajustado para el torneo (p. ej. 30).
- [ ] (Opcional) SMTP configurado y `NOTIFICATIONS_ENABLED=true`; envío probado.
- [ ] Auto-deploy activo en Coolify y Netlify.

---

## 6. Troubleshooting

| Síntoma | Causa probable | Solución |
|---|---|---|
| Frontend carga pero sin datos | CORS o URL del backend mal | Revisa `CORS_ORIGINS` y `apiBaseUrl`. |
| 502/health rojo en Coolify | Migración falló o DB inaccesible | Revisa logs; valida `DATABASE_URL` (host interno + `+asyncpg`). |
| Predicciones vacías | Falta entrenar/simular | Ejecuta `python -m app.data.train` y `POST /simulate/run`. |
| Plantillas vacías | Sin claves o `PLAYER_SOURCES=fixture` | Pon claves reales y `PLAYER_SOURCES=apifootball,thesportsdb,wikidata`. |
| No llegan emails | SMTP mal o `NOTIFICATIONS_ENABLED=false` | Revisa credenciales y SPF/DKIM; prueba `python -m app.data.notify --force`. |
| Rutas dan 404 al recargar en Netlify | Falta redirección SPA | Ya está en `netlify.toml`; confirma el publish dir. |
