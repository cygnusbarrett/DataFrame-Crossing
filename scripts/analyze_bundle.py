#!/usr/bin/env python3
"""
Analiza un bundle liviano (manifest + JSON + inventarios) SIN el dataset completo.
El agente cloud corre esto tras recibir data/inputs/corpus_bundle.zip

Uso local (Mac) — crear bundle:
  cd ~/Desktop/consejos_guerra_REPORTE_EQUIPO   # o consejos_guerra_caracterizacion
  zip -r ~/Desktop/corpus_bundle.zip \\
    manifest.csv causas_multi_fondo.json inventarios_texto/ \\
    intra_fondo_multi.json sin_codigo_causa.json 2>/dev/null || \\
  zip -r ~/Desktop/corpus_bundle.zip manifest.csv caracterizacion.json

Subir: arrastrar corpus_bundle.zip al chat de Cursor, o:
  cp ~/Desktop/corpus_bundle.zip /ruta/al/repo/data/inputs/ && git push
"""

from __future__ import annotations

import csv
import json
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "data" / "inputs" / "corpus_bundle.zip"
EXTRACT = ROOT / "data" / "inputs" / "corpus_bundle"
OUT = ROOT / "docs" / "caracterizacion" / "REPORTE_EQUIPO.md"


def load_bundle() -> Path:
    if not BUNDLE.is_file():
        raise FileNotFoundError(
            f"No está {BUNDLE}\n"
            "Subí corpus_bundle.zip a data/inputs/ (ver scripts/bundle_for_agent.sh)"
        )
    EXTRACT.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(BUNDLE) as z:
        z.extractall(EXTRACT)
    return EXTRACT


def read_manifest(base: Path) -> list[dict]:
    csv_path = base / "manifest.csv"
    if not csv_path.is_file():
        for p in base.rglob("manifest.csv"):
            csv_path = p
            break
    if not csv_path.is_file():
        raise FileNotFoundError("manifest.csv no encontrado en el bundle")
    with csv_path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def read_multi(base: Path) -> dict:
    for name in ("causas_multi_fondo.json", "caracterizacion.json"):
        p = base / name
        if p.is_file():
            data = json.loads(p.read_text(encoding="utf-8"))
            if name == "caracterizacion.json":
                return data.get("causas_multi_fondo", data)
            return data
    for p in base.rglob("causas_multi_fondo.json"):
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def read_inventarios(base: Path) -> list[tuple[str, str]]:
    inv_dir = base / "inventarios_texto"
    if not inv_dir.is_dir():
        for d in base.rglob("inventarios_texto"):
            inv_dir = d
            break
    texts = []
    if inv_dir.is_dir():
        for p in sorted(inv_dir.glob("*.md")):
            texts.append((p.name, p.read_text(encoding="utf-8")))
    return texts


def build_report(rows: list[dict], multi_json: dict, inventarios: list[tuple[str, str]]) -> str:
    by_fondo = Counter(r.get("fondo") or "?" for r in rows if r.get("kind") == "file")
    n_files = sum(1 for r in rows if r.get("kind") == "file")

    # Reconstruir multi-fondo desde manifest si no hay JSON detallado
    causa_fondos: dict[str, set[str]] = defaultdict(set)
    causa_files: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    import re

    CAUSA_RE = re.compile(r"(?<!\d)(\d{1,4})\s*[-_/]\s*(\d{2}|\d{4})(?!\d)")

    for r in rows:
        if r.get("kind") != "file":
            continue
        rel = r.get("rel_path") or r.get("rel") or ""
        fondo = r.get("fondo") or "?"
        causas = (r.get("causas") or "").split(";") if r.get("causas") else []
        if not causas or causas == [""]:
            for m in CAUSA_RE.finditer(rel):
                yy = int(m.group(2))
                year = yy if yy >= 1000 else (1900 + yy if yy >= 70 else 2000 + yy)
                causas.append(f"{int(m.group(1))}-{year % 100:02d}")
        for c in set(causas):
            if c:
                causa_fondos[c].add(fondo)
                causa_files[c][fondo].append(r)

    multi = {c: fs for c, fs in causa_fondos.items() if len(fs) > 1}

    lines = [
        "# Reporte equipo — Consejos de Guerra",
        "",
        f"Archivos en manifiesto: **{n_files}** · Causas multi-fondo: **{len(multi)}**",
        "",
        "## Inventarios Word",
        "",
    ]
    if inventarios:
        for name, text in inventarios:
            lines += [f"### {name}", "", text.strip(), ""]
    else:
        lines.append("_Inventarios no incluidos en el bundle. Re-exportar con inventarios_texto/_")
        lines.append("")

    lines += ["## Causas en ≥2 fondos (detalle)", ""]
    for causa in sorted(multi):
        lines.append(f"### `{causa}`")
        fondos_map = causa_files.get(causa, {})
        for fondo, files in sorted(fondos_map.items()):
            lines.append(f"**{fondo}** ({len(files)} archivos):")
            basenames: Counter[str] = Counter()
            for f in files:
                rel = f.get("rel_path") or f.get("rel", "")
                name = rel.rsplit("/", 1)[-1]
                basenames[name.lower()] += 1
                sz = f.get("size", "?")
                lines.append(f"- `{rel}` ({sz} B)")
            lines.append("")
        # duplicados por basename
        all_bn: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for fondo, files in fondos_map.items():
            for f in files:
                rel = f.get("rel_path") or f.get("rel", "")
                bn = rel.rsplit("/", 1)[-1].lower()
                all_bn[bn].append((fondo, str(f.get("size", ""))))
        shared = {bn: occ for bn, occ in all_bn.items() if len({o[0] for o in occ}) > 1}
        if shared:
            lines.append("**Basenames compartidos entre fondos:**")
            for bn, occ in shared.items():
                sizes = {o[1] for o in occ}
                tag = "copia probable" if len(sizes) == 1 else "distinto peso"
                lines.append(f"- `{bn}` → {occ} ({tag})")
            lines.append("")
        else:
            lines.append("_Sin basenames idénticos → material probablemente **complementario**._")
            lines.append("")

    lines += ["## Fondos (conteo)", ""]
    for f, n in by_fondo.most_common():
        lines.append(f"- **{f}**: {n} archivos")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    base = load_bundle()
    rows = read_manifest(base)
    multi = read_multi(base)
    inv = read_inventarios(base)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build_report(rows, multi, inv), encoding="utf-8")
    print(f"Escrito: {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
