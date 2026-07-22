"""Resolución de la raíz del dataset privado de Consejos de Guerra."""

from __future__ import annotations

import os
from pathlib import Path

# Rutas candidatas (máquina local del investigador + symlink del repo).
DEFAULT_CANDIDATES: tuple[Path, ...] = (
    Path("data/external/consejos_guerra"),
    Path("/Users/camilogutierrez/STEM/nuestra-memoria/MuseoDeLaMemoria/2607 - Consejos de Guerra"),
    Path.home()
    / "STEM"
    / "nuestra-memoria"
    / "MuseoDeLaMemoria"
    / "2607 - Consejos de Guerra",
)

FASIC_ONEDRIVE_DIRNAME = "OneDrive_2026-07-13"


def load_dotenv(path: Path | None = None) -> None:
    """Carga .env simple (KEY=VALUE) sin dependencia externa."""
    env_path = path or Path(".env")
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def resolve_data_root(explicit: str | Path | None = None) -> Path:
    """Devuelve la raíz del dataset o lanza FileNotFoundError con pistas."""
    load_dotenv()
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    env = os.environ.get("CONSEJOS_GUERRA_ROOT", "").strip()
    if env:
        candidates.append(Path(env).expanduser())
    candidates.extend(DEFAULT_CANDIDATES)

    tried: list[str] = []
    for cand in candidates:
        tried.append(str(cand))
        if cand.is_dir():
            return cand.resolve()

    raise FileNotFoundError(
        "No se encontró el dataset privado de Consejos de Guerra.\n"
        "Opciones:\n"
        "  1) export CONSEJOS_GUERRA_ROOT='/ruta/al/2607 - Consejos de Guerra'\n"
        "  2) ln -s '/ruta/al/2607 - Consejos de Guerra' data/external/consejos_guerra\n"
        "  3) copiar .env.example → .env y completar CONSEJOS_GUERRA_ROOT\n"
        "Rutas intentadas:\n  - " + "\n  - ".join(tried)
    )


def fondos_dir(root: Path) -> Path:
    """Localiza el directorio Fondos (tolerante a mayúsculas / anidación)."""
    for name in ("Fondos", "fondos", "FONDOS"):
        p = root / name
        if p.is_dir():
            return p
    # A veces la raíz YA es Fondos
    if any(root.iterdir()):
        return root
    raise FileNotFoundError(f"No se encontró carpeta Fondos bajo {root}")
