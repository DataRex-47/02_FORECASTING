# Informe de preproducción 

> **Notebook:** `03_notebooks/08_Preproduccion.ipynb` · **Estado:** cerrada. Funciones y los tres procesos (reentrenamiento, evaluación y ejecución) escritos y corridos. Siguiente: despliegue batch.

## Qué es esta fase

Los notebooks 01 a 07 sirvieron para **descubrir** qué hacer. Aquí todo lo que de verdad cambia los datos se **empaqueta en funciones** para que corra solo en producción. El EDA no entra: solo miraba los datos. **Funciones y no pipelines**, porque hay pasos que cambian el número de filas (borrar las filas sin precio, el `dropna` de los lags) y eso no cabe en un pipeline de sklearn.

## Las funciones

| Parte | Función | Qué hace |
|---|---|---|
| Calidad | `calidad_datos` | Se queda con las variables madre (`VAR_MADRE`, del Excel de procesos), pasa `month` a texto, eventos vacíos a `Sin_evento` y borra las filas sin precio (pre lanzamiento) |
| Variables | `crear_variables` | Rotura de stock (3, 7 y 15 días), lags (ventas 1 a 15, precio 1 a 7, rotura 1), ventanas (min, max y media ponderada de 2 a 15), quita las filas sin lags y crea `producto` = tienda_producto |
| Transformación | `transformar_variables_entrenamiento` | Aprende el OHE con todo el histórico y lo guarda con `joblib` |
| Transformación | `transformar_variables_ejecucion` | Abre el OHE guardado y solo lo aplica |
| Transformación | `aplicar_ohe` | Auxiliar de las dos anteriores |
| Preselección | `preseleccion_variables` | MI de **un** producto y sus 75 mejores variables (`nlargest`) |
| Entrenamiento | `modelizar` | Entrena **un** producto: preselección, `TimeSeriesSplit` y búsqueda |
| Entrenamiento | `lanzar_entrenamiento` | Recorre **todos** los productos y guarda la lista `(producto, modelo)` |
| Ejecución | `lanzar_ejecucion` | Predice todos los productos para **un solo día** |
| Ejecución | `forecasting_autorregresivo` | Repite la anterior hasta completar los `HORIZONTE` días (8) |

**Por qué dos funciones de transformación:** el encoder es una plantilla de columnas fijas. Se crea una vez al entrenar, viendo los 3 años, y en cada ejecución se **abre la guardada**. Si se creara una nueva con pocos días, faltarían columnas (un día sin Navidad no tendría la columna de Navidad) y el modelo fallaría.

## Cómo predice 8 días

**En palabras del autor:** Para un modelo de Machine Learning las fechas no existen: entiende columnas, y por eso se le fabrican variables artificiales (lags, promedios, ventanas) que meten el pasado en la fila. Los lags de ventas, del 1 al 15, se llenan en cadena: el lag 1 de un día es la venta del día anterior, el lag 2 es la de dos días antes, y así. Si no tengo la venta de mañana, la fila de pasado mañana queda con el lag 1 vacío, y a partir de ahí se van vaciando los demás. Por eso el modelo predice un solo día y se ejecuta tantas veces como días necesito para el pedido: la primera vuelta predice el día 1, la segunda usa esa predicción para llenar el lag 1 del día 2, la tercera usa las dos anteriores, y así sucesivamente. Las predicciones sirven de insumo para llenar los lags que todavía no existen. Con 15 días de historia se llenan los lags y se predicen 8 días, que es el horizonte del pedido. El precio no bloquea, porque se conoce por adelantado; lo que bloquea son las ventas y la rotura, que sale de ellas. El costo: el error crece en cada vuelta, porque se predice sobre predicciones.

Tres ideas que lo completan:

1. **Una respuesta por fila.** El modelo es multivariable en la entrada pero **univariable en la respuesta**: solo da `ventas`. Como en un scoring, puntúa muchas filas de una vez (los 20 productos de mañana), pero la fila de pasado mañana necesita la respuesta de mañana. Por eso el `shift` y el recursivo.
2. **Por qué bastan 15 días.** Al predecir no se aprende nada: el modelo ya aprendió con unos 1.045 días por producto. Igual que un CRM que le manda a la API la fila de un cliente, se manda **una fila** por producto, armada **aplanando** los últimos 15 días en `ventas_lag1` … `ventas_lag15`. No son una muestra, son 15 columnas. Con los 3 años completos la fila sale igual (comprobado). El 15 lo eligió el analista al crear los lags.
3. **La falsa dimensión temporal.** El modelo no entiende de fechas; el viaje al día siguiente se hace a mano en cada vuelta: escribir la predicción como venta y **borrar el día más antiguo**. `lanzar_ejecucion` predice la fecha más baja con sus 15 lags completos; si no se borrara el 16 de noviembre, el 1 de diciembre se predeciría una y otra vez. Borrar no aumenta el error: lo aumenta usar predicciones como si fueran ventas reales.

**Recursiva y no directa:** la directa usa un modelo por cada día del horizonte: 20 × 8 = 160 modelos (7.300 a un año). La recursiva se queda en 20. Su costo: el día 8 tiene 7 de sus 15 lags predichos (`ventas_lag1` a `ventas_lag7`) y solo 8 reales.

Dibujos en el vault (`ML_Forecasting`, Multi-Step): `Forecast_Recursivo.png`, `Escalera_Lags.png`, `Lags_Reales_vs_Predichos.png` y `Ventana_Deslizante.png`.

## Los tres procesos

| Proceso | Qué hace | Resultado |
|---|---|---|
| Reentrenamiento | `train.pkl` → `calidad_datos` → `crear_variables` → `lanzar_entrenamiento` | `05_modelos/ohe_retail.pkl` y `lista_modelos_retail.pkl` |
| Evaluación | Corte el 30 de noviembre: historia del 16 al 30, se tapan las ventas reales del 1 al 8 de diciembre, el recursivo las predice y se comparan con `validacion.pkl` | **MAE 9,56 a 8 días** |
| Ejecución | CSV de la consulta SQL → `forecasting_autorregresivo` → `07_despliegue/predicciones.csv` | 160 filas (24 al 31 de diciembre), sin negativos |

**Cómo leer el MAE.** Medido como el profesor (a 1 día, el 16 de diciembre, con los 15 días anteriores reales) sale **5,75**; él obtuvo 5,6. El modelo está a la par: el 9,56 es el costo honesto de predecir 8 días. Por día, el error va de 8,1 (1 de diciembre) a 9,0 (8 de diciembre), con un pico de 12 el 6: con solo 20 productos por día, el ruido pesa más que la escalera.

## Evaluación con varias ventanas y modelo base

Una sola ventana de 8 días mide poco, así que la evaluación se repitió en las cuatro semanas de diciembre de 2015. Los cortes fueron el 30 de noviembre y el 8, 16 y 23 de diciembre, siempre con los modelos entrenados hasta el 30 de noviembre y con 15 días reales de historia en cada corte.

Como referencia se usó un modelo base, muy simple: cada serie vende hoy lo mismo que vendió hace 7 días. Sirve para saber cuánto aporta el modelo de verdad.

| Ventana | Base | Modelo |
|---|---|---|
| 1 al 8 de diciembre | 16,17 | 9,55 |
| 9 al 16 de diciembre | 8,31 | 7,89 |
| 17 al 24 de diciembre | 6,91 | 8,97 |
| 24 al 31 de diciembre | 9,81 | 8,69 |
| Promedio | 10,30 | 8,77 |

**Cómo leerlo.** El modelo gana en promedio, con unos 15 % menos de error, y en 3 de las 4 ventanas. En la del 17 al 24 gana el base. El modelo es más parejo: su error va de 7,9 a 9,6, mientras que el base va de 6,9 a 16,2. El base funciona cuando las semanas se parecen y falla cuando la semana anterior fue atípica. Una posible causa en la primera ventana es la semana de Acción de Gracias, pero no está verificada.

**Límites.** El modelo corre con la configuración por defecto (la parrilla de hiperparámetros tiene una sola opción), así que este resultado es un punto de partida y no un techo. Los datos terminan el 31 de diciembre de 2015, por lo que no hay un examen final posterior. Diciembre sirve para evaluar mientras no se use para escoger configuraciones. Si se afina la parrilla, hay que elegir con meses anteriores y dejar diciembre como examen final.

El cálculo del modelo base está en celdas aparte, al final del notebook 08.

**Backtest exportado para Power BI.** Las mismas cuatro ventanas se guardan fila por fila (real, predicho del modelo y predicho del base, con el día del horizonte de 1 a 8) en `07_despliegue/backtest.csv`, generado por `07_despliegue/exportar_backtest.py`. Son 640 filas y los MAE por ventana coinciden con la tabla de arriba. Alimenta la página 2 del tablero, que responde qué tan confiable es el modelo.

## La entrada de la ejecución (consulta SQL)

`forecasting_autorregresivo` recibe la entrada hecha: 15 días reales + 8 a predecir. La arma una **consulta SQL** (la corre el analista o Sistemas) y se guarda como CSV en `07_despliegue/`. Plantilla probada en `07_despliegue/consulta_entrada_ejecucion.sql`. Ejemplo: para predecir del 24 al 31 de diciembre, la historia va del 9 al 23.

| Parte | Cómo se llena |
|---|---|
| Esqueleto | 23 días × 20 series (10 productos en CA_3 y 10 en CA_4) = 460 filas |
| Calendario | Se conoce por adelantado |
| Eventos | Del calendario de festivos. **Vacíos (NULL) si no hay evento, nunca 0**: `event_type_1_Sin_evento` es variable final |
| `sell_price` | Calendario de promociones o, si no hay, el último precio válido. Nunca vacío (`calidad_datos` borraría la fila) |
| `ventas` | Reales hasta el corte; **0 en los días futuros** (el recursivo las sobrescribe) |
| `dept_id`, `cat_id`, `event_name_2`… | En 0 por estructura: `calidad_datos` solo usa `VAR_MADRE` |

En la celda de ejecución: la fecha pasa a texto `aaaa-mm-dd`; los eventos en 0 del CSV del profesor se vacían; y `fecha_corte = entrada.index.unique().sort_values()[-(HORIZONTE + 1)]`, que es escalable porque depende de la forma del archivo, no del mes. Para correr a diario, la consulta debe calcular su ventana desde el día de corte, sin fechas fijas.

## Decisiones frente a un paso anterior

1. **Sin moda en `sell_price`:** se borran las filas pre lanzamiento (la moda metía precios del futuro en el pasado).
2. **OHE y no TE:** la transformación no necesita la `y`.
3. **Transformación fuera del `for`:** una vez con todo, no 20 veces sobrescribiendo el encoder.
4. **`dropna` solo sobre los lags.**
5. **75 variables por producto:** salió del corte del MI general (notebook 05). Es un parámetro.
6. **Predicción por nombre de producto (`map`)** al actualizar el recursivo, sin depender del orden.
7. **Evaluación a 8 días** con el recursivo; el profesor solo evalúa a 1 día.
8. **Constantes en mayúsculas** (`VAR_MADRE`, `VAR_OHE`, `RUTA_OHE`, `RUTA_MODELOS`, `HORIZONTE`).

## Hallazgo de la ejecución: Navidad

El 25 de diciembre la tienda cierra (venta real total: 1 unidad), pero el modelo predijo **481**. En el entrenamiento solo hay 2 navidades por serie y `HistGradientBoosting` exige al menos 20 filas por hoja (`min_samples_leaf=20`), así que no puede aprender ese día. Además, ese error se arrastra como lag a los días siguientes. Arreglo aplicado (04/10): **regla de negocio** en `forecasting_autorregresivo`, si el día es Christmas la venta se pone en 0 antes de pasar al día siguiente. También el piso de 0 (`clip`) en `lanzar_ejecucion`. Falta reejecutar para ver el nuevo `predicciones.csv`.

## Pendiente

1. Reejecutar el notebook 08 (regla de Navidad y `clip` ya puestos) y revisar `predicciones.csv`: el 25 de diciembre debe salir en 0.
2. Despliegue batch : script de ejecución y programación del job.
3. Contrato de datos con Sistemas si la entrada la entregan ellos.
