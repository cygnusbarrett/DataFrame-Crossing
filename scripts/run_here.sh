#!/usr/bin/env bash
# Ejecuta la caracterización completa EN ESTE entorno (cloud/local).
# Prioridad de datos:
#   1) --manifest-dir / --manifest-zip
#   2) data/inputs/manifest_consejos_guerra/manifest.csv
#   3) CONSEJOS_GUERRA_ROOT o data/external/consejos_guerra (dataset montado)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

MANIFEST_DIR="${ROOT}/data/inputs/manifest_consejos_guerra"
OUT_DIR="${ROOT}/docs/caracterizacion/generado"
MANIFEST_ZIP=""
DATA_ROOT="${CONSEJOS_GUERRA_ROOT:-}"
APPLY_FASIC=0

usage() {
  cat <<'EOF'
Uso: scripts/run_here.sh [opciones]

  --manifest-dir DIR   Carpeta con manifest.csv (+ inventarios_word/)
  --manifest-zip ZIP   Zip del export-manifest (se descomprime en data/inputs/)
  --data-root DIR      Dataset completo montado (salta el manifiesto)
  --out DIR            Salida del informe (default: docs/caracterizacion/generado)
  --apply-fasic        Si hay dataset montado, aplica reorganización FASIC
  -h, --help           Esta ayuda

Ejemplos:
  scripts/run_here.sh
  scripts/run_here.sh --manifest-zip ~/Downloads/manifest_consejos_guerra.zip
  scripts/run_here.sh --data-root "$CONSEJOS_GUERRA_ROOT" --apply-fasic
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --manifest-dir) MANIFEST_DIR="$2"; shift 2 ;;
    --manifest-zip) MANIFEST_ZIP="$2"; shift 2 ;;
    --data-root) DATA_ROOT="$2"; shift 2 ;;
    --out) OUT_DIR="$2"; shift 2 ;;
    --apply-fasic) APPLY_FASIC=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Opción desconocida: $1"; usage; exit 1 ;;
  esac
done

export PATH="${HOME}/.local/bin:${PATH}"
if [[ ! -x "${ROOT}/.venv/bin/cg-characterize" ]] && ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="${HOME}/.local/bin:${PATH}"
fi
uv sync --extra dev

if [[ -n "$MANIFEST_ZIP" ]]; then
  echo "→ Descomprimiendo $MANIFEST_ZIP"
  mkdir -p "${ROOT}/data/inputs"
  rm -rf "$MANIFEST_DIR"
  mkdir -p "$MANIFEST_DIR"
  unzip -q -o "$MANIFEST_ZIP" -d "$MANIFEST_DIR"
  # Si el zip traía una carpeta raíz, aplanar un nivel
  if [[ ! -f "$MANIFEST_DIR/manifest.csv" ]]; then
    inner="$(find "$MANIFEST_DIR" -maxdepth 2 -name manifest.csv | head -1 || true)"
    if [[ -n "$inner" ]]; then
      base="$(dirname "$inner")"
      shopt -s dotglob
      mv "$base"/* "$MANIFEST_DIR"/ 2>/dev/null || true
      shopt -u dotglob
    fi
  fi
fi

mkdir -p "$OUT_DIR"

if [[ -n "$DATA_ROOT" && -d "$DATA_ROOT" ]]; then
  echo "→ Dataset montado: $DATA_ROOT"
  uv run cg-characterize characterize -d "$DATA_ROOT" -o "$OUT_DIR"
  uv run cg-characterize inventarios -d "$DATA_ROOT" -o "$OUT_DIR/inventarios"
  if [[ "$APPLY_FASIC" -eq 1 ]]; then
    uv run cg-characterize fasic-reorganize -d "$DATA_ROOT" --apply
  else
    uv run cg-characterize fasic-reorganize -d "$DATA_ROOT" \
      --plan-out "$OUT_DIR/fasic_reorganize_plan.json" || true
  fi
elif [[ -f "$MANIFEST_DIR/manifest.csv" ]]; then
  echo "→ Manifiesto: $MANIFEST_DIR"
  uv run cg-characterize characterize-manifest -m "$MANIFEST_DIR" -o "$OUT_DIR"
else
  cat <<EOF
No hay datos visibles todavía.

Para ejecutarlo AQUÍ, elegí UNA vía:

A) Desde la Mac, exportá y subí el zip/manifiesto:
   export CONSEJOS_GUERRA_ROOT="/Users/camilogutierrez/STEM/nuestra-memoria/MuseoDeLaMemoria/2607 - Consejos de Guerra"
   uv run cg-characterize export-manifest
   cd data/inputs && zip -r ../../manifest_consejos_guerra.zip manifest_consejos_guerra
   # subí manifest_consejos_guerra.zip al workspace (o commit+push) y luego:
   scripts/run_here.sh --manifest-zip /workspace/manifest_consejos_guerra.zip

B) Commit + push del export, y aquí:
   git pull
   scripts/run_here.sh

C) Montar el dataset completo en data/external/consejos_guerra y:
   scripts/run_here.sh --data-root data/external/consejos_guerra
EOF
  exit 2
fi

echo
echo "Listo. Informe sintético:"
echo "  $OUT_DIR/caracterizacion.md"
echo "  $OUT_DIR/caracterizacion.json"
echo "  $OUT_DIR/causas_por_anio.csv"
ls -la "$OUT_DIR" || true
