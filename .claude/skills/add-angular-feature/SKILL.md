---
name: add-angular-feature
description: Crea una nueva feature (componente standalone + servicio + ruta) en el frontend Angular 18 de maya-predice usando signals y la convención del proyecto. Usa esta skill cuando se pida una nueva pantalla o sección en el frontend.
---

# Añadir una feature Angular

Convención de maya-predice: Angular 18 standalone + signals.

## 1. Modelos
Si la feature usa datos nuevos, añade las interfaces en
`frontend/src/app/core/models/index.ts`.

## 2. Servicio
Si consume el backend, añade el método al `ApiService`
(`core/services/api.service.ts`) usando `HttpClient` y `environment.apiBaseUrl`.
No hardcodees URLs en el componente.

## 3. Componente standalone
Crea `frontend/src/app/features/<feature>/<feature>.component.ts`:

```ts
@Component({
  selector: 'app-<feature>',
  standalone: true,
  imports: [CommonModule, /* ... */],
  template: `...`,
  styles: [`...`],
})
export class <Feature>Component {
  private api = inject(ApiService);
  data = signal<Tipo[]>([]);
  // carga en el constructor o con un método
}
```

- Estado con `signal()`. Inyección con `inject()`.
- Estilos SCSS usando las variables CSS de `styles.scss`.
- Usa la sintaxis de control flow `@if` / `@for` (track obligatorio).

## 4. Ruta
Regístrala con lazy loading en `frontend/src/app/app.routes.ts`:

```ts
{ path: 'ruta', loadComponent: () =>
    import('./features/<feature>/<feature>.component').then(m => m.<Feature>Component) }
```

## Checklist
- [ ] Tipos en core/models.
- [ ] Método en ApiService (si aplica), URL desde environment.
- [ ] Componente standalone con signals, sin `any`.
- [ ] Ruta lazy registrada.
- [ ] `npm run build` sin errores.
