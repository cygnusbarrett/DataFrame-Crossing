# Qué correr (para que el agente haga el análisis completo)

Hace falta **una sola exportación liviana** en tu Mac. No subas PDFs ni el archivo entero.

## En tu Mac (una vez, o cuando crezca el dataset)

```bash
cd /ruta/al/repo   # DataFrame-Crossing / este proyecto
git checkout cursor/grafo-multimodal-consejos-guerra-e698
git pull
uv sync --extra dev

export CONSEJOS_GUERRA_ROOT="/Users/camilogutierrez/STEM/nuestra-memoria/MuseoDeLaMemoria/2607 - Consejos de Guerra"

# 1) Export liviano: árbol de nombres + Word *inventario* (sin PDFs)
uv run cg-characterize export-manifest

# 2) (Opcional, en la misma máquina) reorganizar FASIC de verdad
uv run cg-characterize fasic-reorganize                 # dry-run
uv run cg-characterize fasic-reorganize --apply         # si el plan está OK

# 3) Subir el manifiesto al repo
git add data/inputs/manifest_consejos_guerra
git commit -m "Datos: manifiesto Consejos de Guerra para caracterización remota"
git push
```

## Después: pedile al agente

> Caracterizá el dataset desde `data/inputs/manifest_consejos_guerra`  
> (informe pedagógico, eficiente y sintético + inventarios + solapes + FASIC).

El agente correrá:

```bash
uv run cg-characterize characterize-manifest
```

## Qué genera el export

| Archivo | Para qué |
| --- | --- |
| `manifest.csv` | Todos los paths (stats `xx-yy`, fondos, extensiones) |
| `tree.txt` | Vista legible del árbol |
| `inventarios_word/` | Solo Word con “inventario” en el nombre |
| `meta.json` | Conteos rápidos |

## Alternativa (si querés que el agente vea el disco completo)

Abrí Cursor **en local / Remote-SSH** con esa carpeta montada y pedí el análisis directo. El cloud agent remoto **no** puede leer `/Users/camilogutierrez/...`.
