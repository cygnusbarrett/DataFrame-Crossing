from pathlib import Path

from consejos_guerra.characterize.causas import extract_causa_codes, primary_causa_code, yy_to_year
from consejos_guerra.characterize.scan import characterize_dataset
from consejos_guerra.fasic.reorganize import apply_plan, build_plan
from consejos_guerra.inventarios.extract import extract_inventarios

FIXTURE = Path(__file__).parent / "fixtures" / "consejos_guerra_mini"


def test_yy_to_year():
    assert yy_to_year(75) == 1975
    assert yy_to_year(1978) == 1978


def test_extract_causa():
    codes = extract_causa_codes("Causa 15-75 sentencia")
    assert codes[0].label == "15-75"
    assert codes[0].year == 1975
    assert primary_causa_code("foo") is None


def test_characterize_fixture():
    result = characterize_dataset(FIXTURE)
    assert result.total_causas_unicas >= 4  # 15-75, 22-76, 08-74, 30-78, 41-79
    assert "1975" in result.causas_por_anio
    assert result.causas_por_anio["1975"] >= 1
    # 15-75 en Alicia y Bernardo
    multi_labels = {m["causa"] for m in result.causas_multi_fondo}
    assert "15-75" in multi_labels
    assert result.fasic_split_detected
    names = {f.name for f in result.fondos}
    assert "Fondo Alicia" in names
    assert "Fondo Bernardo" in names


def test_inventarios_fixture():
    docs = extract_inventarios(FIXTURE)
    assert len(docs) >= 2
    assert any(not d.error for d in docs)


def test_fasic_reorganize_dry_and_apply(tmp_path: Path):
    import shutil

    root = tmp_path / "data"
    shutil.copytree(FIXTURE, root)
    plan = build_plan(root)
    assert plan.n_moves >= 1
    dry = apply_plan(plan, dry_run=True)
    assert dry["moved"] >= 1

    applied = apply_plan(plan, dry_run=False)
    assert applied["moved"] >= 1
    canonical = Path(plan.canonical_root)
    assert canonical.exists()
    assert any(canonical.rglob("pieza.pdf"))


def test_export_and_characterize_manifest(tmp_path: Path):
    from consejos_guerra.characterize.export_manifest import export_for_remote_analysis
    from consejos_guerra.characterize.from_manifest import characterize_from_manifest
    from consejos_guerra.characterize.scan import write_outputs

    out = tmp_path / "manifest"
    meta = export_for_remote_analysis(FIXTURE, out)
    assert meta["n_files"] >= 5
    assert (out / "manifest.csv").is_file()
    assert (out / "inventarios_word").is_dir()

    result = characterize_from_manifest(out / "manifest.csv", out / "inventarios_word")
    assert result.total_causas_unicas >= 4
    assert "1975" in result.causas_por_anio
    assert result.fasic_split_detected
    paths = write_outputs(result, tmp_path / "report")
    md = paths["md"].read_text(encoding="utf-8")
    assert "caracterización sintética" in md
    assert "Causas por año" in md
