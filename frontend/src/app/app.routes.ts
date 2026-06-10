import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./features/dashboard/dashboard.component').then((m) => m.DashboardComponent),
  },
  {
    path: 'fixture',
    loadComponent: () =>
      import('./features/fixture/fixture.component').then((m) => m.FixtureComponent),
  },
  {
    path: 'equipos',
    loadComponent: () =>
      import('./features/teams/teams.component').then((m) => m.TeamsComponent),
  },
  {
    path: 'equipos/:code',
    loadComponent: () =>
      import('./features/team-detail/team-detail.component').then((m) => m.TeamDetailComponent),
  },
  {
    path: 'simulacion',
    loadComponent: () =>
      import('./features/simulation/simulation.component').then((m) => m.SimulationComponent),
  },
  {
    path: 'admin',
    loadComponent: () =>
      import('./features/admin/admin.component').then((m) => m.AdminComponent),
  },
  { path: '**', redirectTo: '' },
];
