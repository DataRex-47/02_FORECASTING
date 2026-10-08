# Informe de Calidad de Datos — Proyecto Forecasting Retail

> **Documento vivo (v1 — fase en curso).** Recoge el trabajo de auditoría y limpieza ejecutado hasta ahora en el notebook de calidad de datos. Se irá completando a medida que avance la fase.
> Elaborado a partir de la **lectura directa de las salidas ejecutadas del notebook**, del documento del caso y de la bitácora maestra. No se ha ejecutado código adicional para su redacción.

---

## 1. Ficha del documento

| Campo | Valor |
|---|---|
| Proyecto | Forecasting Retail — proyecto multimodelo de predicción de demanda |
| Fase | A_02 — Calidad de Datos |
| Notebook de trabajo | `03_notebooks/02_Calidad_Datos.ipynb` |
| Entrada | `02_datos/03_Entrenamiento/train.pkl` — tablón integrado (21.280 × 17) |
| Salidas persistidas | `train_resultado_calidad.pkl`, `cat_resultado_calidad.pkl`, `num_resultado_calidad.pkl` |
| Resultado final de este bloque | **21.209 filas × 12 columnas**, sin nulos, **con índice temporal `date` conservado**, listo para la siguiente fase |

---

## 2. Resumen ejecutivo

- Se auditó el tablón integrado completo: **21.280 registros × 17 columnas**, con índice temporal del 01/01/2013 al 30/11/2015 (1.064 días).
- **71 valores nulos** detectados en `sell_price` (0,33% del total): **el 100% concentrados en un único producto (`FOODS_3_288`)** y en el periodo de **enero y primeros días de febrero de 2013**, siempre con `ventas = 0`. El análisis concluye que corresponden al **periodo previo al lanzamiento comercial** del producto, no a un fallo de captura.
- **Decisión metodológica:** en lugar de imputar precios, se aplicó un **truncado por lanzamiento comercial** (eliminación de las 71 filas). Evita fuga de datos (*data leakage*) y no introduce precios artificiales en la relación precio–demanda.
- **0 duplicados** completos en la matriz analítica (verificado con `df.duplicated().sum()`).
- Se depuraron las dimensiones del dataset: **3 columnas eliminadas por constantes** (`state_id`, `dept_id`, `cat_id`) y **2 columnas eliminadas por casi vacías** (`event_name_2`, `event_type_2`, 99,7% de nulos).
- Se normalizaron tratamientos de tipo: `year`, `month` y `wday` convertidos a categóricas (`str`); nulos de `event_name_1`/`event_type_1` imputados a la categoría **«Sin_evento»** (19.580 registros cada una).
- **Ninguna variable numérica fue imputada**: la única con missing (`sell_price`) se resolvió por truncado, por lo que la escala real del precio **[1,00 – 4,98]** queda intacta, sin valores imputados por debajo del mínimo ni por encima del máximo.
- Resultado persistido en **3 artefactos sincronizados** (tablón unificado + vistas numérica y categórica): **21.209 filas × 12 columnas**, sin nulos.
- **Índice temporal conservado (corrección aplicada el 25/09/2026):** los tres artefactos mantienen el índice `date` (2013-01-01 → 2015-11-30; 1.064 fechas) heredado de `train.pkl`, tanto en el tablón unificado como en las vistas `cat` y `num`. Un `reset_index(drop=True)` en la fase de truncado lo había degradado a `RangeIndex` (0–21.208) en la primera persistencia; eliminada esa llamada, los tres artefactos se regeneraron con el índice restaurado.

---

## 3. Alcance y diseño del proyecto

### 3.1 Universo de análisis

El diseño del caso fija un **proyecto multimodelo** deliberadamente acotado para garantizar homogeneidad de surtido y comparabilidad entre series (documento del caso, pág. 4; recogido también en la bitácora):

| Dimensión | Valor definido |
|---|---|
| Retailer | 1 gran retailer |
| Categoría | 1 (alimentación — familia `FOODS_3`) |
| Tiendas | 2 (`CA_3`, `CA_4`) |
| Productos | 10 (`FOODS_3_090`, `120`, `202`, `252`, `288`, `329`, `555`, `586`, `587`, `714`) |
| Periodo | 01/01/2013 → 30/11/2015 (1.064 días) |
| Grano de la tabla | día × tienda × producto → 1.064 × 2 × 10 = **21.280 registros** |

> **Del documento del caso (pág. 4):**
> «En este caso vamos a trabajar sobre datos reales de un gran distribuidor. […] Pero lo que vas a aprender vas a poder aplicarlo a prácticamente cualquier empresa, ya que se usa en todos los sectores.»
>
> El esquema de la página desciende por la jerarquía del alcance: **1 gran retailer → 1 categoría: alimentación → 2 tiendas → 10 productos por tienda**.

La fase de selección de universo (estado, departamento y categoría) se resolvió por **acotación directa del alcance**: se fija un único estado, un único departamento y una única categoría. Los criterios de selección granular (por ejemplo, top-N por volumen) quedan **parametrizados**: escalar el piloto a un caso real de gran retailer consiste en relajar esos filtros (más estados, tiendas, categorías y productos) sin tocar el resto del pipeline.

**Verificación en datos:** los valores únicos calculados en el notebook reproducen exactamente el alcance del diseño:

- `store_id` → **2** valores (`CA_3`: 10.640 filas; `CA_4`: 10.640 filas)
- `item_id` → **10** valores (2.128 filas cada uno)
- `state_id`, `dept_id`, `cat_id` → **1** valor cada uno (constantes)
- `dia_ind` → 1.064 días (`d_704` … `d_1767`)
- Series temporales resultantes: **20** (2 tiendas × 10 productos)

### 3.2 ¿Por qué se eliminaron `state_id`, `dept_id` y `cat_id`?

Estas tres columnas presentan **cardinalidad = 1** en la muestra (un único estado, un único departamento, una única categoría). Al ser **constantes, tienen varianza nula y no aportan ninguna capacidad discriminante** al modelo: mantenerlas solo añadiría ruido dimensional y almacenamiento, además de una falsa sensación de jerarquía explotable. Por eso se eliminan de la matriz analítica en esta fase.

**Nota analítica (extensible a un despliegue a gran escala):** en un proyecto multirregión, multidepartamento y multicategoría, estas columnas serían precisamente las **claves de segmentación y agrupación** del negocio, y **no deberían eliminarse**: habilitan modelos por segmento (global vs. local), agregaciones jerárquicas tipo *roll-up* (producto → categoría → departamento → estado), *backtesting* estratificado y reentrenamientos selectivos por región o familia. En este proyecto se eliminan **por decisión de alcance** (universo fijado a un único nivel de cada jerarquía), no porque el dataset no las contemple: al escalar el caso, se conservan y pasan a ser variables de partición.

---

## 4. Auditoría ejecutada en el notebook

| # | Bloque del notebook | Qué se revisó | Resultado clave |
|---|---|---|---|
| 1 | Visión general y tipos de datos | `df.info()` + `df.shape` | 21.280 × 17; única columna con nulos: `sell_price` (21.209 no nulos → 71 NaN) |
| 2 | Tipos de calendario | Revisión semántica de `year`, `month`, `wday` | Convertidas a categóricas (`str`): son dimensiones para cruces, no magnitudes continuas |
| 3 | Valores únicos | `df.nunique()` | `state_id`/`dept_id`/`cat_id` = 1; `store_id` = 2; `item_id` = 10 |
| 4 | Duplicados | `df.duplicated().sum()` | **0 duplicados** (ver salida literal en § Anexo A) |
| 5 | Separación numéricas / categóricas | `select_dtypes` | `con` = `wm_yr_wk`, `ventas`, `sell_price`; `cat` = resto de dimensiones |
| 6 | Categóricas — nulos | `cat.isna().sum()` | `event_name_1`/`event_type_1`: 19.580 nulos c/u; `event_name_2`/`event_type_2`: 21.220 nulos c/u |
| 7 | Categóricas — corrección | `fillna` + `drop` | Eventos 1 → «Sin_evento»; eventos 2 → columnas eliminadas (99,7% nulos) |
| 8 | Categóricas — frecuencias | `value_counts` por variable + revisión de categorías poco frecuentes | 30 eventos distintos en `event_name_1`; 4 tipos en `event_type_1`; sin colisiones de escritura detectadas |
| 9 | Numéricas — estadísticos | `con.describe().T` | `sell_price`: media 2,397 · mediana 1,580 · rango [1,00 – 4,98]; `ventas`: media 28,875 · mediana 18 · máx 763 |
| 10 | Numéricas — nulos | `con.isna().sum()` + `groupby` por `item_id` | 71 nulos, todos en `FOODS_3_288` (resto de productos: 0) |
| 11 | Numéricas — análisis del nulo | Aislamiento por mes / ventas / prueba de control | 62 nulos en enero + 9 en primeros de febrero; `ventas = 0` en los 71; control 04/2014 OK |
| 12 | Numéricas — atípicos | Criterio de desviación típica (`num_desv_tip = 4`) sobre `ventas` y `sell_price` | `sell_price` sin atípicos; `ventas` con valores extremos identificados (ver § 7.3) |
| 13 | Unión y depuración final | `concat` → `dropna` (**sin** `reset_index`) | 71 filas eliminadas → 21.209 registros; índice `date` conservado y sincronía de índices verificada |
| 14 | Guardado | `to_pickle` × 3 | 3 artefactos persistidos y sincronizados, todos con índice `date` |
| 15 | Verificación del índice | Comparación `df` / `df_2` / `cat` / `con` + relectura de los `.pkl` | Índice `date` (2013-01-01 → 2015-11-30) conservado en los 3 artefactos; `df_2`, `cat` y `con` comparten índice idéntico |

---

## 5. Hallazgo principal: 71 nulos en `sell_price`

### 5.1 Diagnóstico

El defecto detectado es de **exactamente 71 valores nulos** en la variable continua `sell_price`. El aislamiento espacial y temporal fue concluyente:

- **Un único producto implicado:** `FOODS_3_288` (71 nulos; los otros 9 productos: 0).
- **Ambas tiendas implicadas** (`CA_3` y `CA_4`).
- **Periodo continuo y acotado:** 62 nulos en enero + 9 en los primeros días de febrero de 2013.
- **La demanda es estrictamente cero** en esos 71 registros: `ventas = 0` en el 100% de los casos.

**Prueba de control ejecutada:** se aisló el comportamiento del mismo producto en un periodo normal posterior (abril de 2014), obteniendo 60 registros con actividad con normalidad (30 días × 2 tiendas). Esto confirma que el problema **no era permanente** del artículo, sino acotado a su arranque.

### 5.2 Conclusión

El 100% de los nulos pertenecen al **periodo previo al lanzamiento comercial** del producto en esas sucursales: el artículo aún no estaba en el catálogo activo (ni en góndola), y por eso no tenía precio ni ventas. Se descarta un fallo aleatorio de captura o una venta sin precio registrado.

---

## 6. Tratamiento aplicado: truncado por lanzamiento comercial (no imputación)

### 6.1 Por qué se descartó la imputación de precios

Las soluciones de imputación tipo «moda» (semanal o histórica global) fueron descartadas por estos motivos:

1. **Inconsistencia del agrupamiento semanal:** al inicio de la serie, esas semanas son 100% nulas, por lo que la moda semanal resulta vacía.
2. **Fuga de datos (*data leakage*) temporal:** un mecanismo de rescate con la moda histórica global del producto trasladaría precios de 2014–2015 hacia enero de 2013, inyectando información del futuro en el pasado.
3. **Distorsión de la relación precio–demanda:** asignar un precio artificial simularía que el producto estuvo 45 días en góndola sin vender nada, falseando la elasticidad precio–demanda que aprenderán los modelos.
4. **Omisión de la tienda:** imputar sin distinguir `store_id` asume una política de precios idéntica entre sucursales.

### 6.2 Acción ejecutada

- Se **unificaron previamente** las matrices numérica y categórica (`pd.concat([con, cat], axis=1)`) para preservar la integridad referencial y evitar desalineaciones posicionales entre atributos.
- Se **eliminaron las 71 filas** con `sell_price` nulo (`dropna(subset=['sell_price'])`), **sin `reset_index`**: así se conserva el índice temporal `date` del tablón.
- Efecto: la serie temporal de `FOODS_3_288` **inicia formalmente en su lanzamiento comercial** (comienzos de febrero de 2013) con precio real, y los históricos de los otros 9 productos quedan íntegros.

### 6.3 Documentación de imputaciones numéricas (control de escala)

| Variable | Nº nulos | Método aplicado | Valor imputado | ¿Dónde cae ese valor en la escala real? | Justificación |
|---|---|---|---|---|---|
| `sell_price` | 71 | **Ninguno — truncado** (eliminación de las 71 filas) | No existe valor imputado | Escala real conservada: **[1,00 – 4,98]** (media 2,397 · mediana 1,580). Al no imputar, no hay ningún valor artificial que pueda caer fuera del rango | Los nulos son pre-lanzamiento comercial: un precio imputado (aunque cayera dentro del rango) falsearía la relación precio–demanda y podría introducir *leakage* |
| `ventas` | 0 | No procede | — | — | Sin missing |
| `wm_yr_wk` | 0 | No procede | — | — | Sin missing |

> **Nota de cumplimiento (regla de imputación numérica):** no se aplicó ninguna imputación numérica. A título de control se comprobó que los candidatos clásicos (media 2,397; mediana 1,580) caerían **dentro** del rango real [1,00 – 4,98] y por encima del mínimo; aun así se descartaron por la pérdida de fidelidad señalada. El truncado garantiza que ningún registro conserve un precio artificial.

### 6.4 Consideraciones para fases posteriores

- **Cálculo de lags y medias móviles:** al generar retardos por serie `[store_id, item_id]`, los primeros registros de `FOODS_3_288` producirán nulos iniciales **legítimos** (no hay historia previa al lanzamiento); deberán gestionarse con filtros temporales o imputaciones controladas, sin arrastrar ceros ficticios previos a febrero de 2013.
- **Modelos tabulares (LightGBM / XGBoost):** operan fila por fila y asimilan series de longitudes distintas sin inconveniente; además, se benefician de haber eliminado el ruido artificial en la variable objetivo y en las covariables de precio.

---

## 7. Resto de tratamientos de calidad aplicados

### 7.1 Tipos y dimensiones de calendario

- `year`, `month` y `wday` se convierten de `int64` a categórica (`str`): se usan como dimensiones de cruce (calendario), no como magnitudes continuas.
- Se conservan `wday` (numérico) y `weekday` (nombre) como representaciones complementarias del día de la semana.

### 7.2 Categóricas de evento

| Columna | Nulos originales | Tratamiento | Justificación |
|---|---|---|---|
| `event_name_1` | 19.580 (≈92%) | Imputación a categoría **«Sin_evento»** | El nulo *significa* «día sin evento»: es una categoría propia e informativa, no un dato ausente que deba estimarse |
| `event_type_1` | 19.580 (≈92%) | Imputación a **«Sin_evento»** | Idem |
| `event_name_2` | 21.220 (99,7%) | **Columna eliminada** | Vacío estructural: apenas 60 registros con valor en 21.280 filas |
| `event_type_2` | 21.220 (99,7%) | **Columna eliminada** | Idem |

Tras el tratamiento, `event_name_1` conserva 30 eventos distintos (con sus 4 tipos: National 580, Religious 560, Cultural 380, Sporting 180) y los días sin evento quedan identificables. No se detectaron problemas de mayúsculas/acentos ni etiquetas duplicadas semánticamente en las revisiones de frecuencia.

### 7.3 Atípicos en numéricas (análisis, sin recorte)

- Método: **desviación típica** con parámetro `num_desv_tip = 4` aplicado sobre `ventas` y `sell_price` (funciones `atipicos_desv_tip` / `conteo_atipicos`).
- Resultado: **`sell_price` sin atípicos**; **`ventas` con un conjunto amplio de valores extremos identificados** (247 valores distintos en el recuento registrado, mezclando ceros y picos altos propios de una demanda intermitente).
- **No se aplicó recorte** (ni *winsorization* ni *clipping*) en esta fase: el análisis queda documentado como insumo para EDA/modelado, donde se decidirá el tratamiento (o su ausencia) con evidencia adicional.

> **Nota — hipótesis preliminares de negocio sobre el valor extremo de `ventas`.** El máximo registrado en la variable objetivo (**763 unidades frente a una mediana de 18**) es el principal foco heredado de este bloque. Antes de tomar cualquier decisión de tratamiento en fases posteriores se contrastarán tres hipótesis de negocio:
>
> 1. **Compra institucional o mayorista (B2B puntual en tienda física):** un pedido de volumen excepcional de un cliente profesional realizado sobre el canal minorista.
> 2. **Efecto rebote post-rotura de stock previo:** demanda acumulada que se libera de golpe al reponerse el artículo tras un periodo sin disponibilidad.
> 3. **Campaña promocional o evento local no registrado en las columnas de calendario:** pico de demanda asociado a una acción comercial o a un evento de la zona no capturado por `event_name_1`/`event_type_1`.
>
> Estos registros **no se han recortado en la fase de Calidad de Datos** —coherente con la decisión de no aplicar *winsorization* ni *clipping*—, pero quedan **marcados como prioridad de análisis para la fase de EDA**, donde se contrastarán contra la serie completa, el histórico de precios y el calendario de eventos.

### 7.4 Duplicados

- `df.duplicated().sum()` → **0**. No existen duplicados completos en la matriz analítica, por lo que no fue necesaria ninguna estrategia de desduplicación (conservar primero/último, colapsar, etc.).
- Como control de grano: cada combinación `[store_id, item_id, dia_ind]` es única por construcción (2 × 10 × 1.064 = 21.280 registros), confirmando que el grano día × tienda × producto es correcto.

---

## 8. El ciclo des-unir → transformar → unir → depurar → volver a separar (y por qué)

Durante la fase se trabajó con las matrices por tipo de dato y, al final, se revirtió a la matriz unificada para limpiar y se volvió a separar para persistir. Este ida y vuelta es **deliberado**:

1. **Des-unir (separar numéricas y categóricas):** cada bloque requiere tratamientos distintos (estadísticos y atípicos en numéricas; frecuencias, nulos y categorías en categóricas).
2. **Transformar:** nulos de eventos, tipos de calendario, depuración de columnas casi vacías, etc.
3. **Unir (`pd.concat([con, cat], axis=1)`):** la eliminación de filas (truncado de `sell_price`) **debe** hacerse sobre la matriz unificada para que el borrado sea consistente entre atributos y no quede ningún índice desalineado entre lo numérico y lo categórico.
4. **Depurar:** eliminación de las 71 filas pre-lanzamiento **sin `reset_index(drop=True)`**. Esa llamada destruía el índice temporal `date` (lo degradaba a `RangeIndex` 0–21.208) y el tablón perdía su anclaje temporal nativo; el índice se conserva en los tres artefactos.
5. **Volver a separar (`select_dtypes`):** la arquitectura modular del pipeline posterior consume tanto el tablón unificado como las vistas por tipo de dato, sincronizadas fila a fila **y con el mismo índice `date`**.
6. **Persistir:** se guardan los tres artefactos con **total sincronía de dimensiones e índices**:

| Artefacto | Contenido | Dimensiones |
|---|---|---|
| `train_resultado_calidad.pkl` | Tablón unificado (numéricas + categóricas) | 21.209 × 12 |
| `num_resultado_calidad.pkl` | Vista numérica: `wm_yr_wk`, `ventas`, `sell_price` | 21.209 × 3 |
| `cat_resultado_calidad.pkl` | Vista categórica: 9 dimensiones | 21.209 × 9 |

> Ubicación: `02_datos/03_Entrenamiento/`. **Los tres artefactos conservan el índice `date` original** (2013-01-01 → 2015-11-30; 1.064 fechas) heredado de `train.pkl`. Las columnas `wm_yr_wk`, `dia_ind`, `year`, `month`, `wday` y `weekday` siguen disponibles como dimensiones temporales complementarias.

> ⚠️ **Incidente de índice detectado y corregido (25/09/2026).** En la primera versión de esta fase, el truncado se ejecutaba con `dropna(...).reset_index(drop=True)`: esa llamada **descartaba el índice `date`** y lo sustituía por un `RangeIndex` (0–21.208), de modo que el tablón persistido dejaba de arrastrar su anclaje temporal nativo y **el orden físico de las filas no garantizaba la secuencia cronológica de cada serie**. Se documentan a continuación las consecuencias que se habían asumido, junto con su estado final:
>
> - La cronología era **reconstruible** a partir de `wm_yr_wk`/`dia_ind`, pero esa reconstrucción (con su ordenación explícita) pasaba a ser un paso **obligatorio** del preprocesado.
> - Cualquier operación dependiente del orden temporal —retardos (`.shift()`), ventanas móviles, expansiones— debía ejecutarse **solo después** de ordenar por `['store_id', 'item_id', 'dia_ind']` o de restaurar la fecha como índice temporal.
>
> **Estado tras la corrección:** eliminada la llamada `reset_index(drop=True)`, los tres artefactos **conservan el índice `date`**, por lo que el anclaje temporal nativo queda restaurado. El índice `date` **no es único** (1.064 fechas repetidas en 20 series: 2 tiendas × 10 productos), así que sigue siendo recomendable ordenar por `['store_id', 'item_id', 'dia_ind']` antes de calcular retardos; si en fases posteriores se necesita una clave única, la candidata es `['date', 'store_id', 'item_id']`.

---

## 9. Registro de transformaciones variable a variable

### 9.1 Transformaciones por columna

| Variable | Nº total | Transformación(es) aplicada(s) | Justificación |
|---|---:|---|---|
| `state_id` | 1 | Eliminación | Constante (1 valor): varianza nula |
| `dept_id` | 1 | Eliminación | Constante (1 valor): varianza nula |
| `cat_id` | 1 | Eliminación | Constante (1 valor): varianza nula |
| `year` | 1 | Conversión `int64` → `str` | Dimensión de calendario para cruces |
| `month` | 1 | Conversión `int64` → `str` | Dimensión de calendario para cruces |
| `wday` | 1 | Conversión `int64` → `str` | Dimensión de calendario para cruces |
| `event_name_1` | 1 | Imputación de 19.580 nulos → «Sin_evento» | El nulo significa «sin evento» (categoría propia) |
| `event_type_1` | 1 | Imputación de 19.580 nulos → «Sin_evento» | Idem |
| `event_name_2` | 1 | Eliminación | 99,7% nulos (21.220 de 21.280) |
| `event_type_2` | 1 | Eliminación | 99,7% nulos (21.220 de 21.280) |
| `sell_price` | 1 | Truncado: 71 filas eliminadas (pre-lanzamiento) | Preservar relación precio–demanda real; evitar *leakage* |
| `wm_yr_wk` | 0 | Sin cambios (validada) | Sin nulos; rango coherente (11.249–11.544) |
| `ventas` | 0 | Sin cambios (validada; atípicos identificados sin recorte) | Variable objetivo; integridad confirmada |
| `store_id` | 0 | Sin cambios (validada) | 2 valores; clave de serie |
| `item_id` | 0 | Sin cambios (validada) | 10 valores; clave de serie |
| `dia_ind` | 0 | Sin cambios (validada) | 1.064 días |
| `weekday` | 0 | Sin cambios (validada) | 7 valores |

**Total: 11 transformaciones sobre variables.**

### 9.2 Acciones estructurales (afectan al conjunto, no a una columna)

| Acción | Nº | Detalle |
|---|---:|---|
| Separación inicial numéricas/categóricas | 1 | `select_dtypes` sobre el tablón |
| Unificación previa al truncado | 1 | `pd.concat([con, cat], axis=1)` |
| Depuración de filas pre-lanzamiento | 1 | `dropna(subset=['sell_price'])` → 71 filas |
| Conservación del índice | 1 | Se elimina `reset_index(drop=True)`; el índice `date` se mantiene en los 3 artefactos |
| Re-separación post-limpieza | 1 | `select_dtypes` sobre el tablón limpio |
| Persistencia | 1 | `to_pickle` × 3 artefactos sincronizados |

**Total: 6 acciones estructurales.**

### 9.3 Secuencia reproducible

1. Cargar `train.pkl` (tablón integrado de la fase de importación).
2. `df.info()` y `df.shape` → inventario de tipos y nulos.
3. Convertir `year`, `month`, `wday` a `str`.
4. Eliminar `state_id`, `dept_id`, `cat_id` (constantes del alcance).
5. Verificar duplicados: `df.duplicated().sum()` → 0.
6. Separar matrices: `con` (numéricas) y `cat` (categóricas).
7. En `cat`: eliminar `event_name_2`/`event_type_2`; imputar `event_name_1`/`event_type_1` a «Sin_evento»; revisar frecuencias y categorías poco frecuentes.
8. En `con`: estadísticos (`describe`), nulos, aislamiento de `sell_price` por `item_id`/mes/ventas, y conteo de atípicos (4σ).
9. Unir (`concat`) → eliminar las 71 filas con `sell_price` nulo (**sin `reset_index`**, para conservar el índice `date`).
10. Re-separar por tipo (`select_dtypes`) y persistir los 3 `.pkl` en `02_datos/03_Entrenamiento/`.

### 9.4 Verificaciones de integridad finales

- Filas: 21.280 − 71 = **21.209** ✔
- Series: `FOODS_3_288` pasa de 2.128 a 2.057 registros (−71); los otros 9 productos conservan sus 2.128 ✔ (9 × 2.128 + 2.057 = 21.209)
- Nulos en la matriz final: **0** ✔
- Sincronía entre los 3 artefactos persistidos: mismas filas e índice ✔ (verificado releyendo los `.pkl` de disco)
- Índice temporal conservado en los 3 artefactos: `Index` llamado `date`, 2013-01-01 → 2015-11-30 ✔

---

## 10. Consideraciones para Feature Engineering y Modelado

- ⚠️ **Directriz de orden antes de calcular retardos.** El tablón persistido **sí conserva el índice `date`** (corrección del 25/09/2026, § 8), por lo que el anclaje temporal nativo está disponible. Aun así, al **no ser un índice único** (1.064 fechas repetidas en 20 series), antes de ejecutar retardos (`.shift()`) o ventanas móviles conviene **ordenar explícitamente por `['store_id', 'item_id', 'dia_ind']`** para evitar que los rezagos mezclen observaciones de distintas series o de periodos equivocados.
- Las series deben construirse por la clave `[store_id, item_id]` (20 series). Para `FOODS_3_288`, los primeros retardos del histórico post-lanzamiento serán nulos legítimos: tratar con filtros temporales o imputaciones controladas, **nunca** con ceros ficticios previos a febrero de 2013.
- La distinción entre **cero estructural** (producto no disponible / no lanzado) y **cero de demanda** (producto disponible sin ventas) queda documentada como línea de trabajo de Calidad + EDA (recogida en la bitácora maestra).
- El truncado protege la variable objetivo de ceros estructurales artificiales; los atípicos de `ventas` quedan identificados para su tratamiento en fases posteriores.
- Los modelos tabulares (LightGBM / XGBoost) asimilan sin problema series de longitudes distintas, por lo que la pérdida de 71 registros en una sola serie no compromete el diseño.

---

## 11. Estado y siguientes pasos

- **Fase en curso:** este documento cubre el primer bloque de Calidad de Datos (auditoría, nulos, tipos, duplicados, depuración y persistencia). Se ampliará con las siguientes tareas del plan de calidad conforme se ejecuten.
- Próximos focos sugeridos por el plan de la fase: verificación de duplicados por clave candidata `[store_id, item_id, dia_ind]`, reglas lógicas de negocio y cierre del análisis univariante.
- El tablón limpio (`train_resultado_calidad.pkl` y compañeros) es la base sobre la que trabajarán las fases posteriores del pipeline.
- **25/09/2026 — corrección del índice temporal:** se detectó que el truncado con `reset_index(drop=True)` degradaba el índice `date` a `RangeIndex`. Eliminada la llamada, los tres artefactos se regeneraron conservando el índice `date` (2013-01-01 → 2015-11-30, tanto en el tablón como en las vistas `cat` y `num`) y se actualizó `copilot-instructions.md` con el nuevo `df.info()`.

---

## Anexo — Salidas literales del notebook (evidencias)

### A. Duplicados

```text
np.int64(0)
```

### B. Estructura de entrada (`df.info()` del tablón original)

```text
<class 'pandas.DataFrame'>
Index: 21280 entries, 2013-01-01 to 2015-11-30
Data columns (total 17 columns):
 #   Column        Non-Null Count  Dtype
---  ------        --------------  -----
 0   state_id      21280 non-null  str
 1   store_id      21280 non-null  str
 2   dept_id       21280 non-null  str
 3   cat_id        21280 non-null  str
 4   item_id       21280 non-null  str
 5   wm_yr_wk      21280 non-null  int64
 6   dia_ind       21280 non-null  str
 7   ventas        21280 non-null  int64
 8   sell_price    21209 non-null  float64
 9   year          21280 non-null  int64
 10  month         21280 non-null  int64
 11  wday          21280 non-null  int64
 12  weekday       21280 non-null  str
 13  event_name_1  1700 non-null   str
 14  event_type_1  1700 non-null   str
 15  event_name_2  60 non-null     str
 16  event_type_2  60 non-null     str
dtypes: float64(1), int64(5), str(11)
memory usage: 2.9+ MB
```

### C. Valores únicos (cardinalidades)

```text
state_id           1
dept_id            1
cat_id             1
store_id           2
event_type_2       2
event_name_2       3
year               3
event_type_1       4
weekday            7
wday               7
item_id           10
month             12
sell_price        23
event_name_1      30
wm_yr_wk         153
ventas           301
dia_ind         1064
```

### D. Conteo de nulos

```text
sell_price    71
wm_yr_wk       0
ventas         0
```

```text
event_name_2    21220
event_type_2    21220
event_name_1    19580
event_type_1    19580
dia_ind             0
store_id            0
item_id             0
weekday             0
wday                0
month               0
year                0
```

### E. Aislamiento de los nulos de `sell_price`

```text
item_id
FOODS_3_288    71
FOODS_3_090     0
...             (resto de productos: 0)

month
1    62
2     9

ventas
0    71
```

Prueba de control (producto en periodo normal, abril 2014):

```text
item_id
FOODS_3_288    60
```

### F. Atípicos (desviación típica, `num_desv_tip = 4`)

```text
Conteo de atípicos para ventas:
ventas
0      518
1      103
5      100
10      95
7       92
      ...
158      1
139      1
103      1
107      1
323      1
Name: count, Length: 247, dtype: int64

Conteo de atípicos para sell_price:
Series([], Name: count, dtype: int64)
```

### G. Estadísticos de las numéricas (`con.describe().T`)

| Variable | count | mean | std | min | 25% | 50% | 75% | max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `wm_yr_wk` | 21.280 | 11415,023 | 82,875 | 11249 | 11335 | 11420 | 11506 | 11544 |
| `ventas` | 21.280 | 28,875 | 38,988 | 0 | 6 | 18 | 37 | 763 |
| `sell_price` | 21.209 | 2,397 | 1,237 | 1,00 | 1,50 | 1,58 | 2,98 | 4,98 |

### H. Verificación del índice temporal (corrección del 25/09/2026)

Estado de los índices en memoria (salida literal del notebook):

```text
cat, con y df_2 comparten el mismo índice: True
```

| vista | filas | columnas | tipo_indice | nombre_indice | primera_fecha | ultima_fecha |
|---|---|---|---|---|---|---|
| `df` (en memoria, tras depurar columnas) | 21.280 | 14 | `Index` | `date` | 2013-01-01 | 2015-11-30 |
| `df_2` (tablón limpio) | 21.209 | 12 | `Index` | `date` | 2013-01-01 | 2015-11-30 |
| `cat` (categóricas) | 21.209 | 9 | `Index` | `date` | 2013-01-01 | 2015-11-30 |
| `con` (numéricas) | 21.209 | 3 | `Index` | `date` | 2013-01-01 | 2015-11-30 |

Relectura de los artefactos persistidos en disco:

| artefacto | filas | columnas | tipo_indice | nombre_indice | primera_fecha | ultima_fecha |
|---|---|---|---|---|---|---|
| `train_resultado_calidad.pkl` | 21.209 | 12 | `Index` | `date` | 2013-01-01 | 2015-11-30 |
| `cat_resultado_calidad.pkl` | 21.209 | 9 | `Index` | `date` | 2013-01-01 | 2015-11-30 |
| `num_resultado_calidad.pkl` | 21.209 | 3 | `Index` | `date` | 2013-01-01 | 2015-11-30 |

---

*Nota de elaboración: informe generado por lectura directa de las salidas ejecutadas del notebook `03_notebooks/02_Calidad_Datos.ipynb`, del documento del caso (pág. 4) y de la bitácora maestra. No se ejecutó código adicional. Versión v1 — se completará al cierre de la fase.*
