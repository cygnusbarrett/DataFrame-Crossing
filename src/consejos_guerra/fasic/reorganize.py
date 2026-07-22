"""Reorganización del Fondo FASIC partido por error de descarga OneDrive."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from consejos_guerra.paths import FASIC_ONEDRIVE_DIRNAME

SKIP = {".DS_Store", "__MACOSX", ".ipynb_checkpoints", "Thumbs.db"}


@dataclass
class MergeAction:
    action: str  # move | skip_duplicate | conflict
    src: str
    dest: str
    detail: str = ""


@dataclass
class ReorganizePlan:
    onedrive_root: str
    canonical_root: str
    branch_dirs: list[str]
    actions: list[MergeAction] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def n_moves(self) -> int:
        return sum(1 for a in self.actions if a.action == "move")

    @property
    def n_dupes(self) -> int:
        return sum(1 for a in self.actions if a.action == "skip_duplicate")

    @property
    def n_conflicts(self) -> int:
        return sum(1 for a in self.actions if a.action == "conflict")


def find_onedrive_fasic(dataset_root: Path) -> Path | None:
    """Busca `.../Fondos/OneDrive_2026-07-13` o equivalente."""
    direct = list(dataset_root.rglob(FASIC_ONEDRIVE_DIRNAME))
    for p in direct:
        if p.is_dir():
            return p
    # Variantes de nombre
    for p in dataset_root.rglob("*"):
        if p.is_dir() and FASIC_ONEDRIVE_DIRNAME.lower() in p.name.lower():
            return p
    return None


def _file_digest(path: Path, chunk: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _rank_branch(path: Path) -> tuple[int, int, str]:
    """Prioriza la rama 'principal' al elegir destino canónico."""
    name = path.name.lower()
    score = 0
    if name == "fasic":
        score += 100
    if "fasic" in name:
        score += 50
    if "fondo" in name:
        score += 20
    if re.search(r"\(\d+\)", name):
        score -= 30
    if name.startswith("onedrive"):
        score -= 10
    # Más archivos ≈ rama más completa
    try:
        n_files = sum(1 for p in path.rglob("*") if p.is_file())
    except OSError:
        n_files = 0
    return (score, n_files, name)


def discover_branches(onedrive_root: Path) -> list[Path]:
    children = [
        c
        for c in onedrive_root.iterdir()
        if c.name not in SKIP and not c.name.startswith(".")
    ]
    dirs = [c for c in children if c.is_dir()]
    files = [c for c in children if c.is_file()]

    # Caso A: dos (o más) carpetas top-level = ramas partidas
    if len(dirs) >= 2:
        return sorted(dirs, key=_rank_branch, reverse=True)

    # Caso B: una carpeta + archivos sueltos / zip
    if len(dirs) == 1 and files:
        return dirs

    # Caso C: anidación OneDrive/OneDrive/...
    nested = [c for c in dirs if FASIC_ONEDRIVE_DIRNAME.lower() in c.name.lower()]
    if nested:
        return discover_branches(nested[0])

    # Caso D: una sola carpeta FASIC ya casi canónica, pero con sub-ramas internas
    if len(dirs) == 1:
        inner = [
            c
            for c in dirs[0].iterdir()
            if c.is_dir() and c.name not in SKIP and "fasic" in c.name.lower()
        ]
        if len(inner) >= 2:
            return sorted(inner, key=_rank_branch, reverse=True)
        return dirs

    return dirs


def build_plan(
    dataset_root: Path,
    onedrive_root: Path | None = None,
    canonical_name: str = "Fondo FASIC",
) -> ReorganizePlan:
    od = onedrive_root or find_onedrive_fasic(dataset_root)
    if od is None:
        raise FileNotFoundError(
            f"No se encontró '{FASIC_ONEDRIVE_DIRNAME}' bajo {dataset_root}"
        )

    branches = discover_branches(od)
    # Destino canónico: hermano de OneDrive dentro de Fondos (o dentro de od si es lo único)
    parent = od.parent
    canonical = parent / canonical_name

    notes: list[str] = [
        f"OneDrive root: {od}",
        f"Ramas detectadas ({len(branches)}): "
        + ", ".join(b.name for b in branches),
        f"Destino canónico propuesto: {canonical}",
        "Estrategia: la rama de mayor score aporta la base; el resto se fusiona "
        "por ruta relativa. Duplicados byte-idénticos se omiten; conflictos se "
        "reportan sin sobrescribir.",
    ]

    actions: list[MergeAction] = []
    if not branches:
        notes.append("No hay ramas/dirs que fusionar.")
        return ReorganizePlan(
            onedrive_root=str(od),
            canonical_root=str(canonical),
            branch_dirs=[],
            actions=actions,
            notes=notes,
        )

    primary = branches[0]
    others = branches[1:]

    # 1) Si canonical no existe, mover/copiar estructura de primary
    promoting_primary = not canonical.exists()
    if promoting_primary:
        actions.append(
            MergeAction(
                action="move",
                src=str(primary),
                dest=str(canonical),
                detail="Promover rama principal a Fondo FASIC canónico",
            )
        )
    else:
        notes.append("El destino canónico ya existe; solo se fusionarán ramas adicionales.")

    def rel_under(branch: Path, file_path: Path) -> Path:
        return file_path.relative_to(branch)

    def resolve_existing_counterpart(rel: Path) -> Path | None:
        """Archivo que ocupará (o ya ocupa) canonical/rel tras promover primary."""
        if canonical.exists():
            candidate = canonical / rel
            return candidate if candidate.is_file() else None
        if promoting_primary:
            candidate = primary / rel
            return candidate if candidate.is_file() else None
        return None

    # 2) Fusionar otras ramas
    for branch in others:
        for src in branch.rglob("*"):
            if any(part in SKIP for part in src.parts):
                continue
            if not src.is_file():
                continue
            rel = rel_under(branch, src)
            dest = canonical / rel
            counterpart = resolve_existing_counterpart(rel)

            if counterpart is not None:
                try:
                    same = _file_digest(src) == _file_digest(counterpart)
                except OSError as e:
                    actions.append(
                        MergeAction(
                            "conflict",
                            str(src),
                            str(dest),
                            f"No se pudo comparar: {e}",
                        )
                    )
                    continue
                if same:
                    actions.append(
                        MergeAction(
                            "skip_duplicate",
                            str(src),
                            str(dest),
                            "SHA-256 idéntico",
                        )
                    )
                else:
                    alt = dest.with_name(f"{dest.stem}__from_{branch.name}{dest.suffix}")
                    actions.append(
                        MergeAction(
                            "conflict",
                            str(src),
                            str(alt),
                            "Mismo path relativo, contenido distinto — conservar ambas con sufijo",
                        )
                    )
            else:
                actions.append(
                    MergeAction(
                        "move",
                        str(src),
                        str(dest),
                        f"Fusionar desde rama '{branch.name}'",
                    )
                )

    # Archivos sueltos en la raíz OneDrive
    for src in od.iterdir():
        if src.name in SKIP or src.is_dir():
            continue
        if src.is_file():
            dest = canonical / src.name
            actions.append(
                MergeAction(
                    "move",
                    str(src),
                    str(dest),
                    "Archivo suelto en raíz OneDrive → canónico",
                )
            )

    return ReorganizePlan(
        onedrive_root=str(od),
        canonical_root=str(canonical),
        branch_dirs=[str(b) for b in branches],
        actions=actions,
        notes=notes,
    )


def apply_plan(plan: ReorganizePlan, dry_run: bool = True) -> dict[str, Any]:
    """Ejecuta el plan. dry_run=True no modifica el disco."""
    results = {
        "dry_run": dry_run,
        "moved": 0,
        "skipped": 0,
        "conflicts_materialized": 0,
        "errors": [],
    }

    def ensure_parent(path: Path) -> None:
        if not dry_run:
            path.parent.mkdir(parents=True, exist_ok=True)

    for act in plan.actions:
        src = Path(act.src)
        dest = Path(act.dest)
        try:
            if act.action == "skip_duplicate":
                results["skipped"] += 1
                continue
            if act.action == "conflict":
                # Materializar copia con sufijo para no perder evidencia
                if dry_run:
                    results["conflicts_materialized"] += 1
                    continue
                ensure_parent(dest)
                if src.is_dir() and not dest.exists() and act.detail.startswith("Promover"):
                    shutil.move(str(src), str(dest))
                else:
                    if src.is_file():
                        shutil.copy2(str(src), str(dest))
                results["conflicts_materialized"] += 1
                continue
            if act.action == "move":
                if dry_run:
                    results["moved"] += 1
                    continue
                ensure_parent(dest)
                if src.is_dir() and act.detail.startswith("Promover"):
                    shutil.move(str(src), str(dest))
                elif src.is_file():
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(src), str(dest))
                else:
                    # dir intermedio u otro: intentar move
                    shutil.move(str(src), str(dest))
                results["moved"] += 1
        except Exception as e:  # noqa: BLE001 — reportar y seguir
            results["errors"].append({"src": act.src, "dest": act.dest, "error": str(e)})

    # Tras aplicar, dejar un marcador README en OneDrive explicando la mudanza
    if not dry_run:
        od = Path(plan.onedrive_root)
        marker = od / "README_REORGANIZADO.txt"
        try:
            marker.write_text(
                "Contenido FASIC reorganizado hacia:\n"
                f"  {plan.canonical_root}\n"
                "Esta carpeta OneDrive puede archivarse tras verificar la fusión.\n",
                encoding="utf-8",
            )
        except OSError as e:
            results["errors"].append({"src": str(marker), "dest": "", "error": str(e)})

    return results


def plan_to_dict(plan: ReorganizePlan) -> dict[str, Any]:
    return {
        "onedrive_root": plan.onedrive_root,
        "canonical_root": plan.canonical_root,
        "branch_dirs": plan.branch_dirs,
        "notes": plan.notes,
        "counts": {
            "moves": plan.n_moves,
            "duplicates": plan.n_dupes,
            "conflicts": plan.n_conflicts,
        },
        "actions": [asdict(a) for a in plan.actions],
    }


def write_plan(plan: ReorganizePlan, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(plan_to_dict(plan), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return out_path
