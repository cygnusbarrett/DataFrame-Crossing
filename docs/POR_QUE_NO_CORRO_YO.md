# Por qué el agente cloud no puede “correrlo solo”

El **Cloud Agent** corre en un contenedor Linux remoto. **No tiene acceso** a:

```text
/Users/camilogutierrez/STEM/...
```

Tu Mac y el agente cloud son **dos máquinas distintas**. Por eso pedirte pegar un reporte de 500 KB+ se corta, y por eso yo no puedo leer tus PDFs/Word directamente desde aquí.

## Forma eficiente (una vez, ~1 MB)

En tu Mac, después de haber corrido `reporte_corpus_equipo.py`:

```bash
curl -fsSL "https://raw.githubusercontent.com/cygnusbarrett/DataFrame-Crossing/cursor/grafo-multimodal-consejos-guerra-e698/scripts/bundle_for_agent.sh" -o /tmp/bundle.sh
bash /tmp/bundle.sh
```

Eso crea `~/Desktop/corpus_bundle.zip` (**solo** manifest + JSON + inventarios en texto, sin PDFs).

Luego **una** de estas:

1. **Arrastrar** `corpus_bundle.zip` al chat de Cursor (adjunto).
2. Si clonaste el repo en algún lado:
   ```bash
   cp ~/Desktop/corpus_bundle.zip /ruta/al/repo/data/inputs/
   git add data/inputs/corpus_bundle.zip && git commit -m "bundle corpus" && git push
   ```
   y decir: *“analiza el bundle”*.

Yo descomprimo, corro `scripts/analyze_bundle.py` y escribo `docs/caracterizacion/REPORTE_EQUIPO.md` **aquí**, sin que pegues nada.

## Alternativa ideal: agente en tu Mac

Abrí **Cursor en local** (o Remote-SSH al servidor donde vive el corpus) con la carpeta del dataset en el workspace. Ahí el agente **sí** lee el disco directamente — cero bundles.
