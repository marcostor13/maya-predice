import {
  animate,
  query,
  stagger,
  style,
  transition,
  trigger,
} from '@angular/animations';

// Entrada suave de un elemento.
export const fadeIn = trigger('fadeIn', [
  transition(':enter', [
    style({ opacity: 0, transform: 'translateY(14px)' }),
    animate('.5s cubic-bezier(.2,.7,.2,1)', style({ opacity: 1, transform: 'none' })),
  ]),
]);

// Aparición escalonada de una lista (aplicar al contenedor con *ngIf/@for dentro).
export const listStagger = trigger('listStagger', [
  transition(':enter, * => *', [
    query(
      ':enter',
      [
        style({ opacity: 0, transform: 'translateY(18px) scale(.98)' }),
        stagger(60, [
          animate(
            '.5s cubic-bezier(.2,.7,.2,1)',
            style({ opacity: 1, transform: 'none' }),
          ),
        ]),
      ],
      { optional: true },
    ),
  ]),
]);
