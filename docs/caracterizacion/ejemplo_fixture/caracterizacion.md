# Caracterización preliminar — Consejos de Guerra

**Raíz:** `/workspace/tests/fixtures/consejos_guerra_mini`

Archivos: **11** · Carpetas: **11** · Causas únicas (por código xx-yy en nombres): **5**

## Causas judiciales por año

| Año | N° causas (únicas) |
| ---: | ---: |
| 1974 | 1 |
| 1975 | 1 |
| 1976 | 1 |
| 1978 | 1 |
| 1979 | 1 |

## Fondos

### Fondo Alicia

- Ruta relativa: `Fondos/Fondo Alicia`
- Archivos: 3 · dirs: 2 · causas únicas: 2
- Extensiones: .pdf=2, .docx=1
- Inventarios Word: `Inventario_Fondo_Alicia.docx`
- Sistema de clasificación (heurística por nombres):
  - Indexación dominante por código de causa xx-yy (número correlativo + últimos dos dígitos del año).
  - Material digitalizado (imágenes/PDF) además de estructura de carpetas.
  - Vocabulario procesal-penal/militar (expediente, sentencia, consejo, fiscal).
- Entradas de primer nivel: `15-75`, `22-76`, `Inventario_Fondo_Alicia.docx`

### Fondo Bernardo

- Ruta relativa: `Fondos/Fondo Bernardo`
- Archivos: 3 · dirs: 3 · causas únicas: 2
- Extensiones: .pdf=2, .docx=1
- Inventarios Word: `Inventario_Fondo_Bernardo.docx`
- Sistema de clasificación (heurística por nombres):
  - Indexación dominante por código de causa xx-yy (número correlativo + últimos dos dígitos del año).
  - Presencia de unidades de conservación (caja/legajo/tomo/carpeta numerada).
  - Material digitalizado (imágenes/PDF) además de estructura de carpetas.
- Entradas de primer nivel: `08-74`, `15-75`, `Inventario_Fondo_Bernardo.docx`

### OneDrive_2026-07-13

- Ruta relativa: `Fondos/OneDrive_2026-07-13`
- Archivos: 5 · dirs: 6 · causas únicas: 2
- Extensiones: .pdf=3, .txt=1, .docx=1
- Inventarios Word: `FASIC/Inventario_FASIC.docx`
- Sistema de clasificación (heurística por nombres):
  - Indexación dominante por código de causa xx-yy (número correlativo + últimos dos dígitos del año).
  - Material digitalizado (imágenes/PDF) además de estructura de carpetas.
  - Vocabulario procesal-penal/militar (expediente, sentencia, consejo, fiscal).
  - Referencias institucionales en nombres (posible sub-serie por productor).
  - Traza de descarga OneDrive: revisar fusión de ramas antes de usar como fuente canónica.
- Entradas de primer nivel: `FASIC`, `FASIC (1)`, `readme_descarga.txt`

## Solapamiento de causas entre fondos

Se encontraron **1** códigos presentes en ≥2 fondos.

Interpretación: coincidencia de código **no implica** archivo idéntico. Dos investigadores pueden haber reunido piezas distintas (o parcialmente solapadas) sobre la misma causa. Tratarlos como **candidatos a alineación** en el grafo, no como deduplicación automática.

- `15-75` → Fondo Alicia, Fondo Bernardo (2 fondos)

## Fondo FASIC / OneDrive

**Posible descarga partida detectada.** Ejecutar `python -m consejos_guerra.fasic.reorganize --apply` tras revisar el dry-run.
- `/workspace/tests/fixtures/consejos_guerra_mini/Fondos/OneDrive_2026-07-13`
- `/workspace/tests/fixtures/consejos_guerra_mini/Fondos/OneDrive_2026-07-13/FASIC (1)`
- `/workspace/tests/fixtures/consejos_guerra_mini/Fondos/OneDrive_2026-07-13/FASIC`
- `/workspace/tests/fixtures/consejos_guerra_mini/Fondos/OneDrive_2026-07-13/readme_descarga.txt`

---
_Caracterización preliminar basada solo en nombres de rutas. Los inventarios Word aportan la descripción canónica de cada fondo._
