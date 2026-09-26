- Responde siempre en español.
- Comienza cada mensaje con el emoji 🤖
- Genera el código para el script o notebook abierto, nunca para la ventana interactiva, salvo que se indique lo contrario.
- La ventana interactiva solo se usa para verificar resultados o mensajes de error.
- No expliques el código salvo que se pida.

## Convenciones de este proyecto
- Entorno gestionado con **UV**. Para añadir una dependencia: `uv add <paquete>`. Nunca `pip install`.
- Para ejecutar cualquier script: `uv run python 04_scripts/<archivo>.py`
- **Bucles tradicionales** (`for` + `append`) en lugar de comprehensions y lambdas.
- Comentarios de sección con el formato `# ── Título ─────────`
- Rutas siempre con `pathlib`, nunca concatenando strings.
- Los datos crudos de `02_datos/01_Originales/` son de **solo lectura**: nunca se sobrescriben.
- **Funciones reutilizables**: antes de escribir una función de análisis, comprobar si ya existe en `04_scripts/utils.py` (46 funciones, generadas desde `00_CATALOGO_FUNCIONES.md` del vault). Se importan: `from utils import frecuencias_cat`. No reescribir equivalentes. Las altas y los cambios los gestiona `A_00_Bibliotecario`.

## ESTADO ACTUAL DEL PROYECTO

**Dataframe actual**: `../02_datos/03_Entrenamiento/train_resultado_calidad.pkl` — tablón unificado tras la fase de Calidad de Datos (trabajo desarrollado en `03_notebooks/02_Calidad_Datos.ipynb`).

**Estructura del dataframe**: 21.209 filas × 12 columnas, sin valores nulos, **con índice temporal `date`** (`Index`, 2013-01-01 → 2015-11-30; 1.064 fechas únicas repetidas en 20 series).

| # | Columna | Dtype | No nulos |
|---|---------|-------|----------|
| 0 | wm_yr_wk | int64 | 21.209 |
| 1 | ventas | int64 | 21.209 |
| 2 | sell_price | float64 | 21.209 |
| 3 | store_id | str | 21.209 |
| 4 | item_id | str | 21.209 |
| 5 | dia_ind | str | 21.209 |
| 6 | year | str | 21.209 |
| 7 | month | str | 21.209 |
| 8 | wday | str | 21.209 |
| 9 | weekday | str | 21.209 |
| 10 | event_name_1 | str | 21.209 |
| 11 | event_type_1 | str | 21.209 |

**Volcado literal de `df.info()`** (ejecutado en la corrección del 25/09/2026):

```
<class 'pandas.DataFrame'>
Index: 21209 entries, 2013-01-01 to 2015-11-30
Data columns (total 12 columns):
 #   Column        Non-Null Count  Dtype
---  ------        --------------  -----
 0   wm_yr_wk      21209 non-null  int64
 1   ventas        21209 non-null  int64
 2   sell_price    21209 non-null  float64
 3   store_id      21209 non-null  str
 4   item_id       21209 non-null  str
 5   dia_ind       21209 non-null  str
 6   year          21209 non-null  str
 7   month         21209 non-null  str
 8   wday          21209 non-null  str
 9   weekday       21209 non-null  str
 10  event_name_1  21209 non-null  str
 11  event_type_1  21209 non-null  str
dtypes: float64(1), int64(2), str(9)
memory usage: 2.1+ MB
```

**Artefactos complementarios** (mismas filas e índice que el tablón, en la misma carpeta): `cat_resultado_calidad.pkl` (9 columnas categóricas) y `num_resultado_calidad.pkl` (3 columnas numéricas).

**Notas de limpieza de esta fase**: eliminadas `state_id`, `dept_id`, `cat_id` (constantes del alcance) y `event_name_2`/`event_type_2` (99,7% nulos); `event_name_1`/`event_type_1` imputadas a «Sin_evento»; 71 registros pre-lanzamiento de `FOODS_3_288` eliminados por truncado (sin imputación de precios). El truncado se ejecuta **sin `reset_index`**, para conservar el índice temporal `date` (corrección del 25/09/2026).

**Informe de la fase**: `../06_resultados/Calidad_Datos/informe_calidad_datos.md`
