# Informe de modelización

> **Notebook:** `03_notebooks/07_Modelizacion.ipynb` · El ranking de modelos, la configuración ganadora y las métricas definitivas se añaden al cerrar la fase.

## Lo primero: qué es esta fase

No hay un modelo general: hay **20 modelos**, uno por cada combinación tienda × producto (bottom-up). Aquí se monta la **cadena de montaje** que los entrena, en dos pasos:

1. **Prueba con un solo producto** (`CA_3_FOODS_3_586`): el proceso completo de principio a fin.
2. **Escalar a los 20**: meter ese proceso en una función y recorrerlos con un `for`. Es el patrón **MegaEscalaEstructura** (vault: `Patrones/Patron_ML_01_MegaEscalaEstructura`).

> ⚠️ **No es el modelo final** ni va tal cual a preproducción. Las comprobaciones predicen sobre datos que el modelo ya vio, a propósito, solo para ver que la maquinaria funciona.

## Los datos

1. **20 series:** 2 tiendas (`CA_3`, `CA_4`) × 10 productos. 20.909 filas, unas 1.045 por serie. Ojo: `FOODS_3_288` arranca en febrero de 2013 en las dos tiendas (es un alta), así que sus series son algo más cortas.
2. **Target:** `ventas` (unidades de ese producto en esa tienda ese día).
3. **Predictoras:** `02_datos/03_Entrenamiento/x_preseleccionado.pkl` (75 variables, recorte general de MI). La selección fina por producto queda pendiente (ver el final).

## Prueba con un solo producto

1. **Aislar la serie:** solo `CA_3` + `FOODS_3_586`, y como variables todo menos `date`, `store_id` e `item_id`.
2. **Validación temporal:** `TimeSeriesSplit(3, test_size=10)`. Tres "exámenes": cada uno entrena con todo lo anterior acumulado y predice a ciegas los 10 días siguientes. Nunca se entrena con el futuro.

    | Examen | Entrena con | Predice |
    |---|---|---|
    | 1 | todo salvo los últimos 30 días | los 10 siguientes |
    | 2 | todo salvo los últimos 20 días | los 10 siguientes |
    | 3 | todo salvo los últimos 10 días | los últimos 10 |

3. **Búsqueda simplificada:** `RandomizedSearchCV` sobre un `Pipeline` con `HistGradientBoostingRegressor` (boosting por histogramas, misma familia que LightGBM). Con `n_iter=1` y una parrilla con solo la configuración por defecto, **todavía no se tunea nada**: se deja la estructura lista.
4. **Entrenar** (`.fit()`): pasa por los 3 exámenes y guarda sus errores en `cv_results_` (`split0`, `split1`, `split2`, media y desviación). Después `best_estimator_` se reentrena con todo el histórico de la serie.
5. **Predecir** (`.predict()`): la venta estimada, la $\hat{y}$ ("y con sombrero").
6. **El punto ciego:** el gráfico de real contra predicho usa los mismos días con los que se entrenó, así que sale mejor de lo real. Lo correcto en el modelo final: apartar los últimos días como `x_test` y `y_test`, predecir a ciegas y medir ahí.

**Resultado de los 3 exámenes:** MAE de 10,6 · 10,9 · 14,3 → media de **unas 12 unidades al día (±1,7)**. Es decir, el modelo se equivoca de media en unas 12 unidades diarias. Ilustrativo: falta el tuneo y el test honesto.

## Por qué se quitan los identificadores

Lo que es **constante dentro de una serie no explica nada** de esa serie. En un modelo por tienda × producto, `store_id` e `item_id` valen lo mismo en todas las filas.

| Nivel del modelo | `store_id` | `item_id` |
|---|---|---|
| Tienda × producto (el nuestro) | fuera | fuera |
| Por tienda (varios productos) | fuera | se queda |
| Por ciudad o país | se queda | se queda |

`date` sale por otra razón: es trazabilidad, y el tiempo ya entra por los lags, las ventanas y el calendario.

## El buscador y la parrilla

`Pipeline` = cadena de montaje empaquetada como una sola pieza. El buscador le pide `.fit()` y `.predict()` sin saber qué hay dentro, y los hiperparámetros se nombran con el paso: `algoritmo__learning_rate` es "el learning_rate del paso llamado algoritmo".

| Pieza de `RandomizedSearchCV` | Qué es |
|---|---|
| `estimator` | lo que se prueba: el pipeline |
| `param_distributions` | el catálogo de combinaciones (la parrilla) |
| `n_iter` | cuántas combinaciones se sortean del catálogo |
| `cv` | cómo se examina cada una: el `TimeSeriesSplit` |
| `scoring` | la vara de medir: `neg_mean_absolute_error` (MAE en negativo, porque sklearn siempre maximiza) |
| `n_jobs` | núcleos a usar (−1 = todos) |

Hiperparámetros de la parrilla de la función (comentados, listos para activar):

| Hiperparámetro | Qué controla | Valores |
|---|---|---|
| `learning_rate` | cuánto aprende de cada árbol nuevo; más bajo, más fino y más lento | 4 |
| `max_iter` | número máximo de árboles | 3 |
| `max_depth` | profundidad de cada árbol; más profundo, más riesgo de memorizar | 4 |
| `l2_regularization` | freno contra el sobreajuste | 5 |

**Cuánto cuesta:** entrenamientos = combinaciones probadas × 3 exámenes.

1. Parrilla completa de la función: 4 × 3 × 4 × 5 = **240 combinaciones**. Con `GridSearchCV` (todas) serían 720 entrenamientos por producto, **14.400** para los 20.
2. Con `RandomizedSearchCV`, `n_iter=30`: 90 por producto, **1.800** en total. Explora una parte del catálogo y suele encontrar algo cercano a lo mejor.
3. Hoy, `n_iter=1`: 3 por producto, **60** en total.

## Escalar a los 20 productos

1. **Columna `producto`** = `store_id` + `item_id` (ej. `CA_3_FOODS_3_586`), y se eliminan las dos originales.
2. **`productos = list(x.groupby("producto"))`**: lista de 20 parejas `(nombre, tabla de esa serie)`.
3. **`def modelizar(x_producto, y)`**: el código de la prueba refactorizado; define su `TimeSeriesSplit`, su pipeline y su búsqueda, y devuelve el modelo final de esa serie.
4. **`for`** sobre las parejas: por cada una, toma su trozo de `y`, llama a `modelizar` y guarda `(producto, modelo)` en `lista_modelos`. Al final, 20 modelos etiquetados.
5. **Comprobación:** real contra predicho de los últimos 100 días de cada serie. Con el mismo punto ciego: valida la maquinaria, no la calidad.

## Cosas a pulir

1. **`test_size`:** la demo usa 10 días y la función 8. Unificar con el horizonte de negocio.
2. **`'algoritmo__scoring'` en la parrilla:** `scoring` va en el buscador, no en el algoritmo. Si se descomenta tal cual, da error.
3. **`random_state`:** fijarlo cuando se amplíe la búsqueda, para que los sorteos se puedan repetir.
4. **Métrica:** MAE. El MAPE no sirve aquí: divide por la venta real y hay muchos días a 0.

## Lo que falta para cerrar la fase

1. Meter dentro del bucle la **selección de variables por producto con MI**, idealmente partiendo de las 126 variables y no del recorte general.
2. Activar la parrilla de hiperparámetros y decidir el algoritmo.
3. Evaluación honesta: últimos días apartados como test.
4. Ranking de modelos, interpretabilidad del ganador y guardar la configuración (`06_resultados/Modelizacion/config_mejor_modelo.json`).
