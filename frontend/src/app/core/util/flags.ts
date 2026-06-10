// Mapa código FIFA -> ISO 3166-1 alpha-2 (o subdivisión) para flagcdn.com.
// Se usan imágenes de bandera porque los emoji de bandera no se renderizan en
// Windows ni en algunos navegadores.
const ISO: Record<string, string> = {
  ALG: 'dz', ARG: 'ar', AUS: 'au', AUT: 'at', BEL: 'be', BIH: 'ba', BRA: 'br',
  CAN: 'ca', CPV: 'cv', COL: 'co', CRO: 'hr', CUW: 'cw', CZE: 'cz', COD: 'cd',
  ECU: 'ec', EGY: 'eg', ENG: 'gb-eng', FRA: 'fr', GER: 'de', GHA: 'gh', HAI: 'ht',
  IRN: 'ir', IRQ: 'iq', CIV: 'ci', JPN: 'jp', JOR: 'jo', MEX: 'mx', MAR: 'ma',
  NED: 'nl', NZL: 'nz', NOR: 'no', PAN: 'pa', PAR: 'py', POR: 'pt', QAT: 'qa',
  KSA: 'sa', SCO: 'gb-sct', SEN: 'sn', RSA: 'za', KOR: 'kr', ESP: 'es', SWE: 'se',
  SUI: 'ch', TUN: 'tn', TUR: 'tr', USA: 'us', URU: 'uy', UZB: 'uz',
};

/** URL de la bandera (SVG) para un código FIFA, o null si es placeholder/desconocido. */
export function flagUrl(code?: string): string | null {
  if (!code) return null;
  const iso = ISO[code.toUpperCase()];
  return iso ? `https://flagcdn.com/${iso}.svg` : null;
}
