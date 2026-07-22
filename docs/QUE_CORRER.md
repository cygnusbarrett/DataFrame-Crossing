# Qué correr — opción “aquí mismo” (Cloud Agent)

## Flujo corto

### En tu Mac (generar el paquete)

```bash
cd /ruta/al/repo
git checkout cursor/grafo-multimodal-consejos-guerra-e698 && git pull
uv sync --extra dev

export CONSEJOS_GUERRA_ROOT="/Users/camilogutierrez/STEM/nuestra-memoria/MuseoDeLaMemoria/2607 - Consejos de Guerra"
uv run cg-characterize export-manifest

git add data/inputs/manifest_consejos_guerra
git commit -m "Datos: manifiesto Consejos de Guerra"
git push
```

### Aquí (este agente)

Decime: **“git pull y corré `scripts/run_here.sh`”**  
o ejecutalo vos en la terminal del agente:

```bash
git pull
chmod +x scripts/run_here.sh
scripts/run_here.sh
```

Salida: `docs/caracterizacion/generado/caracterizacion.md` (informe sintético).

---

## Variante con zip (sin commit de datos)

**Mac:**

```bash
uv run cg-characterize export-manifest
(cd data/inputs && zip -r ../../manifest_consejos_guerra.zip manifest_consejos_guerra)
```

Subí `manifest_consejos_guerra.zip` a `/workspace/` y aquí:

```bash
scripts/run_here.sh --manifest-zip /workspace/manifest_consejos_guerra.zip
```

---

## Dataset completo montado (si existe en esta máquina)

```bash
scripts/run_here.sh --data-root "$CONSEJOS_GUERRA_ROOT" --apply-fasic
```

---

## FASIC en disco real

La fusión de `OneDrive_2026-07-13` conviene en la Mac (`fasic-reorganize --apply`).  
Con el manifiesto, aquí se detecta y documenta el split sin tocar tu disco privado.
