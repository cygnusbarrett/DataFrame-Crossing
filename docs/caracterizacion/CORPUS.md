# Corpus «Consejos de Guerra» — descripción sintética

_Basado en barrido de nombres (2026-07-22). No se abrieron PDFs/imágenes. Los inventarios Word no se extrajeron en esa corrida (faltaba `python-docx`)._

## Qué es

Colección privada en crecimiento de **expedientes y piezas** ligados a **consejos de guerra** en Chile, reunidos por distintos productores (investigadores, familiares, instituciones de DD.HH.). No es un único archivo homogéneo: son **fondos** que a veces hablan de la **misma causa** con material distinto o solapado.

**Clave de lectura:** en los nombres, `15-75` ≈ causa nº **15** de **1975**.

| | |
| --- | ---: |
| Archivos | 3 194 |
| Carpetas | 870 |
| Causas únicas detectadas en nombres (`xx-yy`) | **372** |
| Fondos documentales relevantes | **7** (+ artefactos de carpeta, ver abajo) |

---

## Tiempo: cuándo se concentran las causas

Casi todo el corpus nominativo cae en el arranque de la dictadura:

| Periodo | Causas | Lectura |
| --- | ---: | --- |
| **1973–1975** | 294 (79 %) | Núcleo duro del corpus |
| 1973 | 108 | |
| **1974 (pico)** | **109** | Año con más causas distintas en nombres |
| 1975 | 77 | |
| 1976–1990 | ~70 | Cola dispersa (pocas causas/año) |
| 1991–1998 | 6 | Eco tardío / posibles causas o ruidos de naming |

---

## Los fondos (cómo está armado cada uno)

Ignorar en el conteo de “fondos”: `_raiz_`, el ítem `Inventario.docx` (archivo suelto mal clasificado como fondo).

### 1. OneDrive / **Fondo FASIC** (el volumen dominante)

- **~2 732 archivos** (~86 % del corpus), **~196 causas** en nombres.
- Formatos: sobre todo `.txt` (2 110; probable OCR/texto derivado), luego `.jpg` / `.tif`; casi no hay PDF.
- **Descarga partida:** ramas `Fondo FASIC` y `__Fondo FASIC` (+ log `___All_Errors.txt`). Misma intención de fondo; hay que unificar después.
- Clasificación aparente: serie institucional FASIC indexada por causa / tipología procesal, digitalizada como imagen+texto.

### 2. **Fondo 0084 PDDHH Consejos de Guerra_2021**

- 149 PDF · **142 causas** → casi **1 PDF ≈ 1 causa** (inventario muy denso).
- Primer nivel tipo series/cajas: `C`, `D`, `E`, `CD-A FACH`, `CD-B FACH`.
- Lectura: transferencia/ordenación tipo archivo de Programa DD.HH., no “carpeta de investigador suelta”.

### 3. **Fondo Cristian Cruz**

- 57 archivos · **52 causas** · hay inventario Word.
- Raíz `CONSEJOS DE GUERRA`; PDF dominante.
- Lectura: recolección personal/investigador, una pieza (o pocas) por causa.

### 4. **FONDO CAUCOTO — revisión CG**

- 177 archivos · solo **4 causas** visibles en nombres (el naming no es el eje).
- Organizado por **revisiones de personas** (Lanfranco, Contreras, Cámara, Torres, Lagos, Taberna…).
- Lectura: dossier de **trabajo de revisión** (abogado/investigador), no catálogo causa-a-causa.

### 5. **FONDO SEGUEL PABLO — Causa 1-73**

- 32 archivos · foco explícito en **`1-73`** (+ `ADICION 2025`).
- Lectura: fondo **monográfico** sobre una causa; útil como ancla profunda frente a fondos “anchos”.

### 6. **FONDO PIDEE — Puerto Montt 16-10-1973**

- 44 archivos imagen (`.tif`/`.jpg`) + inventario `.doc`.
- Un hecho/fecha en el nombre del fondo; **0 códigos `xx-yy`** en paths.
- Lectura: serie visual de un consejo concreto (Puerto Montt), otra convención de naming.

### 7. **Fondo Paris Horvitz Familia**

- Solo **2 archivos** (1 PDF + inventario).
- Lectura: aporte familiar mínimo; todavía no es un fondo poblado.

---

## ¿Material repetido entre fondos?

**21 códigos** aparecen en ≥2 fondos (casi siempre **FASIC/OneDrive** + PDDHH o Cruz o Caucoto/Seguel).

Ejemplos: `1-73` (Seguel + Cruz + FASIC), `3-73` (Caucoto + Cruz + FASIC), `4-75` (Seguel + PDDHH + FASIC).

**Interpretación operativa**

- Mismo código ≠ mismo archivo.
- Lo esperable: **FASIC** como base ancha; **PDDHH/Cruz** como otra selección; **Seguel/Caucoto** como profundidad o revisión.
- Para el grafo: nodo `Causa` compartido; `Pieza` ligada al `Fondo`. Deduplicar solo con hash/inventario, no por código.

---

## Mapa mental (una frase)

> Un **núcleo 1973–75** de ~370 causas nominadas, sostenido sobre todo por **FASIC** (masivo, imagen+texto, hoy partido en dos carpetas), con **PDDHH** y **Cruz** como catálogos densos en PDF, más **fondos puntuales** (Seguel 1-73, PIDEE Puerto Montt, revisiones Caucoto, aporte Horvitz).

---

## Pendientes que mejoran la descripción (sin “construir repo”)

1. `pip install --user python-docx` y re-correr con `--inventarios` → leer los Word *Inventario* de cada fondo.
2. Unificar `OneDrive_2026-07-13` (`Fondo FASIC` + `__Fondo FASIC`).
3. Tratar `Inventario.docx` de la raíz como inventario general, no como fondo.
