#!/usr/bin/env bash
# Mac: empaqueta SOLO lo que el agente cloud necesita (~0.5–2 MB). NO incluye PDFs.
set -euo pipefail

SRC="${1:-$HOME/Desktop/consejos_guerra_REPORTE_EQUIPO}"
OUT="${2:-$HOME/Desktop/corpus_bundle.zip}"

if [[ ! -d "$SRC" ]]; then
  SRC="$HOME/Desktop/consejos_guerra_caracterizacion"
fi
if [[ ! -d "$SRC" ]]; then
  echo "No encontré carpeta de salida. Corré primero reporte_corpus_equipo.py"
  exit 1
fi

cd "$SRC"
zip -r "$OUT" \
  manifest.csv \
  causas_multi_fondo.json \
  intra_fondo_multi.json \
  sin_codigo_causa.json \
  inventarios_texto \
  caracterizacion.json \
  2>/dev/null || zip -r "$OUT" manifest.csv caracterizacion.json

echo "Bundle listo: $OUT ($(du -h "$OUT" | cut -f1))"
echo ""
echo "Opción A — arrastrar $OUT al chat de Cursor"
echo "Opción B — si tienes el repo clonado:"
echo "  cp \"$OUT\" /ruta/al/repo/data/inputs/corpus_bundle.zip && git push"
