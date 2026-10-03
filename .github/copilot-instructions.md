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
- **Plantillas Excel de variables**: `01_Documentos/FaseDesarrollo_PlantillaTransformaciones.xlsx` y `FaseProduccion_PlantillaProcesos.xlsx` son el mapa de qué proceso necesita cada variable madre. Las mantiene `A_00_Excelizador` (al cerrar la transformación y antes de la preproducción). Ante la duda en preproducción, se consulta ese mapa.

## ESTADO ACTUAL DEL PROYECTO

**Dataframe actual**:
- Predictoras: `../02_datos/03_Entrenamiento/x_preseleccionado.pkl`
- Target: `../02_datos/03_Entrenamiento/y_preseleccionado.pkl` (columna `ventas`)

Tablón preseleccionado en `03_notebooks/05_Preseleccion_Variables.ipynb` con **Mutual Information** (75 variables) + los identificadores `date`, `store_id`, `item_id`. Total: 20.909 filas × 78 columnas.

**Qué está pasando en esta fase (contexto):**

- La preselección de `05_Preseleccion_Variables.ipynb` es una **prueba a nivel general**: se coge el tablón completo (los 20 productos juntos) y se comparan 3 métodos (MI, RFE, PI) para ver cómo se comportan.
- **No es un entregable.** La selección de variables que cuenta se hace **producto a producto**, dentro de los bucles `for` de la modelización; como allí se vuelve a seleccionar, este recorte general es solo una prueba.
- El dataset (`x_preseleccionado.pkl` + `y_preseleccionado.pkl`) se guarda **solo para reutilizarlo en `07_Modelizacion.ipynb`**, donde se repite el mismo trabajo a escala real: recorrer los 20 productos con `for` y, dentro de cada uno, hacer su propia selección (MI) + su modelización con **LightGBM** (parámetros, hiperparámetros, etc.).
- `07_Modelizacion.ipynb` es un notebook de modelización: **tampoco guarda un dataset**.

**Variables seleccionadas**: `../01_Documentos/Variables_preseleccionadas.txt`

**Estructura del dataframe** (`x_preseleccionado`):
```
<class 'pandas.DataFrame'>
RangeIndex: 20909 entries, 0 to 20908
Data columns (total 78 columns):
 #   Column                       Non-Null Count  Dtype
---  ------                       --------------  -----
 0   date                         20909 non-null  str
 1   store_id                     20909 non-null  str
 2   item_id                      20909 non-null  str
 3   ventasmmp3                   20909 non-null  float64
 4   ventasmmp4                   20909 non-null  float64
 5   ventasmmp5                   20909 non-null  float64
 6   ventasmmp6                   20909 non-null  float64
 7   ventasmmp8                   20909 non-null  float64
 8   ventasmmp2                   20909 non-null  float64
 9   ventasmmp7                   20909 non-null  float64
 10  ventasmmp9                   20909 non-null  float64
 11  ventasmmp10                  20909 non-null  float64
 12  ventasmmp11                  20909 non-null  float64
 13  ventasmmp12                  20909 non-null  float64
 14  ventasmmp13                  20909 non-null  float64
 15  ventasmmp15                  20909 non-null  float64
 16  ventasmmp14                  20909 non-null  float64
 17  ventasmax2                   20909 non-null  float64
 18  ventasmax8                   20909 non-null  float64
 19  ventasmax7                   20909 non-null  float64
 20  ventasmax6                   20909 non-null  float64
 21  ventas_lag1                  20909 non-null  float64
 22  ventasmax3                   20909 non-null  float64
 23  ventasmax9                   20909 non-null  float64
 24  ventasmax10                  20909 non-null  float64
 25  ventasmax4                   20909 non-null  float64
 26  ventasmax5                   20909 non-null  float64
 27  ventasmax13                  20909 non-null  float64
 28  ventasmax11                  20909 non-null  float64
 29  ventasmax14                  20909 non-null  float64
 30  ventasmin2                   20909 non-null  float64
 31  ventasmax12                  20909 non-null  float64
 32  ventasmax15                  20909 non-null  float64
 33  ventasmin3                   20909 non-null  float64
 34  ventasmin4                   20909 non-null  float64
 35  ventasmin5                   20909 non-null  float64
 36  ventasmin6                   20909 non-null  float64
 37  ventasmin7                   20909 non-null  float64
 38  ventas_lag2                  20909 non-null  float64
 39  ventasmin8                   20909 non-null  float64
 40  ventas_lag7                  20909 non-null  float64
 41  ventasmin9                   20909 non-null  float64
 42  ventas_lag6                  20909 non-null  float64
 43  ventasmin10                  20909 non-null  float64
 44  ventas_lag3                  20909 non-null  float64
 45  ventasmin11                  20909 non-null  float64
 46  ventas_lag8                  20909 non-null  float64
 47  ventas_lag4                  20909 non-null  float64
 48  ventasmin12                  20909 non-null  float64
 49  ventasmin13                  20909 non-null  float64
 50  ventas_lag5                  20909 non-null  float64
 51  ventasmin14                  20909 non-null  float64
 52  ventasmin15                  20909 non-null  float64
 53  ventas_lag14                 20909 non-null  float64
 54  ventas_lag13                 20909 non-null  float64
 55  ventas_lag9                  20909 non-null  float64
 56  ventas_lag15                 20909 non-null  float64
 57  ventas_lag12                 20909 non-null  float64
 58  ventas_lag10                 20909 non-null  float64
 59  ventas_lag11                 20909 non-null  float64
 60  sell_price_lag1              20909 non-null  float64
 61  sell_price_lag2              20909 non-null  float64
 62  sell_price_lag7              20909 non-null  float64
 63  sell_price_lag3              20909 non-null  float64
 64  sell_price_lag4              20909 non-null  float64
 65  sell_price_lag6              20909 non-null  float64
 66  sell_price_lag5              20909 non-null  float64
 67  rotura_stock_3_lag1          20909 non-null  float64
 68  rotura_stock_7_lag1          20909 non-null  float64
 69  rotura_stock_15_lag1         20909 non-null  float64
 70  event_name_1_Halloween       20909 non-null  float64
 71  event_type_1_Sin_evento      20909 non-null  float64
 72  event_name_1_OrthodoxEaster  20909 non-null  float64
 73  weekday_Monday               20909 non-null  float64
 74  month_2                      20909 non-null  float64
 75  event_name_1_SuperBowl       20909 non-null  float64
 76  event_name_1_EidAlAdha       20909 non-null  float64
 77  event_name_1_Christmas       20909 non-null  float64
dtypes: float64(75), str(3)
memory usage: 12.4 MB
```

**Notas de la fase**: la Transformación completó el feature engineering de forecasting: flags de rotura de stock (proxy al no haber datos de inventario) + lags (ventas 1→15, sell_price 1→7, rotura 1 día) + ventanas móviles (min/max/media ponderada 2→15, con `shift(1)` para evitar fuga) + One-Hot Encoding (`drop='first'`, `handle_unknown='ignore'`) de calendario y eventos. Se eliminaron `sell_price`, `rotura_stock_3/7/15` (crudas; quedan como lag1), `dia_ind` y `wm_yr_wk`. **Sin escalado** (modelo LightGBM/XGBoost). `dropna()` de calentamiento: 21.209 → 20.909 filas. La columna `date` sigue en **str** (solo trazabilidad; convertir a `datetime` si se necesita para cortes temporales).

**Informe de la fase (Transformación)**: `../06_resultados/Transformacion/informe_transformacion.md`

**Notas de la fase (Preselección)**: en `03_notebooks/05_Preseleccion_Variables.ipynb` se compararon 3 métodos sobre el tablón general para decidir qué variables predictivas conservar: **Mutual Information** (75 variables, método elegido), **RFE** (63, la mitad por defecto; se descartó **RFECV** por lento y porque la validación cruzada al azar no es válida en forecasting) y **Permutation Importance** (74). Se guardó el dataset (`x_preseleccionado.pkl` + `y_preseleccionado.pkl`) reincorporando los identificadores. La selección definitiva se hará **producto a producto** (20 modelos tienda × producto) dentro de los bucles `for` de la modelización. Como allí se vuelve a seleccionar, este recorte general es solo una prueba y no un entregable.

**Informe de la fase (Preselección)**: `../06_resultados/Preseleccion/Informe_Preseleccion_Variables.md`
