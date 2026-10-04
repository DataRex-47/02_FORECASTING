---
tags: [bitacora, forecasting, caso-ml, contexto]
aliases: [Bitácora Forecasting, Contexto del Proyecto 2]
date: 2026-09-24
updated: 2026-10-04
status: 🌿 (Budding)
---

# 🧭 Bitácora Maestra — Caso 2 · Forecasting Retail

> [!SUMMARY] Para qué sirve
> Reengancharte en 3 minutos y practicar sin releer los notebooks.
> Cada fase trae: pregunta de recall → qué pasó → qué quedó en disco → ⚙️ cómo se hizo → 🏋️ ejercicio.
> **El contexto del caso (negocio, jerarquía, reconciliación) no está aquí**: está en la nota del vault `Casos_ML/Caso_02_Forecasting_Retail.md`. Aquí solo va el seguimiento.

---

## 📍 Dónde estoy

**Fases 01 → 08 cerradas (04/10/2026).** Preproducción refactorizada en funciones, con reentrenamiento, evaluación (MAE 9,56 a 8 días; 5,75 a 1 día) y ejecución corridos. `07_despliegue/predicciones.csv` listo para Power BI.

Del EDA salieron tres decisiones: modelizar a nivel **tienda-producto**, crear una **variable que capture la demanda intermitente** y usar **LightGBM**. Cómo se resuelve cada problema, explicado: `Casos_ML/Forecasting_Soluciones.md` (vault).

**Siguiente acción (chat Parte 6):** reejecutar el notebook 08 (regla de Navidad y `clip` ya puestos) y despliegue batch (clases 40 y 41).

> [!IMPORTANT] 📌 Para releer — por qué se añaden variables exógenas
> Sin el precio, la media móvil se come un bache de ventas y el modelo lo arrastra hacia
> adelante como si fuera tendencia. Con el precio, el modelo ve la causa y sabe que fue
> temporal. La nota completa, con el ejemplo 300 → 90 → 300: `ML_Forecasting.md` (vault),
> sección *Por qué se añaden variables exógenas*.

---

## 🔗 La cadena

```
A_01 Import ─► A_02 Calidad ─► A_03 EDA ─► A_04 Transform ─► A_05 Preselección ─► A_07 Modelo ─► A_08/A_09 ─► A_10 Batch
    ✅             ✅             ✅            ✅                 ✅              📍 AQUÍ         ⬜            ⬜
```

**Diferencia con el caso 1:** aquí la salida no es una API, es un **proceso batch** que deja una tabla de predicciones a 8 días, y encima un tablero.

---

## 📊 Números del caso

| Dato | Valor |
|---|---|
| Histórico de entrenamiento | 2013-01-01 → 2015-11-30 (1.064 días) |
| Validación | **diciembre 2015** (2015-12-01 → 2015-12-31), separada por tiempo |
| Horizonte a predecir | 8 días |
| Grano | tienda × producto × día |
| Series | 20 (2 tiendas × 10 productos) |
| Tablón tras calidad | 21.209 filas × 12 columnas (21.280 − 71 filas previas al lanzamiento de `FOODS_3_288`) |
| Tablón tras transformación | 20.909 filas × 130 columnas (tras el `dropna()` de calentamiento) |
| Tablón preseleccionado (MI) | 20.909 filas × 78 columnas (75 variables + `date`, `store_id`, `item_id`) |
| Peso de cada tienda | CA_3 **80 %** · CA_4 20 % (según producto, CA_4 pesa entre el 10,8 % y el 28,9 %) |

---

## 🧱 Los cuatro retos del caso — estado

| Reto | Decisión | Estado |
|---|---|---|
| Forecasting jerárquico + reconciliación | Se modeliza a nivel **tienda-producto**; si se pide el total, se reconcilia | ✅ decidido |
| Demanda intermitente | **Variable sintética de posible rotura** (no hay inventario) | ✅ decidido · se construye en 04 |
| Modelización masiva de SKU | **LightGBM** | ✅ decidido |
| Horizonte a 8 días | Estrategia multi-horizonte | ⬜ pendiente de materia |

---

## 1️⃣ Importación · A_01 ✅

> [!QUESTION]- ¿Por qué la validación no se separa al azar, como en el caso 1?
> Porque en forecasting el orden temporal **es** la información. Un split aleatorio metería días de diciembre en el entrenamiento y le enseñaría el futuro al modelo. La validación son **las últimas observaciones**: todo diciembre de 2015.

- Fuente: una base SQLite (`hipermercado.db`) con tres tablas — `calendar`, `sales` (en formato ancho: una columna por día) y `sell_prices` (precio por semana).
- `sales` se pasó a formato largo con `melt`, y se unió con el calendario por día y con los precios por tienda, producto y semana.
- Fecha como índice. Validación = diciembre de 2015; entrenamiento = todo lo anterior.

**En disco:** `02_Validacion/validacion.pkl` · `03_Entrenamiento/train.pkl` (21.280 × 17)

> [!EXAMPLE]- 🏋️ Practica
> Tienes una tabla con una columna por día (`d_1`, `d_2`, …). Pásala a una fila por día y únele el calendario y los precios semanales.

---

## 2️⃣ Calidad · A_02 ✅

> [!QUESTION]- 71 precios vacíos en un producto: ¿se imputan?
> No. Estaban todos en `FOODS_3_288`, en enero y principios de febrero de 2013, y siempre con ventas cero: el producto **aún no estaba a la venta**. Imputar un precio habría inventado una oferta que no existía. Se eliminaron esas 71 filas (truncado por lanzamiento).

- 0 duplicados.
- Fuera 3 columnas constantes (`state_id`, `dept_id`, `cat_id`) y 2 casi vacías (`event_name_2`, `event_type_2`).
- Eventos sin valor → categoría `Sin_evento`. `year`, `month`, `wday` pasan a categóricas.
- Ninguna numérica imputada. Precio intacto en su rango real [1,00 – 4,98].

**En disco:** `train_resultado_calidad.pkl` (21.209 × 12) + vistas `cat_` y `num_` · informe en `06_resultados/Calidad_Datos/`

> [!EXAMPLE]- 🏋️ Practica
> Aísla en qué producto y en qué fechas caen los nulos de una columna, y comprueba qué valor tiene el target en esas filas.

---

## 3️⃣ EDA · A_03 ✅

> [!QUESTION]- ¿Se puede usar una sola estacionalidad para toda la categoría?
> No. Cada producto tiene su propio calendario: unos pican en otoño, otros en primavera, otros en verano y otros en enero. Una estacionalidad común promediaría patrones opuestos y no describiría a ninguno.

**Lo que dice el análisis de negocio:**

| Tema | Hallazgo | Qué implica |
|---|---|---|
| Tiendas | CA_3 vende el 80 %. El mismo producto se comporta distinto en cada tienda | Modelizar por tienda-producto |
| Precio | Muy rígido: 13 de las 20 series tienen 1-2 precios en casi 3 años. `FOODS_3_120` tiene precio único → demanda pura | El precio explica poco en la mayoría |
| Promociones | Habituales en `_090` y `_202`. En `_329`, `_288` y `_587` **solo en la tienda grande** | La promoción no es igual entre tiendas |
| Estacionalidad | Propia de cada producto (otoño, primavera, verano, enero, plana) | `month` es útil, pero por producto |
| Ceros | Dispersos en las series estables (< 1 %); en bloques largos en las intermitentes (`_329`: 271 días en ambas tiendas a la vez) | Hay dos tipos de cero |
| ¿Productos nuevos? | Los arranques tardíos por tienda no son lanzamientos: el producto ya vendía en la otra tienda | Es demanda intermitente |

**Conclusiones:** estructura jerárquica · productos que parecen nuevos por tienda pero no en general · demanda intermitente.

**Acciones:** modelizar a nivel tienda-producto · variable que capture la demanda intermitente · LightGBM.

**En disco:** `03_train_tablon_eda.pkl` (sin transformaciones: igual que al salir de calidad) · informe en `06_resultados/EDA/`

> [!TIP]- ⚙️ Cómo se hizo
> - **Una gráfica por serie:** `pivot_table(index='date', columns='item_id', values='ventas')` + `.plot(subplots=True)`, repetido por tienda. Es lo que deja ver que las series no se parecen.
> - **Rigidez del precio:** `groupby(['item_id','store_id'])['sell_price'].agg(['min','max','nunique'])`. Un `nunique` de 1 o 2 en tres años es un precio que no se mueve.
> - **% de días a cero por serie:** `df['ventas'].eq(0).groupby([df['item_id'], df['store_id']]).mean()`.

> [!EXAMPLE]- 🏋️ Practica
> 1. En una línea, el % de días con ventas cero de cada serie tienda-producto.
> 2. Explica sin código por qué un bloque de 271 días a cero **en las dos tiendas a la vez** no puede ser falta de demanda.

---

## 4️⃣ Transformación · A_04 ✅

> [!QUESTION]- ¿Por qué los lags y las ventanas móviles se construyen con `shift(1)`?
> Para que el modelo **no vea el presente**. Si la ventana del día *t* incluyera la venta del día *t*, el modelo estaría mirando el target mientras predice: fuga de información. Con `shift(1)`, cada fila solo usa datos de días anteriores.

- Como no hay inventario, se crea un **proxy de rotura**: flags `rotura_stock_3/7/15` (racha de ventas a cero en los últimos 3, 7 y 15 días).
- **Lags**: ventas (1→15), precio (1→7) y rotura (1 día).
- **Ventanas móviles**: min, max y media ponderada (2→15), todas con `shift(1)`.
- **One-Hot Encoding** (`drop='first'`, `handle_unknown='ignore'`) del calendario y los eventos.
- Se eliminaron las columnas crudas que quedaban como lag (`sell_price`, `rotura_stock_3/7/15`), `dia_ind` y `wm_yr_wk`.
- **Sin escalado** (el modelo es de árboles).
- `dropna()` de calentamiento: 21.209 → **20.909 filas**.

**En disco:** `03_Entrenamiento/df_tablon_transformado.pkl` (20.909 × 130) · informe en `06_resultados/Transformacion/`

> [!EXAMPLE]- 🏋️ Practica
> Coge una serie y comprueba que la media móvil de 7 días del día *t* no coincide con la venta del día *t* (es decir, que el `shift(1)` está bien puesto).

---

## 5️⃣ Preselección · A_05 ✅

> [!QUESTION]- ¿Se aplica preselección si el modelo es LightGBM (árboles)?
> No haría falta, porque los árboles seleccionan variables solos. Aquí se hace solo como **comparación de métodos** sobre el tablón general, para tener un recorte de partida. La selección buena se hará producto a producto en la fase 07.

- Se comparan **3 métodos**: **Mutual Information** (75 variables), **RFE** (63, la mitad por defecto) y **Permutation Importance** (74).
- Se elige **MI** como recorte general. La decisión real se repite por producto.
- **RFECV descartado**: tarda muchísimo (>10 min) y la validación cruzada aleatoria no es válida en forecasting (mezcla el tiempo y "espía" el futuro).
- El dataset resultante **sí se guarda** (aunque no sea la selección definitiva) porque se reutiliza en la fase siguiente.

**En disco:** `03_Entrenamiento/x_preseleccionado.pkl` (20.909 × 78) + `y_preseleccionado.pkl` (`ventas`) · lista en `01_Documentos/Variables_preseleccionadas.txt` · informe en `06_resultados/Preseleccion/`

> [!NOTE] El dataset preseleccionado es una **prueba a nivel general**: en la fase 07 se repite el mismo trabajo a escala real (20 productos con `for`, cada uno con su propia selección MI + LightGBM con hiperparámetros). Como allí se vuelve a seleccionar, este recorte general no es el resultado final. `07_Modelizacion.ipynb` tampoco guarda dataset.

> [!EXAMPLE]- 🏋️ Practica
> Ordena las variables por Mutual Information y comprueba cuántas coinciden con el top-63 de RFE.

---

## 📌 Para el informe de preproducción (escribirlo al cerrar la fase)

Cosas que tienen que quedar explicadas en ese informe, en cristiano:

| Tema | Qué decir |
|---|---|
| Refactorizar sin pipelines | Todo el proceso se empaqueta en **funciones** que se llaman en orden. Motivo: en forecasting hay pasos que cambian el número de filas (eliminar las filas sin precio, el `dropna` de los lags) y eso no cabe dentro de un pipeline de sklearn |
| Constantes | `VAR_OHE` y `RUTA_OHE`, en mayúsculas y fuera de las funciones: lo que puede cambiar se toca en un solo sitio |
| Dos funciones de transformación | `transformar_variables_entrenamiento` aprende el OHE con todo el histórico y lo guarda con `joblib`; `transformar_variables_ejecucion` lo carga. Así salen siempre las mismas columnas (el ejemplo de Christmas que desaparece si se hace `fit` con pocos días) |
| `aplicar_ohe` | Función auxiliar que usan las dos anteriores para no repetir código (no es recursiva: no se llama a sí misma) |
| Qué proceso llama a qué | Reentrenamiento: calidad → crear variables → transformar **entrenamiento** → modelizar. Ejecución: calidad → crear variables → transformar **ejecución** → predecir |
| Cambios frente al profesor | Sin moda en `sell_price` (se eliminan las filas pre lanzamiento) · solo `month` pasa a texto · OHE en vez de TE, sin `y` en la transformación · `dropna(subset=lags)` · `producto` = tienda_producto como en la modelización |
| Por qué 75 variables en todos los productos | El corte salió del análisis general de la fase 05: en el gráfico de MI la importancia cae casi a 0 después de la posición 67 (detrás de las ventas, el precio y las roturas solo quedan dummies de calendario y eventos), y se cortó en 75 para dejar pasar algunas de esas dummies. Se aplica el mismo corte a los 20 productos como criterio práctico y consistente; cada producto elige SUS 75 con su propio MI, pero el tamaño es el mismo |
| Mapa de procesos | El Excel `FaseProduccion_PlantillaProcesos.xlsx` (actualizado 03/10) dice qué necesita cada variable madre |
| Por qué 75 variables para todos los productos | El 75 salió del corte visual del MI **general** (notebook 05, gráfico de todo el tablón). Se reutiliza como corte fijo dentro de cada producto por simplicidad y control; es un parámetro (`n_variables`) y se puede afinar por serie |
| Las 4 funciones del proceso | 1 `modelizar`: modeliza **un** producto · 2 `lanzar_entrenamiento`: modeliza **todos** los productos y guarda la lista de modelos · 3 `lanzar_ejecucion`: predice todos los productos pero **un solo día** · 4 `forecasting_autorregresivo`: repite la 3 ocho veces para predecir **8 días** (cada predicción pasa a ser historia del día siguiente). Un modelo de ML con lags solo predice el día siguiente; ARIMA proyecta varios días de una vez |
| Quién llama a quién | REENTRENAMIENTO llama a `lanzar_entrenamiento`, que transforma una vez y recorre los 20 productos llamando a `modelizar`, que a su vez llama a `preseleccion_variables`. Funciones dentro de funciones |

---

## ⚠️ Deuda abierta

| # | Asunto | Estado |
|:--:|---|---|
| 1 | **¿20 modelos o uno?** Decidido: **20 modelos** (uno por serie tienda-producto, bottom-up). La selección de variables se repetirá dentro de cada uno | ✅ decidido |
| 2 | Índice `date` es texto → convertir a datetime | 🟠 fase 04 |
| 3 | Elegir la métrica de error (¿por serie o agregada? CA_4 vende 4 veces menos que CA_3) | 🔵 por decidir |
| 4 | Herramienta del tablero final: Power BI, Tableau o Excel | 🔵 por decidir |
| 5 | **`FOODS_3_288` sí es un alta real**: no tenía precio en ninguna de las dos tiendas. La conclusión "no hay productos nuevos" vale para el resto, no para este. Y por eso sus dos series empiezan en febrero (1.032 y 1.025 días), no las 1.064 que dice el informe de EDA | 🟢 anotado · matizar en el informe |
| 6 | **Maquetas de notebooks tipo CRISP-DM.** Montar plantillas de notebook a partir de los notebooks de soporte del curso (Rex los pasará con sus markdowns). Antes, comprobar si de verdad siguen CRISP-DM. Esperar su orden | 🔵 pendiente |
| 7 | **Evaluar de verdad en la modelización.** El notebook compara la predicción contra los mismos datos con los que entrenó (solo comprueba que el proceso funciona). En el modelo final: apartar los últimos días en `x_test` y `y_test` y medir ahí. Patrón: `Patrones/Patron_ML_01_MegaEscalaEstructura` (vault) | 🟠 modelización |
| 8 | **Entrada de la ejecución: exactamente 15 días + 8.** `lanzar_ejecucion` elige el día a predecir como la fecha más baja que sobrevive al `dropna`, así que si se le pasa más historia predice un día viejo. Además `ventasmmp` (ewm) sale un poco distinta con 15 días que con toda la historia (117,7 vs 116,5 en FOODS_3_090). Arreglo posible: elegir el día como la primera fecha sin venta real y pasar más historia | 🔵 por decidir |
| 9 | **Entrada de la ejecución: consulta SQL** (`07_despliegue/consulta_entrada_ejecucion.sql`, explicada en el informe de preproducción). Sin función propia. Eventos vacíos si no hay (no 0), precio planificado o último válido, ventas futuras en 0 | ✅ decidido |
| 10 | **Navidad:** la tienda cierra el 25 de diciembre (venta real 1) y el modelo predijo 481. Solo hay 2 navidades por serie y `min_samples_leaf=20` impide aprenderlo. Arreglo puesto en `forecasting_autorregresivo` (Christmas = 0) y `clip` en `lanzar_ejecucion`; falta reejecutar | 🟢 aplicado |

---

## 🔗 Conexiones

- **Contexto del caso** → `Casos_ML/Caso_02_Forecasting_Retail.md` (vault)
- **Cómo se resuelven los problemas** → `Casos_ML/Forecasting_Soluciones.md` (vault)
- PDF del caso → `01_Documentos/Forecasting Retail.pdf` · estructura de datos → `CasoRetail_EstructuraRelaciones.jpg`
- Agentes → `.github/`

> [!NOTE] Cómo se actualiza
> Al cerrar cada notebook: mover el 📍, añadir su bloque completo, actualizar la tabla de números y los cuatro retos, y subir a deuda abierta lo que quede vivo.
