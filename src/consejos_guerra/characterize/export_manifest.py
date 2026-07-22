"""Exportación ligera del dataset para análisis remoto (solo nombres + inventarios)."""

from __future__ import annotations

import csv
import json
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from consejos_guerra.inventarios.extract import find_inventario_word_files

SKIP = {".git", ".DS_Store", "__MACOSX", ".ipynb_checkpoints", "Thumbs.db"}


@dataclass
class ManifestEntry:
    rel_path: str
    kind: str  # file | dir
    size: int | None
    suffix: str | None
    mtime_iso: str | None
    depth: int
    fondo: str | None


def _fondo_of(rel: Path) -> str | None:
    parts = rel.parts
    for i, part in enumerate(parts):
        if part.lower() == "fondos":
            if i + 1 < len(parts):
                return parts[i + 1]
            return None  # el propio dir Fondos no es un fondo
    return parts[0] if parts else None


def build_manifest(root: Path) -> list[ManifestEntry]:
    entries: list[ManifestEntry] = []
    for p in sorted(root.rglob("*")):
        if any(part in SKIP for part in p.parts):
            continue
        try:
            rel = p.relative_to(root)
        except ValueError:
            continue
        depth = len(rel.parts)
        fondo = _fondo_of(rel)
        if p.is_dir():
            entries.append(
                ManifestEntry(
                    rel_path=str(rel).replace("\\", "/"),
                    kind="dir",
                    size=None,
                    suffix=None,
                    mtime_iso=None,
                    depth=depth,
                    fondo=fondo,
                )
            )
            continue
        if not p.is_file():
            continue
        try:
            st = p.stat()
            mtime = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat()
            size = st.st_size
        except OSError:
            mtime, size = None, None
        entries.append(
            ManifestEntry(
                rel_path=str(rel).replace("\\", "/"),
                kind="file",
                size=size,
                suffix=p.suffix.lower() or None,
                mtime_iso=mtime,
                depth=depth,
                fondo=fondo,
            )
        )
    return entries


def write_manifest_csv(entries: list[ManifestEntry], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["rel_path", "kind", "size", "suffix", "mtime_iso", "depth", "fondo"],
        )
        w.writeheader()
        for e in entries:
            w.writerow(asdict(e))


def write_tree_txt(entries: list[ManifestEntry], path: Path, max_depth: int | None = None) -> None:
    """Árbol compacto solo con nombres (pedagógico para lectura humana)."""
    lines: list[str] = []
    for e in entries:
        if max_depth is not None and e.depth > max_depth:
            continue
        indent = "  " * (e.depth - 1)
        name = e.rel_path.rsplit("/", 1)[-1]
        suffix = "/" if e.kind == "dir" else ""
        lines.append(f"{indent}{name}{suffix}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def copy_inventarios(root: Path, dest_dir: Path) -> list[dict[str, str]]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    copied: list[dict[str, str]] = []
    for src in find_inventario_word_files(root):
        rel = src.relative_to(root)
        # Prefijo por fondo para evitar colisiones de nombre
        fondo = _fondo_of(rel) or "sin_fondo"
        safe_fondo = "".join(c if c.isalnum() or c in "-_" else "_" for c in fondo)
        dest = dest_dir / f"{safe_fondo}__{src.name}"
        n = 2
        while dest.exists():
            dest = dest_dir / f"{safe_fondo}__{src.stem}_{n}{src.suffix}"
            n += 1
        shutil.copy2(src, dest)
        copied.append({"source": str(rel).replace("\\", "/"), "copied_as": dest.name})
    return copied


def export_for_remote_analysis(root: Path, out_dir: Path) -> dict[str, Any]:
    """
    Empaqueta lo mínimo para caracterización remota exhaustiva:
    - manifest.csv (todos los paths)
    - tree.txt (vista pedagógica)
    - inventarios/ (solo Word *inventario*)
    - meta.json
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    entries = build_manifest(root)
    write_manifest_csv(entries, out_dir / "manifest.csv")
    write_tree_txt(entries, out_dir / "tree.txt")
    inv = copy_inventarios(root, out_dir / "inventarios_word")
    (out_dir / "inventarios_word" / "index.json").write_text(
        json.dumps(inv, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    n_files = sum(1 for e in entries if e.kind == "file")
    n_dirs = sum(1 for e in entries if e.kind == "dir")
    fondos = sorted({e.fondo for e in entries if e.fondo})
    meta = {
        "exported_at": datetime.now(tz=timezone.utc).isoformat(),
        "source_root": str(root),
        "n_files": n_files,
        "n_dirs": n_dirs,
        "n_fondos_guess": len(fondos),
        "fondos_guess": fondos,
        "n_inventarios_copiados": len(inv),
        "contents": [
            "manifest.csv — un path por fila (nombres + tamaño + fondo)",
            "tree.txt — árbol legible",
            "inventarios_word/ — solo Word cuyo nombre contiene 'inventario'",
            "meta.json — este resumen",
        ],
        "nota": (
            "No incluye PDFs ni imágenes. Suficiente para caracterización por nombres, "
            "stats de causas xx-yy, clasificación por fondo y lectura de inventarios."
        ),
    }
    (out_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (out_dir / "README.md").write_text(
        "\n".join(
            [
                "# Manifiesto para análisis remoto",
                "",
                f"- Origen: `{root}`",
                f"- Archivos: **{n_files}** · carpetas: **{n_dirs}** · fondos: **{len(fondos)}**",
                f"- Inventarios Word copiados: **{len(inv)}**",
                "",
                "Commitá / subí esta carpeta al repo y pedile al agente:",
                "`caracterizá a partir de data/inputs/manifest_consejos_guerra`.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return meta
