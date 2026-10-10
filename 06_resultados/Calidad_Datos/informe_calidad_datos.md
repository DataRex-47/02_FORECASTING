# Informe de Calidad de Datos · Forecasting Retail

> **ESTADO: ✅ CERRADA.** Notebook `03_notebooks/02_Calidad_Datos.ipynb`. Versión larga (con anexos y salidas literales) en `99_otros/informe_calidad_datos_version_larga.md`.

## Contexto

| Cosa | Detalle |
|---|---|
| Entrada | `02_datos/03_Entrenamiento/train.pkl` (21.280 filas × 17 columnas) |
| Salida | `train_resultado_calidad.pkl` (**21.209 filas × 12 columnas**), más las vistas `num_` y `cat_` |
| Fechas | 2013-01-01 a 2015-11-30 (1.064 días), en el índice `date` |
| Alcance | 1 categoría (`FOODS_3`), 2 tiendas (`CA_3`, `CA_4`), 10 productos: **20 series** |
| Grano | un producto en una tienda, un día (1.064 × 20 = 21.280) |

## 1. Qué pasó en el notebook, paso a paso

| # | Paso | Resultado |
|---|---|---|
| 1 | `df.info()` | 21.280 × 17. La única con nulos es `sell_price` (71) |
| 2 | Tipos de calendario | `year`, `month`, `wday` pasan a texto: son calendario, no cantidades |
| 3 | Valores únicos | `state_id`, `dept_id`, `cat_id` tienen un solo valor: se eliminan |
| 4 | Duplicados | 0 |
| 5 | Separar numéricas y categóricas | `con`: `wm_yr_wk`, `ventas`, `sell_price`. `cat`: el resto |
| 6 | Eventos | `event_name_1` y `event_type_1` con 19.580 nulos: se llenan con `Sin_evento`. `event_name_2` y `event_type_2` vacías al 99,7 %: se eliminan |
| 7 | Estadísticos | `sell_price` de 1,00 a 4,98. `ventas` con mediana 18 y máximo 763 |
| 8 | Nulos de `sell_price` | los 71 son de `FOODS_3_288`, enero y comienzos de febrero de 2013, todos con venta 0 |
| 9 | Atípicos (4 desviaciones típicas) | `sell_price` ninguno. `ventas` sí, pero no se recortan |
| 10 | Unir y borrar | `concat` y `dropna(subset=['sell_price'])`: quedan 21.209 filas |
| 11 | Separar y guardar | 3 `.pkl` con las mismas filas y el mismo índice `date` |

## 2. Decisión principal: borrar las 71 filas, no imputar

**Diagnóstico.** Los 71 nulos son de un solo producto (`FOODS_3_288`), en las dos tiendas, en un tramo seguido al inicio de la serie, y siempre con venta 0. La prueba de control (abril de 2014) muestra el mismo producto con precio y ventas normales. Conclusión: son los días **antes del lanzamiento**; el producto todavía no estaba en la góndola.

**Por qué no se imputó el precio:**

1. Esas semanas están vacías del todo, así que la moda semanal no tiene de dónde sacar un valor.
2. Usar la moda histórica traería precios de 2014 y 2015 a enero de 2013: información del futuro en el pasado.
3. Un precio inventado le diría al modelo que el producto estuvo 45 días en la góndola sin venderse, y eso falsea la relación entre precio y venta.

**Efecto:** `FOODS_3_288` empieza en su lanzamiento (2.057 filas en vez de 2.128). Las otras 19 series quedan completas. No hay ningún valor imputado en las numéricas.

## 3. Eventos y constantes

| Columna | Tratamiento | Por qué |
|---|---|---|
| `event_name_1`, `event_type_1` | nulo pasa a `Sin_evento` | el nulo significa "ese día no hubo evento": es una categoría, no un dato perdido |
| `event_name_2`, `event_type_2` | eliminadas | solo 60 filas con valor de 21.280 |
| `state_id`, `dept_id`, `cat_id` | eliminadas | un solo valor, no aportan nada al modelo |

Quedan 30 eventos y 4 tipos (National, Religious, Cultural, Sporting). Si el caso se escalara a varios estados o categorías, las tres constantes dejarían de serlo y pasarían a ser claves para partir los modelos.

## 4. Atípicos de ventas

El máximo es **763 unidades con una mediana de 18**. No se recortó en esta fase. Quedaron tres hipótesis para el EDA: compra mayorista puntual, rebote después de una rotura de stock, o una promoción o evento local que no está en el calendario.

## 5. Incidente del índice (corregido el 25/09/2026)

La primera versión hacía `dropna(...).reset_index(drop=True)`, que cambiaba el índice `date` por un 0, 1, 2… y el tablón perdía sus fechas. Se quitó el `reset_index` y los tres artefactos se regeneraron con `date`.

Ojo: `date` **no es único** (cada fecha se repite en las 20 series). Antes de cualquier `shift` o ventana hay que ordenar por `store_id`, `item_id`, `date`. Si se necesita una clave única, es `date` + `store_id` + `item_id`.

## 6. Salidas

Todas en `02_datos/03_Entrenamiento/`, con el índice `date`:

| Artefacto | Contenido | Dimensiones |
|---|---|---|
| `train_resultado_calidad.pkl` | tablón completo | 21.209 × 12 |
| `num_resultado_calidad.pkl` | `wm_yr_wk`, `ventas`, `sell_price` | 21.209 × 3 |
| `cat_resultado_calidad.pkl` | las 9 categóricas | 21.209 × 9 |

Comprobación: 9 productos × 2.128 + 2.057 = 21.209 filas, cero nulos.

## 7. Traspaso a las siguientes fases

1. Los primeros lags de `FOODS_3_288` saldrán vacíos de forma legítima: no hay historia antes del lanzamiento. No se rellenan con ceros.
2. Un 0 en ventas puede ser falta de demanda o falta de producto. Esa diferencia la recoge después la variable de rotura de stock (Transformación).
3. El 763 queda marcado para el EDA.
