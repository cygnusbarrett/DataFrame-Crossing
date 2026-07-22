"""Extracción de códigos de causa judicial tipo xx-yy (p.ej. 15-75 → 1975)."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Códigos frecuentes: 15-75, 015-75, 15-1975, a veces con prefijos/sufijos.
CAUSA_RE = re.compile(
    r"(?<!\d)(?P<num>\d{1,4})\s*[-_/]\s*(?P<yy>\d{2}|\d{4})(?!\d)",
    re.IGNORECASE,
)

# Años plausibles para consejos de guerra / dictadura chilena (amplio).
YEAR_MIN = 1970
YEAR_MAX = 1990


@dataclass(frozen=True, slots=True)
class CausaCode:
    numero: int
    year: int
    raw: str

    @property
    def label(self) -> str:
        return f"{self.numero}-{self.year % 100:02d}"


def yy_to_year(yy: int) -> int | None:
    """Convierte yy de 2 o 4 dígitos a año completo."""
    if yy >= 1000:
        year = yy
    else:
        # Convención del dominio: 70–99 → 1970–1999; 00–69 → 2000–2069 (poco probable aquí).
        year = 1900 + yy if yy >= 70 else 2000 + yy
    if YEAR_MIN <= year <= YEAR_MAX:
        return year
    # Fuera de ventana estricta pero aún siglo XX dictatorial-ampliado
    if 1960 <= year <= 2000:
        return year
    return None


def extract_causa_codes(text: str) -> list[CausaCode]:
    """Extrae todos los códigos de causa plausibles desde un nombre de archivo/carpeta."""
    found: list[CausaCode] = []
    seen: set[tuple[int, int]] = set()
    for m in CAUSA_RE.finditer(text):
        num = int(m.group("num"))
        yy_raw = int(m.group("yy"))
        year = yy_to_year(yy_raw)
        if year is None:
            continue
        key = (num, year)
        if key in seen:
            continue
        seen.add(key)
        found.append(CausaCode(numero=num, year=year, raw=m.group(0)))
    return found


def primary_causa_code(text: str) -> CausaCode | None:
    codes = extract_causa_codes(text)
    return codes[0] if codes else None
