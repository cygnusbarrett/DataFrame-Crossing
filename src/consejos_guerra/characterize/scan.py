"""Barrido preliminar del dataset por nombres de archivos y carpetas."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

from consejos_guerra.characterize.causas import CausaCode, extract_causa_codes, primary_causa_code
from consejos_guerra.paths import FASIC_ONEDRIVE_DIRNAME, fondos_dir

SKIP_DIR_NAMES = {
    ".git",
    ".DS_Store",
    "__MACOSX",
    ".ipynb_checkpoints",
    "Thumbs.db",
}

INVENTARIO_NAME_RE = re.compile(r"inventario", re.IGNORECASE)
WORD_SUFFIXES = {".doc", ".docx"}


@dataclass
class FondoSummary:
    name: str
    path: str
    n_dirs: int = 0
    n_files: int = 0
    extensions: dict[str, int] = field(default_factory=dict)
    top_level_entries: list[str] = field(default_factory=list)
    sample_paths: list[str] = field(default_factory=list)
    causa_codes: list[str] = field(default_factory=list)
    n_causas_unicas: int = 0
    classification_notes: list[str] = field(default_factory=list)
    inventario_files: list[str] = field(default_factory=list)


@dataclass
class DatasetCharacterization:
    root: str
    fondos: list[FondoSummary]
    causas_por_anio: dict[str, int]
    causas_por_anio_por_fondo: dict[str, dict[str, int]]
    causas_multi_fondo: list[dict[str, Any]]
    total_causas_unicas: int
    total_files: int
    total_dirs: int
    fasic_split_detected: bool
    fasic_split_paths: list[str]
    warnings: list[str]


def _iter_entries(root: Path) -> Iterable[Path]:
    for p in root.rglob("*"):
        if any(part in SKIP_DIR_NAMES for part in p.parts):
            continue
        yield p


def _ext(path: Path) -> str:
    suf = path.suffix.lower()
    return suf if suf else "(sin_extension)"


def _infer_classification(fondo_path: Path, top_entries: list[str], sample: list[str]) -> list[str]:
    """Heurísticas de sistema de clasificación a partir de nombres."""
    notes: list[str] = []
    names = top_entries + sample
    joined = " | ".join(names)

    causa_hits = sum(1 for n in names if primary_causa_code(n))
    if causa_hits >= max(3, len(top_entries) // 4):
        notes.append(
            "Indexación dominante por código de causa xx-yy "
            "(número correlativo + últimos dos dígitos del año)."
        )

    if re.search(r"caja|box|legajo|tomo|volumen|carpeta\s*\d", joined, re.I):
        notes.append("Presencia de unidades de conservación (caja/legajo/tomo/carpeta numerada).")

    if re.search(r"\b(pdf|jpg|jpeg|tif|tiff|png)\b", joined, re.I) or any(
        n.lower().endswith((".pdf", ".jpg", ".jpeg", ".tif", ".tiff", ".png")) for n in names
    ):
        notes.append("Material digitalizado (imágenes/PDF) además de estructura de carpetas.")

    if re.search(r"persona|imputad|procesad|victima|víctima|detenid", joined, re.I):
        notes.append("Posible eje onomástico / por persona procesada o víctima.")

    if re.search(r"fiscal|auditor|consejo|sentencia|expediente|pieza", joined, re.I):
        notes.append("Vocabulario procesal-penal/militar (expediente, sentencia, consejo, fiscal).")

    if re.search(r"fasic|vicaría|codepu|agrupaci[oó]n|fundaci[oó]n|archivo", joined, re.I):
        notes.append("Referencias institucionales en nombres (posible sub-serie por productor).")

    if FASIC_ONEDRIVE_DIRNAME.lower() in fondo_path.name.lower() or any(
        FASIC_ONEDRIVE_DIRNAME in s for s in names
    ):
        notes.append(
            "Traza de descarga OneDrive: revisar fusión de ramas antes de usar como fuente canónica."
        )

    if not notes:
        notes.append(
            "Clasificación no evidente solo por nombres; priorizar lectura del Word de inventario."
        )
    return notes


def list_fondos(root: Path) -> list[Path]:
    fdir = fondos_dir(root)
    fondos = sorted([p for p in fdir.iterdir() if p.is_dir() and p.name not in SKIP_DIR_NAMES])
    if not fondos:
        # Si no hay subcarpetas, tratar cada hijo de root como fondo
        fondos = sorted([p for p in root.iterdir() if p.is_dir() and p.name not in SKIP_DIR_NAMES])
    return fondos


def characterize_fondo(fondo: Path, root: Path, max_samples: int = 40) -> FondoSummary:
    rel_fondo = str(fondo.relative_to(root)) if fondo.is_relative_to(root) else str(fondo)
    top = sorted([p.name for p in fondo.iterdir() if p.name not in SKIP_DIR_NAMES])
    ext_counter: Counter[str] = Counter()
    n_files = 0
    n_dirs = 0
    samples: list[str] = []
    causa_set: set[str] = set()
    inventarios: list[str] = []

    for p in _iter_entries(fondo):
        if p.is_dir():
            n_dirs += 1
            continue
        if not p.is_file():
            continue
        n_files += 1
        ext_counter[_ext(p)] += 1
        try:
            rel = str(p.relative_to(fondo))
        except ValueError:
            rel = str(p)
        if len(samples) < max_samples:
            samples.append(rel)
        if INVENTARIO_NAME_RE.search(p.name) and p.suffix.lower() in WORD_SUFFIXES:
            inventarios.append(rel)
        # Códigos en ruta completa (carpeta + archivo)
        for code in extract_causa_codes(rel.replace("\\", "/")):
            causa_set.add(code.label)

    summary = FondoSummary(
        name=fondo.name,
        path=rel_fondo,
        n_dirs=n_dirs,
        n_files=n_files,
        extensions=dict(ext_counter.most_common()),
        top_level_entries=top[:80],
        sample_paths=samples,
        causa_codes=sorted(causa_set),
        n_causas_unicas=len(causa_set),
        classification_notes=_infer_classification(fondo, top, samples),
        inventario_files=inventarios,
    )
    return summary


def detect_fasic_split(root: Path) -> tuple[bool, list[str]]:
    """Detecta la carpeta OneDrive del Fondo FASIC y posibles ramas partidas."""
    hits: list[Path] = []
    for p in root.rglob("*"):
        if p.is_dir() and FASIC_ONEDRIVE_DIRNAME.lower() in p.name.lower():
            hits.append(p)
        if p.is_dir() and p.name.lower() in {"fasic", "fondo fasic", "fondo_fasic"}:
            hits.append(p)

    # Deduplicar por resolve
    uniq: list[Path] = []
    seen: set[Path] = set()
    for h in hits:
        r = h.resolve()
        if r not in seen:
            seen.add(r)
            uniq.append(h)

    paths = [str(p) for p in uniq]
    if not uniq:
        return False, []

    # Heurística de split: más de una raíz FASIC/OneDrive, o hijos duplicados/top-level raros
    onedrive = [p for p in uniq if FASIC_ONEDRIVE_DIRNAME.lower() in p.name.lower()]
    if onedrive:
        od = onedrive[0]
        children = [c for c in od.iterdir() if c.name not in SKIP_DIR_NAMES]
        names = [c.name for c in children]
        # Patrones típicos de descarga rota: dos carpetas espejo, "FASIC" + otra rama, zips sueltos
        splitish = False
        if len(children) >= 2:
            lower = [n.lower() for n in names]
            if sum("fasic" in n for n in lower) >= 2:
                splitish = True
            if any(n.endswith(".zip") for n in lower) and any(
                (od / n).is_dir() for n in names
            ):
                splitish = True
            # Dos árboles top-level sin inventario unificado
            if len(children) == 2 and all(c.is_dir() for c in children):
                splitish = True
        return splitish or len(onedrive) > 1, [str(od)] + [
            str(c) for c in children[:20]
        ]

    return len(uniq) > 1, paths


def characterize_dataset(root: Path) -> DatasetCharacterization:
    fondos_paths = list_fondos(root)
    fondos: list[FondoSummary] = []
    # causa_label -> set de fondos
    causa_fondos: dict[str, set[str]] = defaultdict(set)
    causa_year: Counter[int] = Counter()
    causa_year_fondo: dict[str, Counter[int]] = defaultdict(Counter)
    total_files = 0
    total_dirs = 0
    warnings: list[str] = []

    if not fondos_paths:
        warnings.append("No se detectaron fondos (subdirectorios) bajo la raíz.")

    for fp in fondos_paths:
        s = characterize_fondo(fp, root)
        fondos.append(s)
        total_files += s.n_files
        total_dirs += s.n_dirs
        for label in s.causa_codes:
            causa_fondos[label].add(s.name)
            # label es N-YY
            code = primary_causa_code(label)
            if code:
                causa_year[code.year] += 1
                causa_year_fondo[s.name][code.year] += 1

    # Recalcular años de forma única global (evitar doble conteo por fondo)
    unique_labels = set(causa_fondos.keys())
    causa_year_unique: Counter[int] = Counter()
    for label in unique_labels:
        code = primary_causa_code(label)
        if code:
            causa_year_unique[code.year] += 1

    multi = []
    for label, fs in sorted(causa_fondos.items()):
        if len(fs) > 1:
            multi.append(
                {
                    "causa": label,
                    "fondos": sorted(fs),
                    "n_fondos": len(fs),
                    "interpretacion": (
                        "Misma causa indexada en más de un fondo. "
                        "Puede ser copia redundante O material complementario "
                        "(distinta selección documental / notas de investigador). "
                        "Comparar hashes y lectura de inventarios antes de deduplicar."
                    ),
                }
            )

    fasic_split, fasic_paths = detect_fasic_split(root)

    return DatasetCharacterization(
        root=str(root),
        fondos=fondos,
        causas_por_anio={str(y): causa_year_unique[y] for y in sorted(causa_year_unique)},
        causas_por_anio_por_fondo={
            fondo: {str(y): c[y] for y in sorted(c)} for fondo, c in causa_year_fondo.items()
        },
        causas_multi_fondo=multi,
        total_causas_unicas=len(unique_labels),
        total_files=total_files,
        total_dirs=total_dirs,
        fasic_split_detected=fasic_split,
        fasic_split_paths=fasic_paths,
        warnings=warnings,
    )


def to_jsonable(result: DatasetCharacterization) -> dict[str, Any]:
    return {
        "root": result.root,
        "total_files": result.total_files,
        "total_dirs": result.total_dirs,
        "total_causas_unicas": result.total_causas_unicas,
        "causas_por_anio": result.causas_por_anio,
        "causas_por_anio_por_fondo": result.causas_por_anio_por_fondo,
        "causas_multi_fondo": result.causas_multi_fondo,
        "fasic_split_detected": result.fasic_split_detected,
        "fasic_split_paths": result.fasic_split_paths,
        "warnings": result.warnings,
        "fondos": [asdict(f) for f in result.fondos],
    }


def write_outputs(result: DatasetCharacterization, out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    json_path = out_dir / "caracterizacion.json"
    json_path.write_text(
        json.dumps(to_jsonable(result), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    paths["json"] = json_path

    md = render_markdown_report(result)
    md_path = out_dir / "caracterizacion.md"
    md_path.write_text(md, encoding="utf-8")
    paths["md"] = md_path

    # CSV simple de causas por año
    csv_path = out_dir / "causas_por_anio.csv"
    lines = ["year,n_causas"]
    for y, n in result.causas_por_anio.items():
        lines.append(f"{y},{n}")
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    paths["csv"] = csv_path
    return paths


def render_markdown_report(result: DatasetCharacterization) -> str:
    lines: list[str] = []
    lines.append("# Caracterización preliminar — Consejos de Guerra")
    lines.append("")
    lines.append(f"**Raíz:** `{result.root}`")
    lines.append("")
    lines.append(
        f"Archivos: **{result.total_files}** · Carpetas: **{result.total_dirs}** · "
        f"Causas únicas (por código xx-yy en nombres): **{result.total_causas_unicas}**"
    )
    lines.append("")
    lines.append("## Causas judiciales por año")
    lines.append("")
    if not result.causas_por_anio:
        lines.append("_No se extrajeron códigos xx-yy desde nombres de archivo/carpeta._")
    else:
        lines.append("| Año | N° causas (únicas) |")
        lines.append("| ---: | ---: |")
        for y, n in result.causas_por_anio.items():
            lines.append(f"| {y} | {n} |")
    lines.append("")
    lines.append("## Fondos")
    lines.append("")
    for f in result.fondos:
        lines.append(f"### {f.name}")
        lines.append("")
        lines.append(f"- Ruta relativa: `{f.path}`")
        lines.append(f"- Archivos: {f.n_files} · dirs: {f.n_dirs} · causas únicas: {f.n_causas_unicas}")
        if f.extensions:
            top_ext = ", ".join(f"{k}={v}" for k, v in list(f.extensions.items())[:12])
            lines.append(f"- Extensiones: {top_ext}")
        if f.inventario_files:
            lines.append("- Inventarios Word: " + ", ".join(f"`{x}`" for x in f.inventario_files))
        lines.append("- Sistema de clasificación (heurística por nombres):")
        for note in f.classification_notes:
            lines.append(f"  - {note}")
        if f.top_level_entries:
            preview = ", ".join(f"`{x}`" for x in f.top_level_entries[:25])
            more = "" if len(f.top_level_entries) <= 25 else f" … (+{len(f.top_level_entries) - 25})"
            lines.append(f"- Entradas de primer nivel: {preview}{more}")
        lines.append("")

    lines.append("## Solapamiento de causas entre fondos")
    lines.append("")
    if not result.causas_multi_fondo:
        lines.append(
            "No se detectaron códigos de causa compartidos entre fondos "
            "(según nombres). Esto no descarta duplicados semánticos."
        )
    else:
        lines.append(
            f"Se encontraron **{len(result.causas_multi_fondo)}** códigos presentes en ≥2 fondos."
        )
        lines.append("")
        lines.append(
            "Interpretación: coincidencia de código **no implica** archivo idéntico. "
            "Dos investigadores pueden haber reunido piezas distintas (o parcialmente "
            "solapadas) sobre la misma causa. Tratarlos como **candidatos a alineación** "
            "en el grafo, no como deduplicación automática."
        )
        lines.append("")
        for item in result.causas_multi_fondo[:50]:
            lines.append(
                f"- `{item['causa']}` → {', '.join(item['fondos'])} ({item['n_fondos']} fondos)"
            )
        if len(result.causas_multi_fondo) > 50:
            lines.append(f"- … (+{len(result.causas_multi_fondo) - 50} más; ver JSON)")
    lines.append("")

    lines.append("## Fondo FASIC / OneDrive")
    lines.append("")
    if result.fasic_split_detected:
        lines.append(
            "**Posible descarga partida detectada.** Ejecutar "
            "`python -m consejos_guerra.fasic.reorganize --apply` tras revisar el dry-run."
        )
    else:
        lines.append("No se detectó un split obvio (o la carpeta OneDrive aún no está visible).")
    for p in result.fasic_split_paths:
        lines.append(f"- `{p}`")
    lines.append("")

    if result.warnings:
        lines.append("## Advertencias")
        lines.append("")
        for w in result.warnings:
            lines.append(f"- {w}")
        lines.append("")

    lines.append("---")
    lines.append(
        "_Caracterización preliminar basada solo en nombres de rutas. "
        "Los inventarios Word aportan la descripción canónica de cada fondo._"
    )
    lines.append("")
    return "\n".join(lines)
