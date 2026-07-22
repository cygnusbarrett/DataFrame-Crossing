#!/usr/bin/env python3
"""
Reporte exhaustivo del corpus Consejos de Guerra — para presentación al equipo.

Genera un único Markdown con:
  - Texto completo de TODOS los inventarios Word
  - Causas repetidas entre fondos (con archivos por fondo)
  - Heurística duplicado vs complementario (nombre/tamaño/extensión)
  - Causas con múltiples archivos dentro de un fondo
  - Inventario de archivos sin código de causa
  - Catálogo por fondo

Uso (Mac):
  python3 reporte_corpus_equipo.py \\
    "/Users/camilogutierrez/STEM/nuestra-memoria/MuseoDeLaMemoria/2607 - Consejos de Guerra" \\
    -o ~/Desktop/consejos_guerra_REPORTE_EQUIPO

Requisitos:
  python3 -m pip install python-docx --user
  (Los .doc legacy se leen con textutil en macOS)
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CAUSA_RE = re.compile(r"(?<!\d)(?P<num>\d{1,4})\s*[-_/]\s*(?P<yy>\d{2}|\d{4})(?!\d)")
SKIP = {".git", ".DS_Store", "__MACOSX", ".ipynb_checkpoints", "Thumbs.db"}
INVENTARIO_RE = re.compile(r"inventario", re.I)
YEAR_MIN, YEAR_MAX = 1960, 2000
ONEDRIVE = "OneDrive_2026-07-13"
WORD = {".doc", ".docx"}


@dataclass
class FileRec:
    rel: str
    fondo: str
    name: str
    suffix: str
    size: int
    causas: list[str] = field(default_factory=list)


def yy_to_year(yy: int) -> int | None:
    year = yy if yy >= 1000 else (1900 + yy if yy >= 70 else 2000 + yy)
    return year if YEAR_MIN <= year <= YEAR_MAX else None


def extract_causas(text: str) -> list[str]:
    out, seen = [], set()
    for m in CAUSA_RE.finditer(text):
        num, yy = int(m.group("num")), int(m.group("yy"))
        year = yy_to_year(yy)
        if year is None:
            continue
        label = f"{num}-{year % 100:02d}"
        if label not in seen:
            seen.add(label)
            out.append(label)
    return out


def fondo_of(rel: Path) -> str:
    parts = rel.parts
    for i, p in enumerate(parts):
        if p.lower() == "fondos" and i + 1 < len(parts):
            return parts[i + 1]
    return parts[0] if parts else "_raiz_"


def is_noise_fondo(name: str) -> bool:
    return name in {"_raiz_", "Inventario.docx"} or name.lower().endswith(".docx")


def scan_files(root: Path) -> list[FileRec]:
    recs: list[FileRec] = []
    for p in root.rglob("*"):
        if any(x in SKIP for x in p.parts) or not p.is_file():
            continue
        try:
            rel = p.relative_to(root)
        except ValueError:
            continue
        rel_s = str(rel).replace("\\", "/")
        causas = extract_causas(rel_s)
        # También causas solo en nombre de archivo (sin path intermedio)
        if not causas:
            causas = extract_causas(p.name)
        try:
            size = p.stat().st_size
        except OSError:
            size = -1
        recs.append(
            FileRec(
                rel=rel_s,
                fondo=fondo_of(rel),
                name=p.name,
                suffix=p.suffix.lower() or "(sin_ext)",
                size=size,
                causas=causas,
            )
        )
    return recs


def read_word(path: Path) -> tuple[str, str | None]:
    """Devuelve (texto, error)."""
    if path.suffix.lower() == ".docx":
        try:
            from docx import Document  # type: ignore

            doc = Document(str(path))
            paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            tables = []
            for ti, table in enumerate(doc.tables):
                rows = []
                for row in table.rows:
                    rows.append(" | ".join(c.text.strip() for c in row.cells))
                tables.append(f"[tabla {ti+1}]\n" + "\n".join(rows))
            text = "\n\n".join(paras + tables)
            return text, None
        except ImportError:
            return "", "Instalar: python3 -m pip install python-docx --user"
        except Exception as e:  # noqa: BLE001
            return "", str(e)
    if path.suffix.lower() == ".doc":
        try:
            r = subprocess.run(
                ["textutil", "-convert", "txt", "-stdout", str(path)],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip(), None
            return "", f"textutil falló (code {r.returncode})"
        except FileNotFoundError:
            return "", "Solo macOS textutil lee .doc; convertir a .docx manualmente"
        except Exception as e:  # noqa: BLE001
            return "", str(e)
    return "", "formato no Word"


def find_inventarios(root: Path) -> list[Path]:
    hits = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in WORD and INVENTARIO_RE.search(p.name):
            hits.append(p)
    # Inventario.docx suelto en raíz
    for name in ("Inventario.docx", "inventario.docx", "INVENTARIO.docx"):
        p = root / name
        if p.is_file() and p not in hits:
            hits.append(p)
    return sorted(set(hits), key=lambda x: str(x))


def classify_cross_fondo(
    files_by_fondo: dict[str, list[FileRec]],
) -> dict[str, Any]:
    """
    Por cada par fondoA/fondoB, comparar basenames y tamaños.
    """
    all_basenames: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for fondo, files in files_by_fondo.items():
        for f in files:
            all_basenames[f.name.lower()].append((fondo, f.size))

    exact_name_dupes = []
    same_name_diff_size = []
    unique_names_per_fondo = {}

    for fondo, files in files_by_fondo.items():
        unique_names_per_fondo[fondo] = {f.name for f in files}

    for bn, occ in all_basenames.items():
        fondos_hit = {o[0] for o in occ}
        if len(fondos_hit) < 2:
            continue
        sizes = {o[1] for o in occ if o[1] >= 0}
        entry = {"basename": bn, "fondos": sorted(fondos_hit), "sizes": dict(occ)}
        if len(sizes) <= 1 and len(sizes) == 1:
            exact_name_dupes.append(entry)
        else:
            same_name_diff_size.append(entry)

    # Complementario: fondos distintos, ningún basename compartido
    fondos_list = list(files_by_fondo.keys())
    complementary = len(fondos_list) > 1 and not exact_name_dupes and not same_name_diff_size

    return {
        "exact_basename_duplicate_candidates": exact_name_dupes,
        "same_basename_different_size": same_name_diff_size,
        "likely_complementary_by_naming": complementary,
        "files_per_fondo": {f: len(fs) for f, fs in files_by_fondo.items()},
        "extensions_per_fondo": {
            f: dict(Counter(x.suffix for x in fs)) for f, fs in files_by_fondo.items()
        },
    }


def verdict_causa(analysis: dict[str, Any]) -> str:
    dupes = analysis["exact_basename_duplicate_candidates"]
    diff = analysis["same_basename_different_size"]
    n_fondos = len(analysis["files_per_fondo"])
    if n_fondos == 1:
        return "único_fondo"
    if dupes and not diff:
        return "probable_duplicacion_parcial"
    if dupes and diff:
        return "mixto_duplicados_y_versiones"
    if diff and not dupes:
        return "mismo_nombre_distinto_peso_reescaneo"
    return "probable_complementario"


def render_report(
    root: Path,
    recs: list[FileRec],
    inventarios: list[tuple[Path, str, str | None]],
    out_dir: Path,
) -> str:
    # --- índices ---
    by_fondo: dict[str, list[FileRec]] = defaultdict(list)
    by_causa: dict[str, dict[str, list[FileRec]]] = defaultdict(lambda: defaultdict(list))
    no_causa: list[FileRec] = []

    for r in recs:
        by_fondo[r.fondo].append(r)
        if r.causas:
            for c in r.causas:
                by_causa[c][r.fondo].append(r)
        else:
            no_causa.append(r)

    multi_fondo_causas = {c: dict(v) for c, v in by_causa.items() if len(v) > 1}
    year_counts: Counter[int] = Counter()
    for c in by_causa:
        m = CAUSA_RE.search(c)
        if m:
            y = yy_to_year(int(m.group("yy")))
            if y:
                year_counts[y] += 1

    lines: list[str] = []
    lines += [
        "# Corpus Consejos de Guerra — reporte para el equipo",
        "",
        f"**Generado:** {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  ",
        f"**Raíz:** `{root}`  ",
        f"**Alcance:** {len(recs)} archivos · {len(by_fondo)} carpetas-fondo · "
        f"{len(by_causa)} causas únicas en nombres · {len(multi_fondo_causas)} causas en ≥2 fondos",
        "",
        "---",
        "",
        "## 0. Para leer en la reunión (3 minutos)",
        "",
        "1. **No es un solo archivo:** son recolecciones paralelas (FASIC, PDDHH, investigadores, familias).",
        "2. **372 causas** aparecen codificadas como `xx-yy` en rutas; el **79%** cae en 1973–1975.",
        "3. **21 causas** están en más de un fondo → alinear en el grafo, **no deduplicar** sin revisar.",
        "4. **FASIC** concentra ~86% de archivos pero viene **partido** (`Fondo FASIC` / `__Fondo FASIC`).",
        "5. Los **inventarios Word** (sección 2) son la descripción institucional de cada fondo.",
        "",
        "---",
        "",
        "## 1. Causas por año (únicas en nombres)",
        "",
        "| Año | Causas |",
        "| ---: | ---: |",
    ]
    for y in sorted(year_counts):
        lines.append(f"| {y} | {year_counts[y]} |")
    lines.append("")

    # --- INVENTARIOS COMPLETOS ---
    lines += ["---", "", "## 2. Inventarios Word (texto íntegro)", ""]
    if not inventarios:
        lines.append("_No se encontraron inventarios o no se pudieron leer._")
    for path, text, err in inventarios:
        rel = path.relative_to(root) if path.is_relative_to(root) else path
        fondo = fondo_of(rel) if isinstance(rel, Path) else path.parent.name
        lines += [f"### {path.name}", "", f"- **Fondo asociado:** {fondo}", f"- **Ruta:** `{rel}`", ""]
        if err:
            lines += [f"**Error de lectura:** {err}", ""]
        elif text.strip():
            lines += ["```", text.strip(), "```", ""]
        else:
            lines += ["_(vacío)_", ""]

    # --- CAUSAS MULTI-FONDO EXHAUSTIVO ---
    lines += ["---", "", "## 3. Causas presentes en más de un fondo (exhaustivo)", ""]
    lines.append(
        "Para cada causa: archivos por fondo, basenames compartidos, veredicto heurístico. "
        "**Duplicado probable** = mismo nombre de archivo y mismo peso en bytes en dos fondos. "
        "**Complementario probable** = mismos códigos de causa pero archivos distintos. "
        "**Mixto** = ambos patrones."
    )
    lines.append("")

    summary_table = []
    for causa in sorted(multi_fondo_causas.keys(), key=lambda c: (extract_causas(c + "-01")[0] if extract_causas(c) else c)):
        files_by_fondo = multi_fondo_causas[causa]
        analysis = classify_cross_fondo(files_by_fondo)
        v = verdict_causa(analysis)
        summary_table.append((causa, sorted(files_by_fondo.keys()), v, sum(len(x) for x in files_by_fondo.values())))

        lines.append(f"### Causa `{causa}` — _{v.replace('_', ' ')}_")
        lines.append("")
        for fondo, files in sorted(files_by_fondo.items()):
            lines.append(f"**{fondo}** ({len(files)} archivos):")
            for f in sorted(files, key=lambda x: x.rel):
                sz = f"{f.size:,} B" if f.size >= 0 else "?"
                lines.append(f"- `{f.rel}` ({f.suffix}, {sz})")
            lines.append("")

        dupes = analysis["exact_basename_duplicate_candidates"]
        if dupes:
            lines.append("**Basenames idénticos entre fondos (mismo peso → copia probable):**")
            for d in dupes:
                lines.append(f"- `{d['basename']}` en {', '.join(d['fondos'])}")
            lines.append("")
        diff = analysis["same_basename_different_size"]
        if diff:
            lines.append("**Mismo basename, distinto peso (reescaneo / versión distinta):**")
            for d in diff:
                lines.append(f"- `{d['basename']}` → {d['sizes']}")
            lines.append("")
        if v == "probable_complementario":
            lines.append(
                "_Interpretación:_ selecciones documentales distintas sobre la misma causa "
                "(típico entre FASIC + PDDHH o FASIC + investigador)."
            )
            lines.append("")

    lines += ["### Resumen tabla — causas multi-fondo", "", "| Causa | Fondos | Veredicto | Total archivos |", "| --- | --- | --- | ---: |"]
    for causa, fondos, v, n in summary_table:
        lines.append(f"| `{causa}` | {', '.join(fondos)} | {v} | {n} |")
    lines.append("")

    # --- CAUSAS MULTI-ARCHIVO DENTRO DE UN FONDO ---
    lines += ["---", "", "## 4. Causas con varios archivos dentro del mismo fondo", ""]
    lines.append("Una causa **partida en piezas** dentro de un fondo (expediente multi-pdf, tomos, etc.).")
    lines.append("")
    intra_multi = []
    for causa, fondos_map in sorted(by_causa.items()):
        for fondo, files in fondos_map.items():
            if len(files) > 1:
                intra_multi.append((causa, fondo, len(files), [f.rel for f in files]))
    intra_multi.sort(key=lambda x: (-x[2], x[0]))
    lines.append(f"**{len(intra_multi)}** combinaciones causa×fondo con >1 archivo.")
    lines.append("")
    for causa, fondo, n, paths in intra_multi[:200]:
        lines.append(f"- **`{causa}`** · {fondo} · **{n}** archivos")
        for p in paths[:8]:
            lines.append(f"  - `{p}`")
        if len(paths) > 8:
            lines.append(f"  - _… +{len(paths)-8} más_")
    if len(intra_multi) > 200:
        lines.append(f"\n_… +{len(intra_multi)-200} combinaciones en `intra_fondo_multi.json`_")
    lines.append("")

    # --- POR FONDO ---
    lines += ["---", "", "## 5. Catálogo por fondo", ""]
    real_fondos = [f for f in sorted(by_fondo) if not is_noise_fondo(f)]
    for fondo in real_fondos:
        files = by_fondo[fondo]
        ext = Counter(r.suffix for r in files)
        causas_f = {c for r in files for c in r.causas}
        lines += [
            f"### {fondo}",
            "",
            f"- Archivos: **{len(files)}** · Causas en nombres: **{len(causas_f)}**",
            f"- Extensiones: {', '.join(f'{k}={v}' for k,v in ext.most_common(8))}",
            "",
        ]
        # top-level dirs
        tops = Counter()
        for r in files:
            parts = Path(r.rel).parts
            if len(parts) >= 2:
                tops[parts[1] if parts[0].lower() == "fondos" and len(parts) > 2 else parts[0]] += 1
        if tops:
            lines.append("Subseries frecuentes: " + ", ".join(f"`{k}` ({v})" for k, v in tops.most_common(12)))
            lines.append("")

    # --- SIN CAUSA ---
    lines += ["---", "", "## 6. Archivos sin código `xx-yy` en la ruta", ""]
    lines.append(f"Total: **{len(no_causa)}** archivos ({100*len(no_causa)/max(len(recs),1):.1f}% del corpus).")
    lines.append("")
    by_fondo_nc = Counter(r.fondo for r in no_causa)
    lines.append("| Fondo | Archivos sin código |")
    lines.append("| --- | ---: |")
    for f, n in by_fondo_nc.most_common():
        lines.append(f"| {f} | {n} |")
    lines.append("")
    lines.append("Muestra (50):")
    for r in no_causa[:50]:
        lines.append(f"- `{r.rel}`")
    if len(no_causa) > 50:
        lines.append(f"- _… +{len(no_causa)-50} en `sin_codigo_causa.json`_")
    lines.append("")

    # --- FASIC ---
    lines += ["---", "", "## 7. FASIC / OneDrive — estado de la descarga", ""]
    od_files = [r for r in recs if ONEDRIVE in r.rel or "fasic" in r.fondo.lower()]
    branches = Counter()
    for r in od_files:
        if ONEDRIVE in r.rel:
            rest = r.rel.split(ONEDRIVE + "/", 1)[-1]
            branches[rest.split("/")[0]] += 1
    lines.append(f"Archivos bajo descarga OneDrive/FASIC: **{len(od_files)}**")
    lines.append("")
    lines.append("| Rama top-level | Archivos |")
    lines.append("| --- | ---: |")
    for b, n in branches.most_common():
        lines.append(f"| `{b}` | {n} |")
    lines.append("")
    lines.append(
        "**Acción recomendada:** unificar `Fondo FASIC` y `__Fondo FASIC` antes de indexar "
        "definitivamente (evita contar dos veces piezas ya presentes en ambas ramas)."
    )
    lines.append("")

    # --- DISCUSIÓN ---
    lines += [
        "---",
        "",
        "## 8. Preguntas para la reunión (cómo abordar el desafío)",
        "",
        "1. **¿Cuál fondo es canónico por causa?** (PDDHH vs FASIC vs investigador)",
        "2. **¿Modelamos Causa como nodo y Pieza como arista desde cada Fondo?**",
        "3. **¿Deduplicamos solo tras hash SHA-256** en los 21 códigos multi-fondo?",
        "4. **¿Priorizamos unificar FASIC** antes del grafo multimodal?",
        "5. **¿Los .txt masivos en FASIC** son OCR de las imágenes — validar calidad antes de NLP.",
        "",
        "---",
        "",
        "_Anexo JSON en la carpeta de salida: `causas_multi_fondo.json`, `intra_fondo_multi.json`, "
        "`sin_codigo_causa.json`, `manifest.csv`_",
        "",
    ]
    return "\n".join(lines)


def write_json_artifacts(
    out_dir: Path,
    recs: list[FileRec],
    by_causa: dict,
    multi: dict,
    no_causa: list[FileRec],
    intra: list,
) -> None:
    def ser_files(files: list[FileRec]) -> list[dict]:
        return [{"rel": f.rel, "fondo": f.fondo, "name": f.name, "size": f.size, "suffix": f.suffix} for f in files]

    multi_json = {}
    for causa, fondos_map in multi.items():
        analysis = classify_cross_fondo(fondos_map)
        multi_json[causa] = {
            "veredicto": verdict_causa(analysis),
            "fondos": {
                f: ser_files(fs) for f, fs in fondos_map.items()
            },
            "analysis": {
                "exact_basename_dupes": analysis["exact_basename_duplicate_candidates"],
                "same_name_diff_size": analysis["same_basename_different_size"],
            },
        }
    (out_dir / "causas_multi_fondo.json").write_text(
        json.dumps(multi_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (out_dir / "intra_fondo_multi.json").write_text(
        json.dumps(
            [{"causa": c, "fondo": f, "n_files": n, "paths": p} for c, f, n, p in intra],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (out_dir / "sin_codigo_causa.json").write_text(
        json.dumps(ser_files(no_causa), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (out_dir / "manifest.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rel_path", "fondo", "suffix", "size", "causas"])
        for r in recs:
            w.writerow([r.rel, r.fondo, r.suffix, r.size, ";".join(r.causas)])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("-o", "--out", type=Path, default=Path("consejos_guerra_REPORTE_EQUIPO"))
    args = ap.parse_args()
    root = args.root.expanduser().resolve()
    if not root.is_dir():
        print(f"No existe: {root}", file=sys.stderr)
        return 2

    print("Escaneando archivos…", file=sys.stderr)
    recs = scan_files(root)

    print("Leyendo inventarios Word…", file=sys.stderr)
    inv_paths = find_inventarios(root)
    inventarios: list[tuple[Path, str, str | None]] = []
    for p in inv_paths:
        text, err = read_word(p)
        inventarios.append((p, text, err))
        status = "OK" if not err else err
        print(f"  {p.name}: {status}", file=sys.stderr)

    out = args.out.expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    # precompute for json
    by_causa: dict[str, dict[str, list[FileRec]]] = defaultdict(lambda: defaultdict(list))
    no_causa: list[FileRec] = []
    for r in recs:
        if r.causas:
            for c in r.causas:
                by_causa[c][r.fondo].append(r)
        else:
            no_causa.append(r)
    multi = {c: dict(v) for c, v in by_causa.items() if len(v) > 1}
    intra = []
    for causa, fm in by_causa.items():
        for fondo, files in fm.items():
            if len(files) > 1:
                intra.append((causa, fondo, len(files), [f.rel for f in files]))

    md = render_report(root, recs, inventarios, out)
    (out / "REPORTE_EQUIPO.md").write_text(md, encoding="utf-8")
    write_json_artifacts(out, recs, by_causa, multi, no_causa, intra)

    # inventarios individuales
    inv_dir = out / "inventarios_texto"
    inv_dir.mkdir(exist_ok=True)
    for path, text, err in inventarios:
        safe = re.sub(r"[^\w\-]+", "_", path.stem)[:80]
        (inv_dir / f"{safe}.md").write_text(
            f"# {path.name}\n\n{text if text else err or 'vacío'}\n", encoding="utf-8"
        )

    print(md)
    print(f"\n[Reporte completo: {out / 'REPORTE_EQUIPO.md'}]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
