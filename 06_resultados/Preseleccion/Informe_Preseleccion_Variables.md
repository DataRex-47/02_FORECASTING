# Informe de preselección de variables (en cristiano)

## Lo primero: qué fue esta fase

Esta fase **no** buscaba quedarse con las mejores variables de todo el tablón junto. Eso no tendría sentido, porque no habrá un modelo general: habrá **20 modelos**, uno por cada combinación tienda × producto (bottom-up).

Lo que se hizo fue un **borrador de prueba**: probar los 3 métodos (MI, RFE y PI) sobre el tablón completo para ver cómo se comportan y elegir con cuál se hará después la selección **dentro de cada uno de los 20 modelos**, con un `for`, en la modelización.

| Cosa | Detalle |
|---|---|
| Entrada | `02_datos/03_Entrenamiento/df_tablon_transformado.pkl` (20.909 filas × 130 columnas) |
| Predictoras (x) | 126 (todo menos `date`, `store_id`, `item_id` y `ventas`) |
| Target (y) | `ventas` |
| Método elegido para los 20 modelos | **Mutual Information** |

## Los 3 métodos, en fácil

| Método | Qué hace | ¿Entrena un modelo? | Cuántas deja aquí |
|---|---|---|---|
| **MI (Mutual Information)** | Mide, variable por variable, cuánta información da sobre las ventas | **No.** Es un cálculo estadístico directo entre cada columna y la target | **75** (corte elegido mirando el gráfico) |
| **RFE** | Entrena XGBoost, quita la variable que menos aporta y vuelve a entrenar, hasta quedarse con las que se le pidan | **Sí, muchas veces:** uno por cada variable que quita | **63** (no se le dijo cuántas, y por defecto deja la mitad: 126 ÷ 2) |
| **PI (Permutation Importance)** | Con un modelo ya entrenado, desordena una columna y mide cuánto empeora el error. Si empeora mucho, la variable importaba | **Sí, una vez.** Después solo predice con columnas desordenadas | **74** (corte elegido mirando el gráfico) |

Los cortes (75, 63, 74) son **prácticos**, no óptimos demostrados. Como los tamaños son distintos, la comparación sirve para ver coincidencias entre listas, no para declarar un ganador.

## Decisiones tomadas

1. **Se usará Mutual Information dentro de cada uno de los 20 modelos.** Motivo: al hacer tantos modelos se quiere un control consistente. Si en algún producto otro método dejara un pool muy pequeño de variables, LightGBM se quedaría con poco donde escoger.
2. **Se descartó RFECV y se dejó RFE.** RFECV llevaba más de 11 minutos entrenando (5 folds multiplican el coste) y su validación cruzada por defecto no respeta el tiempo: corta el tablón en bloques y en algunos pliegues entrena con fechas posteriores a las que valida. En forecasting hay que entrenar con lo viejo y validar con lo nuevo.
3. **Sí se guarda un dataset** con el recorte general de MI, como punto de partida reutilizable, no como selección final.

## Salvedades

1. **PI se calculó con MAPE como métrica.** El MAPE divide por la venta real y aquí hay muchos días con venta 0 (roturas), así que los errores se disparan (importancias del orden de 10^14). El ranking de PI puede estar distorsionado. Para repetirlo, mejor usar el MAE (`scoring='neg_mean_absolute_error'`).
2. **PI se midió sobre los mismos datos con los que se entrenó el modelo**, lo que da una importancia algo optimista. Para un borrador vale.
3. En la celda de PI pone `njobs=-1` en vez de `n_jobs=-1`. XGBoost lo ignora (por eso sale el aviso), pero no cambia el resultado.

## Lo que necesita el siguiente agente (modelización)

1. **Predictoras:** `02_datos/03_Entrenamiento/x_preseleccionado.pkl` (75 variables de MI + `date`, `store_id`, `item_id` para identificar cada serie).
2. **Target:** `02_datos/03_Entrenamiento/y_preseleccionado.pkl` (columna `ventas`).
3. **Lista de variables:** `01_Documentos/Variables_preseleccionadas.txt`.
4. **Tarea:** recorrer las 20 combinaciones tienda × producto con `for` y, dentro de cada una, hacer **su propia selección con MI** y su modelo con **LightGBM**. `date`, `store_id` e `item_id` no son predictoras.
5. Si en la modelización se usa validación, que sea **temporal** (por ejemplo `TimeSeriesSplit`), nunca al azar.
