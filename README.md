# Consejos de Guerra — Grafo Multimodal

Repositorio de investigación para caracterizar los fondos documentales de
**Consejos de Guerra** (Museo de la Memoria / Nuestra Memoria) y, más adelante,
construir un **grafo multimodal** (documentos, causas, personas, productores de
archivo, etc.).

> Dataset privado y en crecimiento. **No se versiona** en git. Se accede por
> ruta local / symlink.

## Estado de acceso al dataset

Ruta canónica en la máquina de trabajo:

```text
/Users/camilogutierrez/STEM/nuestra-memoria/MuseoDeLaMemoria/2607 - Consejos de Guerra
```

En agentes cloud remotos esa ruta **no está montada**. Para caracterizar de
verdad:

```bash
export CONSEJOS_GUERRA_ROOT="/Users/camilogutierrez/STEM/nuestra-memoria/MuseoDeLaMemoria/2607 - Consejos de Guerra"
# o
mkdir -p data/external
ln -s "$CONSEJOS_GUERRA_ROOT" data/external/consejos_guerra
```

## Setup

```bash
uv sync
source .venv/bin/activate
cg-characterize status
```

## Comandos

```bash
# Barrido por nombres de archivos/carpetas + stats de causas xx-yy por año
cg-characterize characterize -o docs/caracterizacion/generado

# Solo inventarios Word (*inventario*.doc/docx)
cg-characterize inventarios

# Fondo FASIC partido (OneDrive_2026-07-13): dry-run y luego apply
cg-characterize fasic-reorganize
cg-characterize fasic-reorganize --apply
```

## Convenciones observadas (hipótesis de trabajo)

- Códigos de causa `xx-yy`: `xx` correlativo, `yy` = últimos dos dígitos del año
  (p. ej. `15-75` → causa 15 de 1975).
- Cada **fondo** es una recolección de un productor (investigador, institución,
  colaborador). La misma causa puede aparecer en varios fondos: **no deduplicar
  a ciegas** — puede ser material complementario.
- Los Word cuyo nombre contiene `inventario` describen cada fondo; son la fuente
  cualitativa prioritaria (el pipeline solo abre esos Word).

## Estructura del repo

```text
src/consejos_guerra/     código (caracterización, FASIC, inventarios)
scripts/                 atajos CLI
docs/caracterizacion/    informes (generado/ está gitignore-parcial)
tests/fixtures/          mini dataset sintético para CI
archive/dataframe-crossing/  notebooks previos del repo base
data/external/           symlink al dataset privado (no versionado)
```

## Tests

```bash
uv run pytest -q
```
