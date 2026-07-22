"""CLI: caracterización, inventarios y reorganización FASIC."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from consejos_guerra.characterize.scan import characterize_dataset, write_outputs
from consejos_guerra.fasic.reorganize import apply_plan, build_plan, write_plan
from consejos_guerra.inventarios.extract import extract_inventarios, write_inventario_outputs
from consejos_guerra.paths import resolve_data_root

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Consejos de Guerra — caracterización de fondos (base para grafo multimodal).",
)
console = Console()


def _root(data_root: Optional[Path]) -> Path:
    try:
        return resolve_data_root(data_root)
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=2) from e


@app.command("characterize")
def characterize_cmd(
    data_root: Optional[Path] = typer.Option(
        None, "--data-root", "-d", help="Raíz del dataset privado"
    ),
    out_dir: Path = typer.Option(
        Path("docs/caracterizacion/generado"),
        "--out",
        "-o",
        help="Directorio de salida",
    ),
) -> None:
    """Barrido por nombres: fondos, causas xx-yy por año, solapes y FASIC."""
    root = _root(data_root)
    console.print(f"[bold]Dataset:[/bold] {root}")
    result = characterize_dataset(root)
    paths = write_outputs(result, out_dir)

    table = Table(title="Causas únicas por año")
    table.add_column("Año", justify="right")
    table.add_column("N°", justify="right")
    for y, n in result.causas_por_anio.items():
        table.add_row(y, str(n))
    if result.causas_por_anio:
        console.print(table)
    else:
        console.print("[yellow]Sin códigos xx-yy detectados en nombres.[/yellow]")

    console.print(
        f"Fondos: {len(result.fondos)} · archivos: {result.total_files} · "
        f"causas únicas: {result.total_causas_unicas} · "
        f"multi-fondo: {len(result.causas_multi_fondo)}"
    )
    if result.fasic_split_detected:
        console.print("[magenta]FASIC: posible split OneDrive detectado.[/magenta]")
    for label, p in paths.items():
        console.print(f"  [{label}] {p}")


@app.command("inventarios")
def inventarios_cmd(
    data_root: Optional[Path] = typer.Option(None, "--data-root", "-d"),
    out_dir: Path = typer.Option(
        Path("docs/caracterizacion/generado/inventarios"),
        "--out",
        "-o",
    ),
) -> None:
    """Extrae texto de archivos Word cuyo nombre contiene 'inventario'."""
    root = _root(data_root)
    docs = extract_inventarios(root)
    if not docs:
        console.print("[yellow]No se encontraron Word de inventario.[/yellow]")
        raise typer.Exit(code=0)
    paths = write_inventario_outputs(docs, out_dir)
    for doc in docs:
        status = "OK" if not doc.error else f"AVISO: {doc.error}"
        console.print(f"- [{doc.fondo_guess}] {doc.path} → {status}")
    console.print(f"Índice: {paths['__index__']}")


@app.command("fasic-reorganize")
def fasic_cmd(
    data_root: Optional[Path] = typer.Option(None, "--data-root", "-d"),
    apply: bool = typer.Option(
        False,
        "--apply",
        help="Aplicar cambios en disco (por defecto solo dry-run)",
    ),
    plan_out: Path = typer.Option(
        Path("docs/caracterizacion/generado/fasic_reorganize_plan.json"),
        "--plan-out",
    ),
    canonical_name: str = typer.Option("Fondo FASIC", "--canonical-name"),
) -> None:
    """Ordena el Fondo FASIC partido en OneDrive_2026-07-13."""
    root = _root(data_root)
    plan = build_plan(root, canonical_name=canonical_name)
    write_plan(plan, plan_out)
    for note in plan.notes:
        console.print(f"• {note}")
    console.print(
        f"Plan: moves={plan.n_moves} dupes={plan.n_dupes} conflicts={plan.n_conflicts}"
    )
    console.print(f"Plan JSON: {plan_out}")
    result = apply_plan(plan, dry_run=not apply)
    mode = "APPLY" if apply else "DRY-RUN"
    console.print(f"[{mode}] {result}")
    if not apply:
        console.print("[cyan]Re-ejecutar con --apply para materializar.[/cyan]")


@app.command("status")
def status_cmd(
    data_root: Optional[Path] = typer.Option(None, "--data-root", "-d"),
) -> None:
    """Verifica si el dataset privado es visible desde este entorno."""
    try:
        root = resolve_data_root(data_root)
    except FileNotFoundError as e:
        console.print("[red]Dataset NO accesible desde este entorno.[/red]")
        console.print(str(e))
        raise typer.Exit(code=2) from e
    console.print(f"[green]Dataset OK:[/green] {root}")
    children = sorted([p.name for p in root.iterdir()])[:40]
    console.print("Contenido (primeros): " + ", ".join(children))


if __name__ == "__main__":
    app()
