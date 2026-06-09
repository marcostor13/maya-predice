import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./features/dashboard/dashboard.component').then((m) => m.DashboardComponent),
  },
  {
    path: 'match/:id',
    loadComponent: () =>
      import('./features/match-detail/match-detail.component').then(
        (m) => m.MatchDetailComponent,
      ),
  },
  { path: '**', redirectTo: '' },
];
