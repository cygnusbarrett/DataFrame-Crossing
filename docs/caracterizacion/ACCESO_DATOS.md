# Acceso al dataset privado

## Bloqueo en este entorno (Cloud Agent)

El set de datos vive en la máquina local del investigador:

```text
/Users/camilogutierrez/STEM/nuestra-memoria/MuseoDeLaMemoria/2607 - Consejos de Guerra
```

Esa ruta **no está disponible** en el contenedor remoto del Cloud Agent
(`FileNotFoundError` al resolver `CONSEJOS_GUERRA_ROOT`). Por eso **no** se
pudieron emitir en esta corrida:

- estadísticas reales de causas por año sobre los fondos,
- descripción de clasificación por fondo a partir de nombres reales,
- lectura de los Word `*inventario*`,
- ni la reorganización material del Fondo FASIC en `OneDrive_2026-07-13`.

Sí quedó listo el **repositorio de trabajo** (código + tests + fixture sintético)
para ejecutar todo en cuanto el dataset sea visible.

## Cómo desbloquear (en la Mac / Remote-SSH con el disco montado)

```bash
cd /ruta/a/este/repo
uv sync --extra dev
cp .env.example .env
# editar CONSEJOS_GUERRA_ROOT=...

# o symlink
mkdir -p data/external
ln -s "/Users/camilogutierrez/STEM/nuestra-memoria/MuseoDeLaMemoria/2607 - Consejos de Guerra" \
  data/external/consejos_guerra

uv run cg-characterize status
uv run cg-characterize characterize -o docs/caracterizacion/generado
uv run cg-characterize inventarios
uv run cg-characterize fasic-reorganize          # dry-run
uv run cg-characterize fasic-reorganize --apply  # tras revisar el plan JSON
```

## Qué hace cada paso

| Comando | Efecto |
| --- | --- |
| `characterize` | Árbol por fondo, extensiones, heurística de clasificación, causas `xx-yy` por año, causas multi-fondo |
| `inventarios` | Solo Word cuyo nombre contiene `inventario` → markdown extraído |
| `fasic-reorganize` | Detecta ramas bajo `OneDrive_2026-07-13` (p.ej. `FASIC` + `FASIC (1)`) y propone fusión en `Fondos/Fondo FASIC` |

## Nota sobre duplicados entre fondos

Si la causa `15-75` aparece en dos fondos, el pipeline la marca como
**candidato a alineación**, no como duplicado a borrar. Dos recolecciones
independientes pueden contener:

- las mismas piezas (copia redundante; verificable por hash), o
- selecciones distintas / notas de investigador (material **complementario**).

El grafo multimodal debería modelar `Causa` compartida y `PiezaDocumental`
ligada al `Fondo`/`Productor`.
