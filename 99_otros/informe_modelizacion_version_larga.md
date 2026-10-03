# Informe de modelización (en cristiano)

> **Notebook:** `03_notebooks/07_Modelizacion.ipynb` · **Estado:** fase en curso.
> Este documento cuenta, en fácil, el proceso que se está montando (prueba con un producto + escalado a los 20). El ranking final de modelos, la configuración ganadora y las métricas definitivas se añadirán al cerrar la fase.

## Lo primero: qué es esta fase

La fase anterior (preselección) dejó claro que aquí **no habrá un modelo general**: habrá **20 modelos**, uno por cada combinación tienda × producto (enfoque *bottom-up*). Ver `06_resultados/Preseleccion/Informe_Preseleccion_Variables.md`.

En modelización se está montando la **"cadena de montaje"** que entrena un modelo para cada una de esas series y que, cuando se active el tuneo de verdad, decidirá cuál es la mejor configuración. De momento se ha hecho en dos pasos:

1. **Prueba con un solo producto** (`CA_3_FOODS_3_586`): montar el proceso completo de principio a fin y ver que funciona.
2. **Escalar a los 20 productos**: convertirlo en una función y recorrerlos todos con un `for`.

> ⚠️ **Aviso importante:** esto **no es el modelo final** ni irá tal cual a preproducción/scripts. El notebook deja el proceso listo; el entrenamiento definitivo y la evaluación en serio llegan en fases posteriores. En varias comprobaciones se predice incluso sobre datos que el modelo ya vio (está explicado y está hecho a propósito).

## Los datos con los que se trabaja

- **20 series** = 2 tiendas (`CA_3`, `CA_4`) × 10 productos (`FOODS_3_090`, `_120`, `_202`, `_252`, `_288`, `_329`, `_555`, `_586`, `_587` y `_714`).
- En total **20.909 filas** (≈1.045 días por serie; casi 3 años de historia sin huecos de calendario).
- La **target** es `ventas` (unidades de ese producto en esa tienda ese día).
- **Predictoras:** `02_datos/03_Entrenamiento/x_preseleccionado.pkl` (75 variables). El recorte general con MI de la preselección es solo el punto de partida: la selección fina por producto se hará dentro de este proceso (ver "Lo que falta para cerrar la fase").

## Prueba con un solo producto: qué se hizo, paso a paso

1. **Aislar la serie.** Se filtra solo `CA_3` + `FOODS_3_586` y se conservan como variables todas las columnas menos `date`, `store_id` e `item_id` (¿por qué? ver su sección más abajo).

2. **Diseñar la validación temporal.** Se usa `TimeSeriesSplit(3, test_size=10)`: como el proyecto trabaja con un **horizonte de pedidos de 10 días**, el histórico se parte en 3 "exámenes" consecutivos. En cada examen el modelo entrena con todo el pasado y se le pide predecir los 10 días siguientes **a ciegas**; luego la ventana se desplaza y se repite. Nunca se entrena con días posteriores a los que se predicen (sin trampa temporal).

    | Examen | Entrena con | Predice a ciegas |
    |---|---|---|
    | 1 | todo el historial salvo los últimos 30 días | los 10 días siguientes |
    | 2 | todo el historial salvo los últimos 20 días | los 10 días siguientes |
    | 3 | todo el historial salvo los últimos 10 días | los últimos 10 días |

3. **Montar la búsqueda simplificada** (`RandomizedSearchCV`). Se construye la máquina de buscar la mejor configuración sobre un `Pipeline` con `HistGradientBoostingRegressor` (familia de *boosting* por histogramas, la misma familia que LightGBM/XGBoost). Aquí se deja `n_iter=1` y una parrilla que solo contiene la configuración por defecto: **no se está tuneando nada todavía**. Se monta la estructura para que, cuando se active el tuneo real, el resto del código siga funcionando igual.

4. **Entrenar (`.fit()`).** El algoritmo analiza los patrones de venta del pasado y ajusta sus árboles. Como resultado de la búsqueda se obtienen los errores de los 3 exámenes.

5. **Predecir (ŷ).** Con `predict()` se obtiene la venta estimada día a día: eso es la $\hat{y}$ ("y con sombrero"). La `y` real es `ventas`; la predicción es la versión "adivinada" por el modelo.

6. **El punto ciego (y su corrección pendiente).** Al final se pinta real vs. predicho usando **el mismo histórico con el que se reentrenó el modelo**, y ahí se hace un poco de trampa (*leakage*): el modelo ya "vio" esos días y puede recitar lo memorizado, así que el gráfico sale mejor de lo que será en la realidad. Lo correcto —y es la corrección que se implementará cuando el proceso se cierre— es **apartar los últimos 10 días como `y_test`, predecir a ciegas sobre ellos y medir ahí el error**. Como este notebook no es el entregable final (su objetivo es validar la maquinaria), la trampa se deja a propósito y queda documentada.

### Qué devuelve la búsqueda (solo ilustrativo)

Los 3 exámenes de la demo del producto `CA_3_FOODS_3_586` dieron: MAE ≈ 10,6 · 10,9 · 14,3 → media **≈ 12 unidades/día (±1,7)**.

Traducción: "en esa serie, el modelo se equivoca de media en unas 12 unidades al día" durante los exámenes. No es una foto de la calidad final (faltan el tuneo y el test honesto); solo ilustra el tipo de salida que produce el proceso.

## Por qué se quitan los identificadores (`date`, `store_id`, `item_id`)

Regla de oro: **lo que es constante dentro de una serie no puede explicar nada de esa serie**. Si el modelo se entrena solo con los datos de un producto de una tienda, `store_id` e `item_id` valen lo mismo en todas las filas: no aportan nada y sobran.

El comentario del notebook **es correcto**: si se modelizara en otro nivel (por ejemplo, un modelo por tienda juntando productos), `item_id` variaría y sí podría aportar. En general:

| Nivel del modelo | `store_id` | `item_id` |
|---|---|---|
| Tienda × producto (el nuestro) | fuera (constante) | fuera (constante) |
| Por tienda (varios productos) | fuera (constante) | se queda (varía) |
| Por ciudad (varias tiendas) | se queda | se queda |
| Por país | se queda | se queda |

Dos matices:

- `date` no se quita "por ser identificador", sino porque es texto de trazabilidad: el tiempo ya entra al modelo por vías mejores (lags, ventanas móviles, calendario).
- La lógica asume que la target se agrega al mismo nivel que el modelo (si el modelo fuera por tienda, la target sería la venta total de la tienda ese día).

## El Pipeline y sus "testeos"

Un `Pipeline` es una **cadena de montaje**: los pasos que hay que aplicarle a los datos antes y durante el entrenamiento, empaquetados como una sola pieza. Aquí la cadena lleva un solo paso (el algoritmo), pero deja la puerta abierta a añadir más adelante (escalado, codificación…). ¿Por qué se usa?

- El buscador trata el pipeline como un único modelo: le pide `.fit()` y `.predict()` una vez, sin saber qué hay dentro.
- Los hiperparámetros se direccionan con el nombre del paso: `algoritmo__learning_rate` = "el `learning_rate` del paso llamado `algoritmo`".
- Cambiar de algoritmo o añadir un paso se hace en un solo sitio del código.

**¿Cómo se "testea" el pipeline?** Dentro del buscador: cada combinación candidata pasa por los 3 exámenes del `TimeSeriesSplit`, se entrena 3 veces y se guardan los 3 errores + su media y desviación (columna a columna en `cv_results_`: `split0`, `split1`, `split2`…). Ese es todo el testeo necesario aquí: **pipeline + validación temporal = máquina de examinar**.

## La matemática de la búsqueda (cuántos modelos hay por detrás)

### Qué significa cada pieza

`RandomizedSearchCV` (el buscador):

| Parámetro | Qué es |
|---|---|
| `estimator` | Lo que se prueba: aquí, el pipeline completo |
| `param_distributions` | El catálogo de combinaciones posibles (la parrilla) |
| `n_iter` | Cuántas combinaciones del catálogo se sortean. Con 1, solo una; con 50, 50 al azar |
| `cv` | Cómo se examina cada combinación: aquí, `TimeSeriesSplit` (3 exámenes temporales) |
| `scoring` | La vara de medir: `neg_mean_absolute_error` = el MAE en negativo (sklearn siempre "maximiza"; el signo lo arregla) |
| `n_jobs` | Procesadores a usar (−1 = todos) |
| `verbose` | Cuánto va contando por pantalla |

Los hiperparámetros de la parrilla (ahora comentados en el código, listos para activar):

| Hiperparámetro | Qué controla | Valores del ejemplo (nº) |
|---|---|---|
| `learning_rate` | Cuánto aprende de cada árbol nuevo. Más bajo = pasos más finos (más lento, más preciso) | 0.01–0.1 (4) |
| `max_iter` | Número máximo de árboles (iteraciones de boosting) | 300–800 (3) |
| `max_depth` | Profundidad máxima de cada árbol. Más profundo = más capacidad y más riesgo de memorizar | 3–10 (3) |
| `l2_regularization` | Castigo por complejidad: freno anti-sobreajuste | 0–1 (5) |

*(`scoring` no es un hiperparámetro del algoritmo: va en el buscador, no en la parrilla.)*

### Cuánto costaría probar la parrilla grande

Fórmula: **entrenamientos = combinaciones probadas × 3 exámenes** (+ 1 reentreno final del ganador con todo el histórico de la serie).

- **Parrilla completa:** 4 × 3 × 3 × 5 = **180 combinaciones** por producto.
- **`GridSearchCV`** (probaría todas): 180 × 3 = **540 entrenamientos por producto** → × 20 productos = **10.800 entrenamientos**. Demasiado para repetirlo en cada serie y en cada prueba.
- **`RandomizedSearchCV`** (sortea unas cuantas y se queda con la mejor): n_iter × 3.
    - Hoy (`n_iter=1`): 3 por producto → **60 en total** (la prueba del proceso).
    - `n_iter=30`: 90 por producto → **1.800 en total**.
    - `n_iter=50`: 150 por producto → **3.000 en total**.

Es decir, el buscador aleatorio explora una fracción del catálogo a una fracción del coste, y normalmente encuentra una configuración cercana a la mejor. (La parrilla "equivalente" de la función tiene 240 combinaciones: mismo orden de magnitud.)

Y ojo: en la prueba actual el buscador **no busca nada** (`n_iter=1` y una sola opción en la parrilla). Su valor, hoy, es montar la estructura y pasar el pipeline por los 3 exámenes. Se deja así a propósito.

## Escalar a los 20 productos (la cadena de montaje completa)

### 1. Preparar el tablón

Se crea la columna `producto` = `store_id` + `item_id` (p. ej. `CA_3_FOODS_3_586`) y se eliminan `store_id` e `item_id`: ya están dentro del nombre y, como se explicó, no son variables.

### 2. Partir el tablón en 20 parejas (tuplas)

`productos = list(x.groupby("producto"))` devuelve una lista en la que **cada elemento es una pareja `(nombre, tabla)`**:

| Pareja | Contenido |
|---|---|
| `('CA_3_FOODS_3_090', …)` | los ≈1.045 días de ese producto en esa tienda |
| `('CA_3_FOODS_3_120', …)` | … |
| … | … (20 parejas en total) |

La misma estructura sirve a cualquier nivel: si mañana se modelizara ciudad × tienda × producto, cada pareja se llamaría `('CIUDAD_TIENDA_PRODUCTO', tabla)` y el resto del proceso no cambiaría.

### 3. Empaquetar el proceso en una función

El código de la prueba se refactoriza en `def modelizar(x_producto, y)`: recibe la tabla de una serie y su trozo de target, y dentro define su propio `TimeSeriesSplit`, su pipeline y su búsqueda. Entrena y **devuelve el modelo final de esa serie**.

### 4. Recorrer y guardar con un `for`

Se recorre la lista de parejas; por cada producto se llama a `modelizar(...)` y el resultado se apila como otra pareja `(producto, modelo)` en `lista_modelos` (una lista que empieza vacía). Al final: **20 modelos entrenados, cada uno etiquetado con su serie**.

### 5. Comprobación final (con su aviso)

Por cada modelo se predicen las ventas de su serie y se pinta real vs. predicho (últimos 100 días). ⚠️ Vuelve a aparecer el punto ciego: se predice sobre datos ya vistos, así que las curvas salen mejor de lo real. **Es la comprobación de que la maquinaria funciona; no es una evaluación.**

## Observaciones y cosas a pulir (revisión rápida)

1. **El comentario de los identificadores está bien** (ver su sección). No hay nada que corregir ahí.
2. **`test_size`**: la demo usa 10 días (coherente con el horizonte de pedidos) y la función usa 8. Conviene unificar si el horizonte de negocio son 10.
3. **`'algoritmo__scoring'` dentro de la parrilla**: `scoring` va en el buscador, no en el algoritmo. Si se descomenta tal cual, daría error.
4. **Detalles menores**: fijar `random_state` cuando la búsqueda se amplíe (para que los sorteos sean reproducibles); el `.fit()` final sobre `best_estimator_` es un reentreno duplicado (inocuo, se puede omitir).
5. **El "punto ciego"** está asumido y documentado: es una prueba de proceso, no una evaluación.

## Salvedades

- Todo lo que se mida aquí es **validación cruzada sobre la muestra de entrenamiento**, no un resultado de producción.
- Las comprobaciones visuales entrenan y evalúan sobre lo mismo, a propósito, para validar el proceso.
- El modelo definitivo (con todos los datos) y la evaluación sobre el **dataset de validación externo** se harán en una fase posterior, cuando existan los pipelines de preprocesamiento correspondientes.

## Lo que falta para cerrar la fase

1. Integrar dentro del bucle la **selección de variables por producto** (MI), como pidió el informe de preselección.
2. Decidir el algoritmo (o comparar varios) y **activar la parrilla de hiperparámetros** de verdad.
3. Pasar a la búsqueda la **métrica principal** acordada (MAE / RMSE / MAPE).
4. Construir el **ranking comparativo** de modelos (mejor score, desviación, hiperparámetros).
5. Interpretabilidad del ganador (importancias internas y/o Permutation Importance).
6. Congelar la **configuración ganadora** (`06_resultados/Modelizacion/config_mejor_modelo.json`), guardar los resultados y cerrar este informe.

---

*Nota de elaboración: informe generado a partir de las salidas ejecutadas del notebook `03_notebooks/07_Modelizacion.ipynb` y del contexto de las fases anteriores (calidad, EDA, transformación y preselección). Versión v1 — se completará al cierre de la fase.*
