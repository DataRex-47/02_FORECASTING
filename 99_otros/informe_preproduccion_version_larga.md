# Informe de preproducción (en cristiano)

> **Notebook:** `03_notebooks/08_Preproduccion.ipynb` · **Estado:** funciones y procesos escritos (reentrenamiento, evaluación y ejecución). Falta correr la ejecución completa y pasarla al despliegue batch.

## Qué es esta fase

Los notebooks 01 a 07 sirvieron para **descubrir** qué hacer (calidad, EDA, transformación, preselección, modelización). Aquí todo lo que de verdad cambia los datos se **empaqueta en funciones** para que corra solo, de principio a fin, en producción. El EDA no entra: solo miraba los datos.

## Por qué funciones y no pipelines

En este caso hay pasos que **cambian el número de filas** (eliminar las filas sin precio, el `dropna` de los lags), y eso no cabe dentro de un pipeline de sklearn. Con funciones se controla cada paso.

## Las funciones, en orden

| Función | Qué hace |
|---|---|
| `calidad_datos` | Se queda solo con las variables madre (`VAR_MADRE`, sacadas del Excel de procesos), pasa `month` a texto, rellena los eventos vacíos con `Sin_evento` y elimina las filas sin precio (pre lanzamiento) |
| `crear_variables` | Rotura de stock (3, 7 y 15 días), lags (ventas 1 a 15, precio 1 a 7, rotura 1), ventanas (min, max y media ponderada de 2 a 15), quita las filas sin lags y crea `producto` = tienda_producto |
| `transformar_variables_entrenamiento` | Aprende el OHE con todo el histórico y lo guarda con `joblib` |
| `transformar_variables_ejecucion` | Carga ese OHE guardado y solo lo aplica |
| `aplicar_ohe` | Auxiliar de las dos anteriores para no repetir código |
| `preseleccion_variables` | Mutual information de un producto y se queda con sus 75 mejores variables (`nlargest`) |
| `modelizar` | **1.** Modeliza **un** producto: preselección, `TimeSeriesSplit` y búsqueda; devuelve su mejor modelo |
| `lanzar_entrenamiento` | **2.** Modeliza **todos** los productos con un `for` y guarda la lista `(producto, modelo)` |
| `lanzar_ejecucion` | **3.** Predice todos los productos pero **un solo día** |
| `forecasting_autorregresivo` | **4.** Repite la 3 ocho veces para predecir **8 días** |

La modelización se divide en dos partes, cada una con dos funciones:

| Parte | Función | Qué hace |
|---|---|---|
| Entrenamiento | `modelizar` | Entrena **un** producto con sus particularidades |
| Entrenamiento | `lanzar_entrenamiento` | Recorre **todos** los productos y guarda sus modelos |
| Ejecución | `lanzar_ejecucion` | Predice todos los productos para **un solo día** |
| Ejecución | `forecasting_autorregresivo` | Repite la anterior hasta completar los días de `HORIZONTE` |

## Por qué dos funciones de transformación

El encoder es como una plantilla con columnas fijas. Se crea y se guarda una vez, al entrenar, viendo los 3 años. Cada día de ejecución se **abre la guardada**: si se creara una nueva con pocos días, faltarían columnas (un día sin Navidad no tendría la columna de Navidad) y el modelo fallaría.

## El forecast recursivo, en tres líneas

Un modelo de ML con lags **solo predice el día siguiente** (ARIMA, en cambio, proyecta varios días de una vez). Para predecir 8 días:

1. Para predecir el **lunes** usa la venta real del **domingo**.
2. Para el **martes** necesita la del lunes, que no existe todavía: usa **su predicción del lunes**.
3. Para el **miércoles** usa su predicción del martes. Y así hasta 8 días.

**Por qué bastan 15 días.** Al predecir no se reentrena nada: el modelo ya aprendió con unos 1.045 días por producto. Igual que un CRM que le manda a la API la fila de un cliente y recibe su scoring, aquí se manda **una fila** por producto. Esa fila se arma **aplanando** los últimos 15 días: el `shift` los gira de vertical a horizontal y los convierte en `ventas_lag1` … `ventas_lag15`. Las 15 filas no son una muestra, son las 15 columnas de una sola fila. Con los 3 años completos la fila saldría con los mismos números (comprobado con FOODS_3_090 en CA_3 el 1 de diciembre), salvo un pequeño cambio en la media ponderada (`ventasmmp`), que mira algo más atrás. El 15 lo eligió el analista al crear los lags del 1 al 15.

**En palabras del autor:** Para un modelo de Machine Learning las fechas no existen: entiende columnas, y por eso se le fabrican variables artificiales (lags, promedios, ventanas) que meten el pasado en la fila. Los lags de ventas, del 1 al 15, se llenan en cadena: el lag 1 de un día es la venta del día anterior, el lag 2 es la de dos días antes, y así. Si no tengo la venta de mañana, la fila de pasado mañana queda con el lag 1 vacío, y a partir de ahí se van vaciando los demás. Por eso el modelo predice un solo día y se ejecuta tantas veces como días necesito para el pedido: la primera vuelta predice el día 1, la segunda usa esa predicción para llenar el lag 1 del día 2, la tercera usa las dos anteriores, y así sucesivamente. Las predicciones sirven de insumo para llenar los lags que todavía no existen. Con 15 días de historia se llenan los lags y se predicen 8 días, que es el horizonte del pedido. El precio no bloquea, porque se conoce por adelantado; lo que bloquea son las ventas y la rotura, que sale de ellas. El costo: el error crece en cada vuelta, porque se predice sobre predicciones.

Dibujo: vault `Recursos-Assets/Forecast_Recursivo.png` (nota `ML_Forecasting`, Multi-Step Forecasting).

**Una respuesta por fila:** El modelo es **multivariable en la entrada** (usa muchas columnas predictoras) pero **univariable en la respuesta**: solo predice `ventas`, porque es la única `y` con la que se entrenó. Da **una respuesta por fila**, no una sola en total. En un scoring (a quién llamar, quién contratará) cada fila de cliente ya tiene hoy todas sus columnas completas, así que se puntúan miles de filas de una vez y sale un CSV largo. En forecasting también se predicen muchas filas de una vez (los 20 productos de mañana), pero no las de los días siguientes: sus columnas de lags dependen de la respuesta del día anterior. La diferencia no es el modelo, es que en forecasting **una fila necesita la respuesta de otra**. Por eso hace falta el `shift` y el recursivo, y por eso nuestro CSV final también es largo: 20 productos × 8 días = 160 filas.

**Cómo "viaja" en el tiempo una herramienta que no entiende de fechas.** Se incluye una **falsa dimensión temporal**: el tiempo entra como columnas (lags, ventanas, calendario), y el viaje al día siguiente se hace a mano, con dos movimientos por vuelta. Uno: escribir la predicción como venta del día. Dos: borrar el día más antiguo de la ventana. `lanzar_ejecucion` siempre predice la fecha más baja que tiene sus 15 lags completos. Si no se borrara el 16 de noviembre, el 1 de diciembre seguiría completo y se predeciría una y otra vez: no da error, se queda repitiendo el mismo día. Al borrarlo, el 1 de diciembre pierde su lag 15 y se cae en el `dropna`, así que la fecha más baja completa pasa a ser el 2 de diciembre. Borrar no aumenta el error: lo que lo aumenta es usar predicciones como si fueran ventas reales.

Dibujo: vault `Recursos-Assets/Ventana_Deslizante.png`.

**Por qué recursiva y no directa.** Las dos formas de predecir varios días son la directa (un modelo por cada día del horizonte) y la recursiva (un modelo que se reutiliza día a día). La directa daría 20 productos × 8 días = 160 modelos, y a un año serían 7.300: inmantenible. La recursiva se queda en 20. Su costo es que el error crece: el último día tiene 7 de sus 15 lags predichos y solo 8 reales.

| Día 8 | `ventas_lag1` … `ventas_lag7` | `ventas_lag8` … `ventas_lag15` |
|---|---|---|
| Origen | **Predichos** (7) | Reales (8) |

La escalera completa, día por día, está en el vault: `ML_Forecasting`, sección Multi-Step.

## Quién llama a quién

| Proceso | Llama a |
|---|---|
| Reentrenamiento | `calidad_datos` → `crear_variables` → `lanzar_entrenamiento` (que transforma, y en su `for` llama a `modelizar`, que llama a `preseleccion_variables`) |
| Ejecución | `forecasting_autorregresivo` (que en cada vuelta llama a `calidad_datos` → `crear_variables` → `lanzar_ejecucion`) |

## Decisiones y cambios frente al profesor

1. **Sin moda en `sell_price`:** se eliminan las filas pre lanzamiento. La moda metía precios del futuro en el pasado.
2. **OHE y no TE,** así que la transformación no necesita la `y`.
3. **La transformación va fuera del `for`:** una sola vez con todo, no 20 veces sobrescribiendo el mismo encoder.
4. **`dropna` solo sobre los lags,** para no borrar filas por columnas que no importan.
5. **Por qué 75 variables:** salió del corte visual del MI general (notebook 05) y se usa igual en cada producto por simplicidad. Es un parámetro y se puede afinar.
6. **Al actualizar la predicción en el recursivo** cada fila busca la de su producto por nombre (`map`), sin depender del orden de las filas.
7. **Constantes en mayúsculas** (`VAR_MADRE`, `VAR_OHE`, `RUTA_OHE`, `RUTA_MODELOS`, `HORIZONTE`): lo que puede cambiar se toca en un solo sitio.

## Evaluación a 8 días (la nota real)

Nos paramos el 30 de noviembre (el corte): historia del 16 al 30 de noviembre, se tapan las ventas reales del 1 al 8 de diciembre, el recursivo las predice y se comparan con las reales de `validacion.pkl`, que el modelo nunca vio.

**MAE a 8 días = 9,56 unidades** por día y producto (160 predicciones: 20 productos × 8 días). El profesor evalúa solo a 1 día (el 16 de diciembre, con los 15 días anteriores reales) y obtiene 5,6. Con nuestro modelo, medido igual que él, sale **5,75**: el modelo está a la par. La diferencia con 9,56 es el costo honesto de predecir 8 días, por la escalera de lags predichos.

En esa prueba aparece una predicción negativa (−2 en CA_4 FOODS_3_090): falta el piso de 0 (`.clip(lower=0)`) en `lanzar_ejecucion`.

## Los datos de entrada de la ejecución (consulta SQL)

`forecasting_autorregresivo` no arma su entrada: la recibe hecha. La entrega una **consulta SQL** (la corre el analista o Sistemas) y se guarda como CSV en `07_despliegue/`. Ejemplo: para predecir del 24 al 31 de diciembre, la historia real va del 9 al 23.

| Parte del archivo | Cómo se llena |
|---|---|
| Esqueleto | Cada día de la ventana por cada serie: 23 días × 20 series (10 productos en CA_3 y 10 en CA_4) = 460 filas |
| Calendario (`date`, `weekday`, `month`) | Se conoce por adelantado: se proyecta sin problema |
| Eventos (`event_name_1`, `event_type_1`) | Del calendario de festivos, que también se conoce. **Vacíos (NULL) cuando no hay evento, nunca 0**: en nuestro modelo `event_type_1_Sin_evento` es variable final, y un 0 lo convertiría en una categoría que no existe |
| `sell_price` | El punto conflictivo con negocio. Opción 1: el calendario de promociones planificado. Opción 2: el último precio válido de cada serie. No puede quedar vacío (`calidad_datos` borraría la fila) |
| `ventas` | Reales hasta el corte; **0 en los días futuros**. El recursivo las sobrescribe con sus predicciones |
| `dept_id`, `cat_id`, `state_id`, `event_name_2`, `event_type_2`… | Se pueden dejar en 0 por estructura: `calidad_datos` solo usa `VAR_MADRE` |

La consulta (plantilla, probada sobre `hipermercado.db` con la tabla de ventas en formato largo: 460 filas, sin precios vacíos) está en `07_despliegue/consulta_entrada_ejecucion.sql`:

```sql
-- Entrada de la ejecucion: 15 dias reales + 8 dias a predecir
-- Ejemplo: predecir del 24 al 31 de diciembre de 2015 (historia real: del 9 al 23)
-- Plantilla: ventas_diarias es la tabla de ventas en formato largo (fecha, tienda, producto, ventas)
WITH ventana AS (                 -- calendario de los 23 dias: se conoce por adelantado
    SELECT date, wm_yr_wk, weekday, month, event_name_1, event_type_1
    FROM calendar
    WHERE date BETWEEN '2015-12-09' AND '2015-12-31'
),
series AS (                       -- las 20 series: 10 productos en CA_3 y 10 en CA_4
    SELECT DISTINCT store_id, item_id FROM ventas_diarias
),
esqueleto AS (                    -- cada dia por cada serie (asi existen tambien los dias futuros)
    SELECT v.*, s.store_id, s.item_id
    FROM ventana v CROSS JOIN series s
),
ultimo_precio AS (                -- alternativa 2: ultimo precio valido hasta el corte
    SELECT p.store_id, p.item_id, p.sell_price
    FROM sell_prices p
    WHERE p.wm_yr_wk = (SELECT MAX(p2.wm_yr_wk) FROM sell_prices p2
                        WHERE p2.store_id = p.store_id AND p2.item_id = p.item_id
                          AND p2.wm_yr_wk <= (SELECT wm_yr_wk FROM calendar WHERE date = '2015-12-23'))
)
SELECT e.date, e.store_id, e.item_id,
       CASE WHEN e.date <= '2015-12-23' THEN d.ventas ELSE 0 END AS ventas,   -- futuro en 0: lo sobrescribe el recursivo
       COALESCE(p.sell_price, u.sell_price) AS sell_price,                    -- precio planificado (promos) o ultimo valido
       e.month, e.weekday, e.event_name_1, e.event_type_1                     -- eventos: NULL si no hay (no 0)
FROM esqueleto e
LEFT JOIN ventas_diarias d ON d.date = e.date AND d.store_id = e.store_id AND d.item_id = e.item_id
LEFT JOIN sell_prices p ON p.wm_yr_wk = e.wm_yr_wk AND p.store_id = e.store_id AND p.item_id = e.item_id
LEFT JOIN ultimo_precio u ON u.store_id = e.store_id AND u.item_id = e.item_id
ORDER BY e.date, e.store_id, e.item_id;
```

Respaldo: el CSV del profesor, `07_despliegue/DatosParaProduccion.csv`. Ojo: ahí `event_type_1` viene en 0 en los días futuros, lo que en nuestro modelo daría una categoría inexistente.

## Los tres procesos

| Proceso | Qué hace |
|---|---|
| Reentrenamiento | `train.pkl` → `calidad_datos` → `crear_variables` → `lanzar_entrenamiento` (guarda el encoder y los 20 modelos) |
| Evaluación | Corte el 30 de noviembre, se tapan las ventas del 1 al 8 de diciembre, `forecasting_autorregresivo` y comparación con lo real: MAE 9,56 a 8 días (5,75 a 1 día, igual que el profesor) |
| Ejecución | CSV de la consulta SQL → `forecasting_autorregresivo` → `07_despliegue/predicciones.csv` (fecha, tienda, producto y venta predicha: 160 filas) para Power BI |

## La celda de ejecución

1. Lee el CSV de la consulta SQL (`;`, fecha `dd/mm/aaaa`) y pasa la fecha a texto `aaaa-mm-dd` como índice, igual que en el entrenamiento.
2. Vacía los eventos que vengan en 0 (el CSV del profesor los trae así) para que `calidad_datos` los convierta en `Sin_evento`.
3. Calcula `fecha_corte` como la fecha que queda justo antes de los `HORIZONTE` días: `entrada.index.unique().sort_values()[-(HORIZONTE + 1)]`. Es escalable porque depende de la forma del archivo (15 + 8 días), no del mes. Para correrlo a diario, la consulta debe calcular su ventana desde el día de corte, sin fechas fijas.
4. `forecasting_autorregresivo` predice los 8 días y se guardan en `07_despliegue/predicciones.csv` (fecha, tienda, producto y venta predicha) para Power BI.

## Pendiente

1. Revisar `predicciones.csv` (160 filas, sin negativos si se aplica el `clip`).
2. Pasar todo al despliegue batch (clases 40 y 41): script de ejecución y programación del job.
3. Contrato de datos con Sistemas si la entrada la entregan ellos.
