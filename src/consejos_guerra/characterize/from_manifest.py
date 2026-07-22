"""Caracterización a partir de un manifiesto exportado (sin el archivo completo)."""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

from consejos_guerra.characterize.causas import extract_causa_codes, primary_causa_code
from consejos_guerra.characterize.scan import (
    DatasetCharacterization,
    FondoSummary,
    _infer_classification,
)
from consejos_guerra.paths import FASIC_ONEDRIVE_DIRNAME


def characterize_from_manifest(
    manifest_csv: Path,
    inventarios_dir: Path | None = None,
) -> DatasetCharacterization:
    """Reconstruye la caracterización solo con nombres (manifest.csv)."""
    with manifest_csv.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    by_fondo: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        fondo = (row.get("fondo") or "").strip() or "_raiz_"
        by_fondo[fondo].append(row)

    fondos: list[FondoSummary] = []
    causa_fondos: dict[str, set[str]] = defaultdict(set)
    total_files = 0
    total_dirs = 0

    for fondo_name, items in sorted(by_fondo.items()):
        files = [r for r in items if r.get("kind") == "file"]
        dirs = [r for r in items if r.get("kind") == "dir"]
        total_files += len(files)
        total_dirs += len(dirs)

        ext_counter: Counter[str] = Counter()
        for r in files:
            suf = (r.get("suffix") or "").strip() or "(sin_extension)"
            ext_counter[suf] += 1

        top: list[str] = []
        for r in items:
            parts = r["rel_path"].split("/")
            if len(parts) == 3 and parts[0].lower() == "fondos":
                top.append(parts[2])
            elif fondo_name != "_raiz_" and len(parts) == 2 and parts[0] == fondo_name:
                top.append(parts[1])
        top = sorted(set(top))

        samples = [r["rel_path"] for r in files[:40]]
        causa_set: set[str] = set()
        for r in items:
            for code in extract_causa_codes(r["rel_path"]):
                causa_set.add(code.label)
                causa_fondos[code.label].add(fondo_name)

        inventarios = [
            r["rel_path"]
            for r in files
            if "inventario" in Path(r["rel_path"]).name.lower()
            and (r.get("suffix") or "").lower() in {".doc", ".docx"}
        ]
        if inventarios_dir and inventarios_dir.is_dir():
            safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in fondo_name)
            for p in inventarios_dir.glob(f"{safe}__*"):
                if p.suffix.lower() in {".doc", ".docx"}:
                    inventarios.append(f"[export]{p.name}")

        fondo_path = next(
            (r["rel_path"] for r in dirs if r["rel_path"].rstrip("/").endswith(fondo_name)),
            fondo_name,
        )
        fondos.append(
            FondoSummary(
                name=fondo_name,
                path=fondo_path,
                n_dirs=len(dirs),
                n_files=len(files),
                extensions=dict(ext_counter.most_common()),
                top_level_entries=top[:80],
                sample_paths=samples,
                causa_codes=sorted(causa_set),
                n_causas_unicas=len(causa_set),
                classification_notes=_infer_classification(Path(fondo_path), top, samples),
                inventario_files=inventarios,
            )
        )

    all_paths = [r["rel_path"] for r in rows]
    fasic_paths = [p for p in all_paths if FASIC_ONEDRIVE_DIRNAME in p][:30]
    under = [
        p.split(f"{FASIC_ONEDRIVE_DIRNAME}/", 1)[-1].split("/", 1)[0]
        for p in all_paths
        if f"{FASIC_ONEDRIVE_DIRNAME}/" in p
    ]
    uniq_top = {u for u in under if u}
    fasic_split = sum("fasic" in u.lower() for u in uniq_top) >= 2

    unique_labels = set(causa_fondos.keys())
    causa_year_unique: Counter[int] = Counter()
    per_fondo_years: dict[str, Counter[int]] = defaultdict(Counter)
    for label, fs in causa_fondos.items():
        code = primary_causa_code(label)
        if not code:
            continue
        causa_year_unique[code.year] += 1
        for fname in fs:
            per_fondo_years[fname][code.year] += 1

    multi = [
        {
            "causa": label,
            "fondos": sorted(fs),
            "n_fondos": len(fs),
            "interpretacion": (
                "Misma causa en ≥2 fondos: candidato a alineación en el grafo "
                "(copia o material complementario). No deduplicar a ciegas."
            ),
        }
        for label, fs in sorted(causa_fondos.items())
        if len(fs) > 1
    ]

    return DatasetCharacterization(
        root=str(manifest_csv.parent),
        fondos=fondos,
        causas_por_anio={str(y): causa_year_unique[y] for y in sorted(causa_year_unique)},
        causas_por_anio_por_fondo={
            fondo: {str(y): c[y] for y in sorted(c)} for fondo, c in per_fondo_years.items()
        },
        causas_multi_fondo=multi,
        total_causas_unicas=len(unique_labels),
        total_files=total_files,
        total_dirs=total_dirs,
        fasic_split_detected=fasic_split,
        fasic_split_paths=fasic_paths,
        warnings=[],
    )
