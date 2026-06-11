import { Routes } from '@angular/router';

import { SeoData } from './core/services/seo.service';

export const routes: Routes = [
  {
    path: '',
    data: {
      seo: {
        title: 'maya-predice · Predicciones del Mundial 2026 con IA',
        description:
          'Predicciones del Mundial de Fútbol 2026 con un modelo estadístico: probabilidades de cada partido, simulador de campeón y resultados en vivo.',
        path: '/',
      } satisfies SeoData,
    },
    loadComponent: () =>
      import('./features/dashboard/dashboard.component').then((m) => m.DashboardComponent),
  },
  {
    path: 'en-vivo',
    data: {
      seo: {
        title: 'Resultados en vivo del Mundial 2026 · Marcadores en directo',
        description:
          'Sigue los partidos del Mundial 2026 EN VIVO: marcador en directo minuto a minuto, resultados de hoy y predicciones del modelo. Se actualiza solo cada 2 minutos.',
        path: '/en-vivo',
      } satisfies SeoData,
    },
    loadComponent: () =>
      import('./features/live/live.component').then((m) => m.LiveComponent),
  },
  {
    path: 'fixture',
    data: {
      seo: {
        title: 'Calendario y resultados del Mundial 2026',
        description:
          'Todos los partidos del Mundial 2026 con horarios, resultados y la predicción 1X2 del modelo para cada encuentro.',
        path: '/fixture',
      } satisfies SeoData,
    },
    loadComponent: () =>
      import('./features/fixture/fixture.component').then((m) => m.FixtureComponent),
  },
  {
    path: 'equipos',
    data: {
      seo: {
        title: 'Selecciones del Mundial 2026',
        description:
          'Las 48 selecciones clasificadas al Mundial 2026: plantillas, entrenadores y fuerza del equipo según el modelo.',
        path: '/equipos',
      } satisfies SeoData,
    },
    loadComponent: () =>
      import('./features/teams/teams.component').then((m) => m.TeamsComponent),
  },
  {
    path: 'equipos/:code',
    data: {
      seo: {
        title: 'Plantilla y predicciones de la selección',
        description:
          'Plantilla, entrenador y predicciones de la selección en el Mundial 2026 según el modelo estadístico.',
        path: '/equipos',
      } satisfies SeoData,
    },
    loadComponent: () =>
      import('./features/team-detail/team-detail.component').then((m) => m.TeamDetailComponent),
  },
  {
    path: 'simulacion',
    data: {
      seo: {
        title: 'Simulador del Mundial 2026: ¿quién será campeón?',
        description:
          'Simulación Monte Carlo del Mundial 2026: probabilidades de avanzar de fase y de ganar el título para cada selección.',
        path: '/simulacion',
      } satisfies SeoData,
    },
    loadComponent: () =>
      import('./features/simulation/simulation.component').then((m) => m.SimulationComponent),
  },
  {
    path: 'admin',
    data: { seo: { title: 'Panel de administración', description: 'Panel privado.', path: '/admin' } satisfies SeoData },
    loadComponent: () =>
      import('./features/admin/admin.component').then((m) => m.AdminComponent),
  },
  {
    path: 'privacidad',
    data: {
      seo: {
        title: 'Política de privacidad y cookies',
        description: 'Cómo tratamos los datos, las cookies y la publicidad en maya-predice.',
        path: '/privacidad',
      } satisfies SeoData,
    },
    loadComponent: () =>
      import('./features/privacy/privacy.component').then((m) => m.PrivacyComponent),
  },
  { path: '**', redirectTo: '' },
];
