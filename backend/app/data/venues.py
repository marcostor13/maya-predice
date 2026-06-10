"""Catálogo de las 16 sedes del Mundial 2026 (estadio, ciudad, país, aforo).

Mapea el nombre de sede que entrega el calendario oficial (openfootball, p.ej.
"Mexico City", "New York/New Jersey (East Rutherford)") a su información completa.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Venue:
    stadium: str
    city: str
    country: str
    capacity: int


# clave = valor de `ground` del calendario oficial
VENUES: dict[str, Venue] = {
    "Atlanta": Venue("Mercedes-Benz Stadium", "Atlanta", "Estados Unidos", 71000),
    "Boston (Foxborough)": Venue("Gillette Stadium", "Foxborough", "Estados Unidos", 65000),
    "Dallas (Arlington)": Venue("AT&T Stadium", "Arlington", "Estados Unidos", 80000),
    "Guadalajara (Zapopan)": Venue("Estadio Akron", "Guadalajara", "México", 49000),
    "Houston": Venue("NRG Stadium", "Houston", "Estados Unidos", 72000),
    "Kansas City": Venue("Arrowhead Stadium", "Kansas City", "Estados Unidos", 76000),
    "Los Angeles (Inglewood)": Venue("SoFi Stadium", "Inglewood", "Estados Unidos", 70000),
    "Mexico City": Venue("Estadio Azteca", "Ciudad de México", "México", 83000),
    "Miami (Miami Gardens)": Venue("Hard Rock Stadium", "Miami Gardens", "Estados Unidos", 65000),
    "Monterrey (Guadalupe)": Venue("Estadio BBVA", "Guadalupe", "México", 53000),
    "New York/New Jersey (East Rutherford)": Venue(
        "MetLife Stadium", "East Rutherford", "Estados Unidos", 82500
    ),
    "Philadelphia": Venue("Lincoln Financial Field", "Philadelphia", "Estados Unidos", 69000),
    "San Francisco Bay Area (Santa Clara)": Venue(
        "Levi's Stadium", "Santa Clara", "Estados Unidos", 70000
    ),
    "Seattle": Venue("Lumen Field", "Seattle", "Estados Unidos", 69000),
    "Toronto": Venue("BMO Field", "Toronto", "Canadá", 45000),
    "Vancouver": Venue("BC Place", "Vancouver", "Canadá", 54000),
}


def lookup(ground: str | None) -> Venue | None:
    return VENUES.get(ground) if ground else None
