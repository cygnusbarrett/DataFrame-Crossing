# Metodología de caracterización preliminar

## Alcance

Solo nombres de archivos/carpetas + Word `*inventario*` (si existen).
No se OCR-izan PDFs ni se abren imágenes en esta fase.

## Código de causa `xx-yy`

Regex tolerante a separadores `-`, `_`, `/` y a años de 2 o 4 dígitos.
Ventana preferente 1970–1990 (ampliable 1960–2000).

Ejemplo: `15-75` → número 15, año 1975.

## Por fondo

Para cada subcarpeta de `Fondos/`:

1. Conteos de archivos/dirs y extensiones.
2. Extracción de códigos de causa desde rutas relativas.
3. Heurística de **sistema de clasificación** (por causa, caja/legajo,
   onomástica, vocabulario procesal, productor institucional).
4. Localización de inventarios Word.

## Solapes entre fondos

`causas_multi_fondo`: códigos presentes en ≥2 fondos.

Interpretación operativa para el grafo:

```text
(:Fondo)-[:CONTIENE]->(:Pieza)-[:SOBRE]->(:Causa {codigo:"15-75"})
(:Productor)-[:PRODUCE]->(:Fondo)
```

Dos piezas con el mismo `codigo` de causa **no** se colapsan hasta comparar
contenido (hash / inventario / tipología documental).

## FASIC / OneDrive

Patrón observado en descargas rotas: `OneDrive_YYYY-MM-DD/` con dos ramas
(`FASIC` y `FASIC (1)`, etc.). El reorganizador:

1. elige rama principal por score (nombre + volumen),
2. la promueve a `Fondos/Fondo FASIC`,
3. fusiona el resto por path relativo,
4. omite duplicados SHA-256 idénticos,
5. conserva conflictos con sufijo `__from_<rama>`.

Siempre dry-run → revisar `fasic_reorganize_plan.json` → `--apply`.
