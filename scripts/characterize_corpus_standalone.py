#!/usr/bin/env python3
"""
Caracterización sintética del corpus Consejos de Guerra.
Standalone: no necesita el repo ni uv. Solo Python 3.10+.

Uso:
  python3 characterize_corpus_standalone.py \
    "/Users/camilogutierrez/STEM/nuestra-memoria/MuseoDeLaMemoria/2607 - Consejos de Guerra"

Opcional:
  python3 characterize_corpus_standalone.py "$ROOT" -o ~/Desktop/consejos_guerra_caracterizacion
  python3 characterize_corpus_standalone.py "$ROOT" --inventarios   # requiere: pip install python-docx
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

CAUSA_RE = re.compile(r"(?<!\d)(?P<num>\d{1,4})\s*[-_/]\s*(?P<yy>\d{2}|\d{4})(?!\d)")
SKIP = {".git", ".DS_Store", "__MACOSX", ".ipynb_checkpoints", "Thumbs.db"}
YEAR_MIN, YEAR_MAX = 1960, 2000
ONEDRIVE = "OneDrive_2026-07-13"


@dataclass
class Fondo:
    name: str
    n_files: int = 0
    n_dirs: int = 0
    extensions: Counter = field(default_factory=Counter)
    top_level: list[str] = field(default_factory=list)
    causas: set[str] = field(default_factory=set)
    inventarios: list[str] = field(default_factory=list)
    samples: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def yy_to_year(yy: int) -> int | None:
    year = yy if yy >= 1000 else (1900 + yy if yy >= 70 else 2000 + yy)
    return year if YEAR_MIN <= year <= YEAR_MAX else None


def extract_causas(text: str) -> list[tuple[str, int]]:
    out, seen = [], set()
    for m in CAUSA_RE.finditer(text):
        num, yy = int(m.group("num")), int(m.group("yy"))
        year = yy_to_year(yy)
        if year is None:
            continue
        label = f"{num}-{year % 100:02d}"
        if label not in seen:
            seen.add(label)
            out.append((label, year))
    return out


def fondo_of(rel: Path) -> str | None:
    parts = rel.parts
    for i, p in enumerate(parts):
        if p.lower() == "fondos":
            return parts[i + 1] if i + 1 < len(parts) else None
    return parts[0] if parts else None


def infer_notes(name: str, top: list[str], samples: list[str]) -> list[str]:
    blob = " | ".join(top + samples)
    notes = []
    if sum(1 for t in top if extract_causas(t)) >= max(2, len(top) // 5):
        notes.append("Indexación dominante por causa judicial `xx-yy`.")
    if re.search(r"caja|legajo|tomo|volumen|carpeta\s*\d", blob, re.I):
        notes.append("Unidades de conservación (caja/legajo/tomo).")
    if re.search(r"persona|imputad|procesad|v[ií]ctima|detenid", blob, re.I):
        notes.append("Posible eje onomástico / por persona.")
    if re.search(r"fiscal|auditor|consejo|sentencia|expediente|pieza", blob, re.I):
        notes.append("Vocabulario procesal-penal/militar.")
    if "fasic" in name.lower() or ONEDRIVE.lower() in name.lower():
        notes.append("Traza institucional FASIC / descarga OneDrive.")
    if not notes:
        notes.append("Patrón poco claro solo por nombres → priorizar inventario Word.")
    return notes


def scan(root: Path) -> dict:
    fondos: dict[str, Fondo] = {}
    causa_fondos: dict[str, set[str]] = defaultdict(set)
    all_rel: list[str] = []
    n_files = n_dirs = 0

    for p in root.rglob("*"):
        if any(part in SKIP for part in p.parts):
            continue
        try:
            rel = p.relative_to(root)
        except ValueError:
            continue
        rel_s = str(rel).replace("\\", "/")
        all_rel.append(rel_s)
        fname = fondo_of(rel) or "_raiz_"
        f = fondos.setdefault(fname, Fondo(name=fname))

        if p.is_dir():
            n_dirs += 1
            f.n_dirs += 1
            parts = rel.parts
            if len(parts) == 3 and parts[0].lower() == "fondos":
                if parts[2] not in f.top_level:
                    f.top_level.append(parts[2])
            continue
        if not p.is_file():
            continue

        n_files += 1
        f.n_files += 1
        suf = p.suffix.lower() or "(sin_ext)"
        f.extensions[suf] += 1
        if len(f.samples) < 30:
            f.samples.append(rel_s)
        if "inventario" in p.name.lower() and suf in {".doc", ".docx"}:
            f.inventarios.append(rel_s)
        for label, year in extract_causas(rel_s):
            f.causas.add(label)
            causa_fondos[label].add(fname)

    for f in fondos.values():
        f.top_level = sorted(f.top_level)
        f.notes = infer_notes(f.name, f.top_level, f.samples)

    year_counts: Counter[int] = Counter()
    for label in causa_fondos:
        m = CAUSA_RE.search(label)
        if not m:
            continue
        y = yy_to_year(int(m.group("yy")))
        if y:
            year_counts[y] += 1

    multi = [
        {"causa": lab, "fondos": sorted(fs)}
        for lab, fs in sorted(causa_fondos.items())
        if len(fs) > 1
    ]

    under = [
        p.split(f"{ONEDRIVE}/", 1)[-1].split("/", 1)[0]
        for p in all_rel
        if f"{ONEDRIVE}/" in p
    ]
    fasic_split = sum("fasic" in u.lower() for u in set(under) if u) >= 2

    return {
        "root": str(root),
        "exported_at": datetime.now(tz=timezone.utc).isoformat(),
        "n_files": n_files,
        "n_dirs": n_dirs,
        "n_causas_unicas": len(causa_fondos),
        "causas_por_anio": {str(y): year_counts[y] for y in sorted(year_counts)},
        "causas_multi_fondo": multi,
        "fasic_split_detected": fasic_split,
        "fasic_branches": sorted({u for u in under if u}),
        "fondos": {
            name: {
                "n_files": f.n_files,
                "n_dirs": f.n_dirs,
                "n_causas": len(f.causas),
                "extensions": dict(f.extensions.most_common()),
                "top_level": f.top_level[:40],
                "inventarios": f.inventarios,
                "classification": f.notes,
                "sample_paths": f.samples[:15],
            }
            for name, f in sorted(fondos.items())
            if name != "_raiz_" or f.n_files or f.n_dirs
        },
    }


def render_md(data: dict) -> str:
    lines = [
        "# Consejos de Guerra — descripción sintética del corpus",
        "",
        "Lectura en ~1 minuto: volumen, ordenamiento por fondo, causas por año, solapes y FASIC.",
        "",
        f"_Fuente:_ `{data['root']}`  ",
        f"_Generado:_ {data['exported_at']}",
        "",
        "## 1. Ficha",
        "",
        f"| Fondos | Archivos | Carpetas | Causas únicas (`xx-yy`) |",
        f"| ---: | ---: | ---: | ---: |",
        f"| {len(data['fondos'])} | {data['n_files']} | {data['n_dirs']} | {data['n_causas_unicas']} |",
        "",
        "> **Clave.** `15-75` = causa nº **15** del año **1975** (`yy` = últimos 2 dígitos).",
        "",
        "## 2. Causas por año",
        "",
    ]
    cpa = data["causas_por_anio"]
    if not cpa:
        lines.append("Sin códigos `xx-yy` detectables en nombres de archivo/carpeta.")
    else:
        total = sum(cpa.values())
        lines += ["| Año | Causas | % |", "| ---: | ---: | ---: |"]
        for y, n in cpa.items():
            lines.append(f"| {y} | {n} | {100 * n / total:.0f}% |")
        lines.append(f"| **Total** | **{total}** | |")
        peak_y = max(cpa, key=lambda k: cpa[k])
        lines += ["", f"Pico: **{peak_y}** ({cpa[peak_y]} causas)."]
    lines += ["", "## 3. Fondos (cómo clasifican)", ""]
    lines.append(
        "Cada fondo ≈ recolección de un productor (investigador/institución). "
        "La etiqueta de clasificación es heurística por nombres; manda el Word *inventario*."
    )
    lines.append("")
    for name, f in data["fondos"].items():
        inv = "sí" if f["inventarios"] else "no"
        tip = f["classification"][0] if f["classification"] else "—"
        ext = ", ".join(f"{k}={v}" for k, v in list(f["extensions"].items())[:6]) or "—"
        lines.append(
            f"**{name}** — {f['n_files']} archivos · {f['n_causas']} causas · inventario Word: {inv}  \n"
            f"Clasificación: _{tip}_  \n"
            f"Extensiones: {ext}"
        )
        if f["top_level"]:
            preview = ", ".join(f"`{x}`" for x in f["top_level"][:12])
            extra = f" … +{len(f['top_level']) - 12}" if len(f["top_level"]) > 12 else ""
            lines.append(f"Primer nivel: {preview}{extra}")
        lines.append("")

    lines += ["## 4. ¿Misma causa en dos fondos = mismo archivo?", ""]
    multi = data["causas_multi_fondo"]
    if not multi:
        lines.append("No hay códigos compartidos entre fondos (por nombres).")
    else:
        lines.append(
            f"**{len(multi)}** códigos en ≥2 fondos. "
            "Interpretación: *misma Causa*, piezas posiblemente **complementarias** "
            "(o copias). No deduplicar a ciegas."
        )
        lines.append("")
        for item in multi[:15]:
            lines.append(f"- `{item['causa']}` → {', '.join(item['fondos'])}")
        if len(multi) > 15:
            lines.append(f"- _… +{len(multi) - 15} en el JSON_")
    lines += ["", "## 5. FASIC / OneDrive", ""]
    if data["fasic_split_detected"]:
        lines.append(
            "Descarga partida detectada bajo "
            f"`{ONEDRIVE}` (ramas: {', '.join(data['fasic_branches'][:8])}). "
            "Conviene unificar después; no bloquea la descripción del corpus."
        )
    else:
        lines.append("Sin split obvio de FASIC en esta pasada (o carpeta ausente).")
    lines += [
        "",
        "---",
        "_Solo nombres de rutas (+ inventarios si se pidió `--inventarios`). "
        "No abre PDFs ni imágenes._",
        "",
    ]
    return "\n".join(lines)


def try_inventarios(root: Path, out_dir: Path, data: dict) -> None:
    try:
        from docx import Document  # type: ignore
    except ImportError:
        print(
            "Aviso: para leer inventarios Word: python3 -m pip install python-docx --user",
            file=sys.stderr,
        )
        return
    inv_out = out_dir / "inventarios"
    inv_out.mkdir(parents=True, exist_ok=True)
    index = []
    for name, f in data["fondos"].items():
        for rel in f["inventarios"]:
            src = root / rel
            if src.suffix.lower() != ".docx":
                index.append({"fondo": name, "file": rel, "error": "solo .docx soportado aquí"})
                continue
            try:
                doc = Document(str(src))
                paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
                text = "\n".join(paras)
                safe = re.sub(r"[^\w\-]+", "_", name).strip("_") or "fondo"
                md = inv_out / f"inventario__{safe}.md"
                md.write_text(
                    f"# Inventario — {name}\n\n`{rel}`\n\n{text}\n",
                    encoding="utf-8",
                )
                index.append({"fondo": name, "file": rel, "extracted": str(md)})
            except Exception as e:  # noqa: BLE001
                index.append({"fondo": name, "file": rel, "error": str(e)})
    (inv_out / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def write_manifest_csv(root: Path, out_csv: Path) -> None:
    rows = []
    for p in sorted(root.rglob("*")):
        if any(part in SKIP for part in p.parts):
            continue
        try:
            rel = p.relative_to(root)
        except ValueError:
            continue
        kind = "dir" if p.is_dir() else ("file" if p.is_file() else "other")
        if kind == "other":
            continue
        size = p.stat().st_size if kind == "file" else ""
        rows.append(
            {
                "rel_path": str(rel).replace("\\", "/"),
                "kind": kind,
                "size": size,
                "suffix": p.suffix.lower() if kind == "file" else "",
                "depth": len(rel.parts),
                "fondo": fondo_of(rel) or "",
            }
        )
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f, fieldnames=["rel_path", "kind", "size", "suffix", "depth", "fondo"]
        )
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description="Descripción sintética del corpus Consejos de Guerra")
    ap.add_argument("root", type=Path, help="Ruta al dataset (2607 - Consejos de Guerra)")
    ap.add_argument(
        "-o",
        "--out",
        type=Path,
        default=None,
        help="Carpeta de salida (default: ./consejos_guerra_caracterizacion)",
    )
    ap.add_argument(
        "--inventarios",
        action="store_true",
        help="Extraer texto de Word *inventario* (.docx; necesita python-docx)",
    )
    ap.add_argument(
        "--print-only",
        action="store_true",
        help="Solo imprimir el markdown a stdout (sin escribir archivos)",
    )
    args = ap.parse_args()
    root = args.root.expanduser().resolve()
    if not root.is_dir():
        print(f"No existe el directorio: {root}", file=sys.stderr)
        return 2

    print(f"Escaneando: {root}", file=sys.stderr)
    data = scan(root)
    md = render_md(data)

    if args.print_only:
        print(md)
        return 0

    out = (args.out or Path("consejos_guerra_caracterizacion")).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "caracterizacion.md").write_text(md, encoding="utf-8")
    (out / "caracterizacion.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (out / "causas_por_anio.csv").open("w", encoding="utf-8") as f:
        f.write("year,n_causas\n")
        for y, n in data["causas_por_anio"].items():
            f.write(f"{y},{n}\n")
    write_manifest_csv(root, out / "manifest.csv")
    if args.inventarios:
        try_inventarios(root, out, data)

    print(md)
    print(f"\n[archivos escritos en {out}]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
