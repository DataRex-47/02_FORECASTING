# Informe de Transformación · Forecasting Retail

> **ESTADO: ✅ COMPLETADO.** Notebook `03_notebooks/04_Transformacion_Datos.ipynb`.

## Contexto

| Cosa | Detalle |
|---|---|
| Entrada | `02_datos/03_Entrenamiento/03_train_tablon_eda.pkl` (21.209 filas × 12 columnas) |
| Salida | `02_datos/03_Entrenamiento/df_tablon_transformado.pkl` (**20.909 filas × 130 columnas**) |
| Fechas | entrada 2013-01-01 a 2015-11-30 · salida 2013-01-16 a 2015-11-30 |
| Target | `ventas` |
| Granularidad | un producto en una tienda (PxT), un día · 20 series |
| Modelo previsto | LightGBM o XGBoost (árboles), por eso no se escala |

Todo se calcula **serie a serie**: primero se ordena por `store_id`, `item_id`, `date` y después se agrupa por producto y tienda. Nunca se mezclan series.

## 1. Rotura de stock (demanda intermitente)

Se crean `rotura_stock_3`, `rotura_stock_7` y `rotura_stock_15`. Miran los últimos 3, 7 o 15 días de ventas de la serie: si **todos** fueron 0, ponen `1` (sospecha de rotura); si hubo alguna venta, `0`. Tres niveles de sospecha: posible (3), muy posible (7), casi seguro (15).

| Columna | Unos | % de filas |
|---|---|---|
| `rotura_stock_3` | 2.189 | 10,32 % |
| `rotura_stock_7` | 1.835 | 8,65 % |
| `rotura_stock_15` | 1.539 | 7,26 % |

Series con al menos una rotura: **8 de 20**.

**Salvedades:**

1. Es un **indicio (proxy)**, no una certeza: un 0 puede ser falta de demanda. Es un parche porque no hay datos de inventario; si hubiera inventario diario fiable, bastaría con él y esta variable sobraría.
2. Cuenta **filas seguidas**, no días de calendario.
3. El primer día de cada serie da 0 y no genera `NaN`.

## 2. Lags

Un lag es **el valor de esa variable X días atrás**, dentro de su serie. No predice nada: es el truco para meter el pasado **en la misma fila** que la respuesta, porque el modelo solo lee filas.

| Variable | Lags | Columnas |
|---|---|---|
| `ventas` | 1 a 15 | `ventas_lag1` … `ventas_lag15` |
| `sell_price` | 1 a 7 | `sell_price_lag1` … `sell_price_lag7` |
| `rotura_stock_3`, `_7`, `_15` | 1 | `rotura_stock_{3,7,15}_lag1` |

Se configuran en `CONFIG_LAGS` y los crea `crear_lags`, que devuelve un df aparte (`df_lags`).

**Por qué la rotura lleva solo lag 1:** el flag es pegajoso (se queda en 1 mientras dura la rotura), así que el valor de ayer ya cuenta el estado de hoy. Es el aviso fresco de *"estos ceros no eran falta de demanda, eran falta de producto"*.

### Lead time, horizonte y tamaño del lag

Tres conceptos encadenados, y el primero manda sobre los otros dos:

| Concepto | Qué es |
|---|---|
| **Lead time** | lo que tarda el proveedor en entregar desde que haces el pedido |
| **Horizonte** | cuántos días hacia adelante tienes que predecir |
| **Tamaño del lag** | cuántos días atrás está el dato que metes en la fila |

**La cadena:** si el proveedor tarda 15 días, hoy tienes que pedir lo que vas a vender dentro de 15 días. Eso obliga a predecir a 15 días (horizonte). Y cuando predices el día 16 estando en el día 1, la venta más reciente que conoces es la del día 1, o sea, la de **15 días antes** del día que predices. Por eso el lag mínimo es 15.

**Regla:** el lag tiene que ser **igual o mayor que el horizonte**. Sin lead time (entrega al día siguiente) basta con lag 1; con lead time de 15 días, lag 15.

**Qué pasa si no se cumple:** un `ventas_lag3` para el día 16 sería la venta del día 13, que el día 1 todavía no ha ocurrido. En el entrenamiento ese dato sí existe (el histórico está completo) y el modelo aprende a apoyarse en él porque es la pista más fresca. En producción esa columna no se puede llenar con nada real. Es la **fuga temporal**: el modelo sale muy bien en las pruebas y falla en la vida real.

**Las dos formas de predecir varios días:**

1. **Directa:** un modelo que solo usa lags iguales o mayores que el horizonte. Es simple y no acumula errores, pero pierde las pistas más frescas.
2. **Recursiva:** se predice día a día. La predicción de mañana se usa como `ventas_lag1` para predecir pasado mañana, y así hasta cubrir el horizonte. Permite usar lags cortos (el lag 1 de rotura incluido), a cambio de que el error de cada día se arrastra al siguiente.

**En este caso:** se crearon los lags del 1 al 15 para que existan las columnas que haga falta según la estrategia que se elija. Si se predice de forma directa a varios días, el `rotura_stock_*_lag1` y los lags cortos serían fuga; si se predice de forma recursiva, no. Se decide en la modelización.

## 3. Ventanas móviles

Para cada tamaño de 2 a 15 días se crean tres columnas sobre `ventas`: **14 tamaños × 3 = 42 columnas**.

| Columna | Qué es | Para qué |
|---|---|---|
| `ventasmin{n}` | mínimo de los últimos n días | el suelo: el bache más cercano |
| `ventasmax{n}` | máximo de los últimos n días | el techo: picos por promo o festivo |
| `ventasmmp{n}` | media móvil ponderada (`ewm`), los días recientes pesan más | el nivel vivo de la serie |

**Regla de oro, `shift(1)` antes del `rolling` o `ewm`:** la fila del día D solo ve hasta D menos 1. Sin él, la ventana incluiría la venta que se quiere predecir (fuga de información).

**`groupby` + `transform`:** el `groupby` parte la tabla en las 20 series y `transform` devuelve **un dato por cada una de las ~20 mil filas**, sin colapsar nada. Como 20 mil trabajadores en paralelo, cada uno mirando hacia arriba solo las n filas anteriores **de su serie** y escribiendo su dato. En SQL:

```sql
... OVER (PARTITION BY store_id, item_id ORDER BY date
          ROWS BETWEEN n PRECEDING AND 1 PRECEDING)
```

## 4. Cómo usa el modelo estas pistas

### 4.1 Cada fila es una ficha

Cada fila es **un día a predecir** y lleva dentro: identificadores (`store_id`, `item_id`), predictoras (lo que se sabe **antes** de ese día: lags, ventanas, precio pasado, rotura, calendario) y la target (`ventas` de ese día). Repitiendo miles de fichas *"con estas pistas, esta fue la respuesta"*, el modelo aprende la relación.

| Predictora | Papel |
|---|---|
| lags y ventanas de `ventas` | el nivel: de dónde viene la serie |
| `sell_price_lag*` | por qué cambia: si sube el precio, baja la venta |
| `rotura_stock_*_lag1` | avisa de trampas: ceros por falta de producto |
| calendario y eventos | estacionalidad: fines de semana y festivos |

### 4.2 Cómo "lee" los lags y las ventanas

Para LightGBM el tiempo no existe: no ve una película, ve **fichas sueltas**. El árbol aprende con preguntas del tipo *"si pasa esto y además esto otro, entonces..."*. No memoriza fechas: aprende qué significa **la combinación de pistas**.

| Qué detecta | Cómo lo ve en la fila |
|---|---|
| **Inercia** | `ventas_lag1` frente a `ventasmmp15`: por encima del nivel habitual, viene acelerando; por debajo, frenando |
| **Picos raros** | ayer 200 con un nivel habitual de 20: fue puntual, lo normal es volver hacia la media |
| **Estabilidad o riesgo** | `ventasmin15` en 25 y `ventasmax15` en 30: demanda plana. De 0 a 300: producto errático |

**Ejemplo, un martes (galletas):** `weekday_Tuesday` = 1, `ventas_lag1` (el lunes) = 150, `ventas_lag7` (el martes pasado) = 25, `ventasmmp15` = 28. Mirando solo el lag 1 diría 150. Con las demás pistas aplica lo aprendido: *"los lunes hay picos, los martes la demanda vuelve a su patrón y el nivel habitual es 28"*. Predicción: **entre 25 y 30**.

### 4.3 Cómo distingue si un bajón es por el día o por el precio

Lo **descubre aislando factores** en casi tres años de histórico, donde ha visto todas las combinaciones:

| Día | Precio | Ventas |
|---|---|---|
| Martes | normal (1,20) | 20 |
| Sábado | normal (1,20) | 80 |
| Martes | rebajado (1,00) | 35 |
| Sábado | inflado (1,80) | 30 |

1. **Efecto del día:** con el precio quieto, el martes siempre vende bastante menos que el sábado.
2. **Efecto del precio:** un sábado (día fuerte) que vendió 30 en vez de 80 tenía el precio en 1,80. El día era bueno, así que el bajón es **del precio**.

En el árbol (no calcula porcentajes, corta por umbrales de cada columna):

```text
¿weekday_Tuesday = 1?
 ├── SÍ → ¿sell_price_lag1 > 1,50?
 │         ├── SÍ → ventas esperadas: 8   (doble bajón: día flojo y producto caro)
 │         └── NO → ventas esperadas: 20  (bajón normal por ser martes)
 └── NO → ...
```

### 4.4 Por qué no basta con la serie de ventas sola

Un método que solo mira el histórico de ventas asume que el futuro repite el pasado. En retail falla por cuatro lados:

1. **Ciego ante el precio:** si el precio se dobla y las ventas caen de 300 a 90, ese bache se cuela en la media móvil y se arrastra hacia adelante, aunque el precio ya haya vuelto a la normalidad. Con `sell_price_lag*`, el modelo lo atribuye al precio y no predice a la baja cuando el precio se normaliza.
2. **Confunde "nadie lo quiere" con "no había producto":** 10 días a 0 por falta de stock le hacen proyectar ceros. Con la rotura entiende que, al reponer, la demanda vuelve.
3. **Ciego al calendario:** dos días con el mismo lag y el mismo precio (un sábado y un miércoles) serían iguales para él. Por eso se derivan de la fecha `year`, `month`, `wday`, `weekday` y los eventos (`event_name_1`, `event_type_1`; sin evento va como `Sin_evento`).
4. **No aprende de otras series:** con las 20 series juntas, el modelo aprende reglas comunes a productos y tiendas parecidos.

## 5. Variables eliminadas

| Columna | Motivo |
|---|---|
| `sell_price` | es el precio del día objetivo: no existiría al predecir. Su señal va en `sell_price_lag1` a `lag7` |
| `rotura_stock_3`, `_7`, `_15` | se conservan solo en su versión `_lag1` |
| `dia_ind` | redundante con la fecha |
| `wm_yr_wk` | redundante con la fecha (semana del año) |

Regla: solo entra lo que **se conocería de verdad** al predecir.

## 6. Nulos

Los lags y las ventanas dejan `NaN` en las primeras 15 filas de cada serie (no hay pasado que mirar). Con `dropna()` se pasó de **21.209 a 20.909 filas** (300 = 15 × 20 series, un 1,4 %). No es pérdida real: son filas sin pistas.

## 7. One Hot Encoding

Variables: `year`, `month`, `wday`, `weekday`, `event_name_1`, `event_type_1`. Todas nominales, sin relación monótona con la target (EDA), así que OHE en lugar de numerarlas (numerar inventaría un orden falso).

1. **`drop='first'`:** con k categorías se crean k menos 1 dummies; la que falta queda como base. Evita duplicar información (trampa de las dummies).
2. **`handle_unknown='ignore'`:** una categoría nueva en producción pone todas las dummies a 0 (se trata como la base) y el pipeline no se cae.

Resultado: **59 dummies** (`year` 2 · `month` 11 · `wday` 6 · `weekday` 6 · `event_name_1` 30 · `event_type_1` 4).

## 8. Sin escalado

Los árboles cortan por umbrales (*"¿ventas_lag15 > 210?"*): importa el orden de los valores, no su magnitud. Si algún día se prueba un modelo lineal o una red neuronal, habría que escalar las numéricas.

## 9. Unión final

1. `df` y `df_lags` comprobados con el mismo número de filas y el mismo índice (`df.index.equals(df_lags.index)` → True), luego `pd.concat(axis=1)`. No usar `join` ni `merge` por índice: `date` se repite entre series.
2. Tras eliminar variables y aplicar el OHE, se une: claves + numéricas (42 ventanas + 25 lags) + 59 dummies + target.
3. `date` pasa de índice a columna (trazabilidad y futuro corte por tiempo).
4. `assert` de cierre: mismas filas que las numéricas y **cero nulos**.

| Bloque | Columnas |
|---|---|
| `date`, `store_id`, `item_id` | 3 |
| ventanas móviles (42) y lags (25) | 67 |
| dummies OHE | 59 |
| target `ventas` | 1 |
| **Total** | **130** ✅ |

## 10. Riesgos y traspaso a la preselección

1. **Multicolinealidad alta:** 15 lags consecutivos y ventanas de tamaños vecinos dicen casi lo mismo. Los árboles lo toleran, pero la importancia se reparte entre clones.
2. **Dimensionalidad del OHE:** `event_name_1` aporta 30 dummies, muchas de eventos raros.
3. **Fleco del lag de rotura:** coherencia con el horizonte final (apartado 2).
4. **`month` con OHE pierde la continuidad estacional:** valorar un encoding numérico.
5. Mantener un **corte temporal** (no aleatorio) al entrenar.

## 11. Para repasar

1. `shift(1)` antes de `rolling`: sin él hay fuga.
2. `groupby` + `transform`: un dato por fila, calculado solo con su serie. En SQL, `OVER (PARTITION BY ...)`.
3. Un lag no predice: traslada el pasado a la fila.
4. El modelo no ve tiempo, ve fichas; aprende de la combinación de pistas.
5. OHE con `drop='first'` y `handle_unknown='ignore'`.
6. Solo entra lo que se conocería al predecir.
