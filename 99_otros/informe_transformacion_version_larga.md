# Informe de Transformación — Forecasting Retail

> **ESTADO: ✅ COMPLETADO** — fase cerrada (notebook `03_notebooks/04_Transformacion_Datos.ipynb`).
> Este informe empezó como borrador didáctico ("en cristiano") a mitad de la fase; aquí queda completo: rotura de stock, lags, ventanas móviles, eliminaciones, One-Hot Encoding, la decisión de no escalar, unión final y validaciones.
> Al final, la sección **"Para repasar"** recoge las ideas clave y los flecos abiertos.

**Contenido:** 1 Rotura · 2 Lags · 3 Estructura · 4 Exógenas y calendario · 5 Ventanas móviles · 6 Eliminaciones · 7 NaN · 8 One-Hot Encoding · 9 Sin escalado · 10 Unión y validaciones · 11 Mapa de columnas · 12 Riesgos y traspaso · 13 Para repasar

---

## Contexto

| Cosa | Detalle |
|---|---|
| Dataframe de entrada | `02_datos/03_Entrenamiento/03_train_tablon_eda.pkl` (21.209 filas × 12 columnas) |
| Dataframe de salida | `02_datos/03_Entrenamiento/df_tablon_transformado.pkl` (**20.909 filas × 130 columnas**) |
| Fechas | entrada 2013-01-01 → 2015-11-30 · salida 2013-01-16 → 2015-11-30 (por el calentamiento de lags) |
| Target (lo que queremos predecir) | `ventas` |
| Tipo de problema | Regresión sobre series temporales (forecasting) |
| Granularidad | Un producto en una tienda (producto-tienda / PxT), un día |
| Modelo previsto | LightGBM / XGBoost (árboles) → no requiere escalado |

Todo lo de este informe se calcula **serie a serie** (producto-tienda), nunca mezclando unas con otras.

---

## 1. Variable de demanda intermitente: rotura de stock

Se crean **3 columnas**: `rotura_stock_3`, `rotura_stock_7`, `rotura_stock_15`.

**Qué hacen, en cristiano:** miran los últimos 3, 7 o 15 días de ventas de esa serie. Si **todos** esos días se vendió 0, ponen un `1` (sospecha de rotura). Si algún día hubo venta, ponen un `0`.

**Niveles de sospecha:** 3 = posible, 7 = muy posible, 15 = casi seguro.

**Resultado real medido:**

| Columna | Días seguidos a 0 | Unos | % de filas |
|---|---|---|---|
| `rotura_stock_3` | 3 | 2.189 | 10,32 % |
| `rotura_stock_7` | 7 | 1.835 | 8,65 % |
| `rotura_stock_15` | 15 | 1.539 | 7,26 % |

Series con al menos una rotura: **8 de 20**.

**Salvedades (importante):**

- Un 0 en ventas **no siempre** es falta de stock: puede ser que simplemente no hubiera demanda. Es un **indicio (proxy)**, no una certeza.
- Cuenta **filas seguidas**, no días de calendario. Si faltasen fechas en una serie, la ventana se estira en el tiempo real.
- El primer día de cada serie siempre da 0 (no hay histórico suficiente).
- No genera `NaN`.

---

## 2. Variables de lag

**Qué es un lag, en cristiano:** el valor de esa misma variable **X días atrás**.

⚠️ **Un lag no predice nada.** Es una copia de un dato que ya existe, desplazado hacia abajo X filas dentro de su serie. Nada más.

**Para qué sirve:** un modelo no sabe leer una fecha, solo sabe leer *filas de columnas*. El lag es el truco para meter el **pasado dentro de la misma fila** donde está la respuesta que queremos predecir. Así el modelo puede aprender *"cuando pasó esto antes, suele pasar esto otro"*.

### Configuración aplicada

| Variable original | Lags creados | Columnas nuevas | Por qué |
|---|---|---|---|
| `ventas` | 1 → 15 días | `ventas_lag1` … `ventas_lag15` | Se crean todos los lags intermedios para que el modelo use el último dato conocido según el horizonte (con horizonte de 15 días, el válido es `ventas_lag15`) |
| `sell_price` | 1 → 7 días | `sell_price_lag1` … `sell_price_lag7` | El precio se mueve con cadencia semanal: 7 días capturan "la semana pasada", y los intermedios dan el detalle reciente |
| `rotura_stock_3` | 1 día | `rotura_stock_3_lag1` | Ver decisión abajo |
| `rotura_stock_7` | 1 día | `rotura_stock_7_lag1` | Ver decisión abajo |
| `rotura_stock_15` | 1 día | `rotura_stock_15_lag1` | Ver decisión abajo |

**Regla general de los lags:** el lag debe ser **≥ al horizonte de predicción**. Si predices a 15 días, cualquier lag menor de 15 usaría datos que en el momento de predecir todavía no tienes.

### Decisión final: el lag de rotura es de 1 día

El flag de rotura **se queda encendido muchos días seguidos** cuando se activa. Ejemplo:

```
fecha        ventas   rotura_stock_15   rotura_stock_15_lag1
2013-01-15        0                 1                  0.000   <- se enciende
2013-01-16        0                 1                  1.000   <- el lag lo copia al día siguiente
2013-01-17        0                 1                  1.000
...              ...               ...                    ...
2013-02-03        0                 1                  1.000   <- sigue encendido
```

**¿Por qué un lag de 1 día y no uno largo como en ventas?** Porque el flag es **pegajoso**: mientras dura la rotura se mantiene a 1. Eso significa que **el valor de ayer ya cuenta el estado de hoy**, y lo que el modelo necesita es un aviso fresco: *"los ceros recientes que estás viendo no eran falta de demanda, eran falta de producto"*. Con un lag largo, el aviso llegaría cuando la rotura ya se hubiera apagado y no informaría del estado vigente.

**Fleco reconocido (para la preselección):** si el horizonte final de predicción es de 15 días, un lag de 1 día sería un dato que en producción **todavía no existiría** al predecir (fuga temporal). Se conservó a propósito para no perder información en esta fase; en preselección/modelización hay que decidir entre **subirlo al horizonte o eliminarlo**. ⚠️ Queda apuntado en "Para repasar".

---

## 3. Cómo quedará el dataframe para el modelo

**Idea clave:** el dataframe para predecir es una tabla donde **cada fila es un día a predecir**, y en esa misma fila van:

1. **Identificadores** (para saber de qué serie hablamos)
2. **Variables predictoras** (X): todo lo que sabemos *antes* de ese día → calendario, precios, lags, medias móviles...
3. **Target** (y): lo que queremos predecir, `ventas`, de ese día

Ejemplo de la estructura (valores ilustrativos del arranque):

| date (día objetivo) | store_id | item_id | wday | ventas_lag15 | sell_price_lag7 | rotura_stock_15_lag1 | **ventas (target)** |
|---|---|---|---|---|---|---|---|
| 2013-01-17 | CA_3 | FOODS_3_090 | Thursday | 224 | 1,250 | 0 | *(ventas reales del 17-01)* |
| 2013-01-18 | CA_3 | FOODS_3_090 | Friday | 241 | 1,250 | 0 | *(ventas reales del 18-01)* |

Se lee así: *"la fila del 17-01 lleva dentro el dato de ventas del 02-01 (15 días antes) y, al lado, la respuesta real del 17-01"*. El modelo aprende esa relación.

**Por qué tiene sentido:** cuando toca predecir a 15 días vista, lo último que conoces es de hace 15 días. Por eso `ventas_lag15` es exactamente lo que tendrías en la mano.

### 3.1 Target y predictoras: no confundirlos

- **Target (y)** = `ventas`. Es lo único que queremos adivinar.
- **Predictoras (X)** = todo lo demás. Son **pistas**, no objetivos.

"Predecir ventas" **no** significa "usar solo ventas". Significa usar todo lo que ayude a adivinarlas.

| Columna | Papel que juega |
|---|---|
| `ventas_lag15` | **El nivel**: de dónde vengo. Si vendía 224, lo normal es seguir parecido |
| `sell_price_lag7` | **Por qué cambia**: si el precio subió, se vende menos |
| `rotura_stock_*_lag1` | **Avisa de trampas**: esos ceros no eran falta de demanda, eran falta de producto |
| `wday` / eventos | **Estacionalidad**: findes y festivos venden más |

### 3.2 Por qué esta "artificialidad" alimenta al modelo

El modelo **no entiende de tiempo ni de series temporales**: solo entiende de *filas con columnas* y aprende la relación entre ellas. Montar esta tabla es una **artificialidad deliberada** que traduce el pasado a columnas:

- Cada fila se convierte en un caso cerrado: *"con estas pistas, esta fue la respuesta"*.
- Repitiéndolo miles de veces, el modelo aprende la relación **pistas → respuesta**.
- Con **solo** el lag de ventas, el modelo es un loro: repite el pasado y no sabe subir ni bajar la predicción.
- Con precio, rotura y calendario, el modelo puede **ajustar**: *"venía de 224, pero ahora está más caro y venía de una rotura → bajará"*.

**En una frase:** el lag y las demás predictoras son el truco para meter el pasado **en la misma fila** que la respuesta, porque si no, el modelo no tiene dónde mirar.

### 3.3 Regla de coherencia: lead time ↔ horizonte ↔ lag

- Sin lead time (entrega instantánea) → predices a 1 día → basta un **lag 1**.
- Con lead time de 15 días → predices a 15 días → necesitas **lag 15**, porque es el último dato que existe cuando toca decidir.
- Es decir: **el tamaño del lag lo manda el lead time**.

⚠️ **Incoherencia detectada (no resuelta en esta fase):** conviven lags de 15 días (`ventas_lag15`) con el lag de 1 día del rotura. Si el horizonte final fuese de 15 días, ese lag de 1 día no existiría todavía al predecir → **fuga de información**. Decisión tomada: **conservarlo de momento** (ver apartado 2) y resolverlo en la preselección/modelización según el horizonte que se fije.

👉 **Resultado real de la fase:** el tablón quedó en **20.909 filas × 130 columnas** (detalle de bloques en los apartados 10 y 11).


### 3.4 Cómo "lee" el modelo los lags y las ventanas

Para LightGBM el tiempo no existe: no ve una película, ve **fichas sueltas** (filas). Los lags y las ventanas convierten el paso del tiempo en **pistas fijas dentro de la fila**, y el árbol aprende con preguntas del tipo *"si pasa esto y además esto otro, entonces..."*. No memoriza fechas: aprende qué significa **la combinación de pistas**.

| Qué detecta | Cómo lo ve en la fila |
|---|---|
| **Inercia** | `ventas_lag1` frente a `ventasmmp15`: si ayer está por encima del nivel habitual, el producto viene acelerando; si está por debajo, frenando |
| **Picos raros** | Ayer 200 con un nivel habitual de 20: fue un pico puntual, lo normal es volver hacia la media, no repetir 200 |
| **Estabilidad o riesgo** | `ventasmin15` en 25 y `ventasmax15` en 30: demanda plana y predecible. De 0 a 300: producto errático |

**Ejemplo, un martes cualquiera (galletas):**

| Pista | Valor |
|---|---|
| `weekday_Tuesday` | 1 |
| `ventas_lag1` (el lunes) | 150 |
| `ventas_lag7` (el martes pasado) | 25 |
| `ventasmmp15` (nivel habitual) | 28 |

Mirando solo `ventas_lag1`, diría 150. Con las demás pistas aplica lo que aprendió del histórico: *"los lunes hay picos, los martes la demanda vuelve a su patrón (el martes pasado fue 25) y el nivel habitual es 28"*. Predicción: **entre 25 y 30**, no 150.

---

## 4. Por qué se añaden variables externas (exógenas)

Al principio parecía raro: si quiero predecir ventas, ¿por qué meto precio, festivos, rotura...? La respuesta es que **una serie de ventas no se mueve sola**: se mueve por cosas que pasan a su alrededor. Esas cosas son las **variables exógenas** (las de fuera).

Piensa en el ejemplo de la tabla de arriba:

> *"Hoy se vendieron 300, hace 7 días se vendieron 90 y el precio era el doble."*

Aquí pasan dos cosas distintas:

1. **El precio se duplicó** (una subida, o el fin de una promoción).
2. **Las ventas se cayeron** (90).

**Sin `sell_price`**, el modelo solo ve \"las ventas bajaron\" y no tiene ni idea de **por qué**. Y aquí está el problema gordo: si solo trabaja con la venta y sus derivadas (lags, **medias móviles**), la caída de 300 a 90 **se cuela dentro de la propia media móvil**. El bache entra en la predictora como si fuera la tendencia real del producto:

- La media móvil de los últimos días **baja**, porque incluye el 90.
- El modelo mira esa media, ve que viene cayendo y **predice otra caída**, arrastrando el nivel bajo hacia adelante.
- Y como no tiene el precio (la causa real), **no sabe que eso fue un golpe temporal** → seguirá prediciendo bajo aunque el precio ya haya vuelto a la normalidad.

Resultado: **una predicción rara y, encima, \"pegada\" al bache**. El modelo se ha comido el efecto del precio sin poder identificarlo.

**Con `sell_price`**, el modelo ve la causa: *\"el precio se dobló → la gente compró menos\"*. Ahora puede separar dos cosas que antes iban pegadas: **el bache por precio** (temporal) de **la tendencia real del producto**. Y cuando el precio vuelva a su sitio, **sabrá que las ventas deberían recuperarse**, en vez de arrastrar el bache. Eso es lo que separa un modelo con criterio de un loro.

`sell_price` no es "el precio de hoy": es el precio de **hace 7 días**, colocado en la misma fila que la respuesta. Y sirve para dos cosas muy concretas:

- **Capturar promociones**: precios bajos → picos de venta.
- **Capturar subidas**: precios altos → caídas de venta.

### La dimensión temporal: "hace X días"

Todo lo que entra en la fila lleva una **etiqueta temporal**: ventas de hace 15 días, precio de hace 7 días, rotura de ayer. Esa es la dimensión temporal del forecasting: **no se usan valores "de hoy", se usan valores del pasado**, cada uno con su antigüedad. Por eso una fila se lee siempre igual:

> *"Hace 15 días vendió Y, hace 7 días costaba X, ayer estaba en rotura → con lo que sabemos, este día debería vender Z."*

### Qué se espera aprender con ellas

- **Estacionalidad** (calendario): `wday`, `month`, festivos, eventos.
- **Efecto precio**: `sell_price_lag7`.
- **Efecto disponibilidad**: `rotura_stock_*_lag*`.

Las tres cosas juntas son las que convierten el "loro" en un modelo con criterio.

### El calendario y los eventos: las "ficticias" temporales

Caso hermano del precio: **la fecha**. El modelo no sabe leer un `date`, así que se derivan de él columnas "inventadas" (ficticias): `year`, `month`, `wday` (número del día), `weekday` (nombre del día) y los eventos (`event_name_1`, `event_type_1`).

**¿Por qué son imprescindibles?** Porque una serie de ventas no es plana: los viernes y sábados venden distinto que un martes, los festivos disparan las ventas y hay meses con temporada fuerte (p. ej., la temporada de mango en Colombia cae en el primer y cuarto trimestre).

**Ejemplo de qué pasaría sin ellas:** dos días con el mismo lag y el mismo precio (uno sábado, otro miércoles). Sin calendario, el modelo **no tiene forma de distinguirlos** → predeciría lo mismo para ambos. Y si un festivo cae cada año en un día distinto, el lag no lo sabe: **con solo las ventas, el modelo repite el pasado y se pierde picos y valles** (el "loro" de la sección 3.2). Con las dummies de calendario y eventos, el modelo sí puede aprender *"los sábados sube"*, *"en festivo sube"*.

| Bloque | Captura |
|---|---|
| `wday` / `weekday` | Ritmo semanal (fin de semana) |
| `month` / `year` | Estacionalidad y tendencia anual |
| `event_name_1` / `event_type_1` | Festivos y eventos concretos (los días sin evento van como categoría `Sin_evento`) |

### Cómo distingue si un bajón es por el día o por el precio

El modelo no lo "sabe": lo **descubre aislando factores** en miles de filas del histórico. En casi tres años ha visto todas las combinaciones:

| Día | Precio | Ventas |
|---|---|---|
| Martes | normal (1,20) | 20 |
| Sábado | normal (1,20) | 80 |
| Martes | rebajado (1,00) | 35 |
| Sábado | inflado (1,80) | 30 |

Con eso separa los dos efectos:

1. **Efecto del día:** con el precio quieto, el martes siempre vende bastante menos que el sábado. Esa es la base del calendario.
2. **Efecto del precio:** un sábado (día fuerte) que vendió 30 en vez de 80 tenía el precio en 1,80. El día era bueno, así que el bajón es **del precio**. Si el precio no se movió y las ventas cayeron de domingo a lunes, el bajón es **del ciclo semanal**.

En el árbol se ve así (el árbol no calcula porcentajes, corta por umbrales de cada columna):

```text
¿weekday_Tuesday = 1?
 ├── SÍ → ¿sell_price_lag1 > 1,50?
 │         ├── SÍ → ventas esperadas: 8   (doble bajón: día flojo y producto caro)
 │         └── NO → ventas esperadas: 20  (bajón normal por ser martes)
 └── NO → ...
```

### ⚠️ Cuidado con la multicolinealidad

Si metes **muchas versiones de lo mismo**, el modelo se lía:

- Las ventas de hace 1, 2, 3... 15 días están casi perfectamente correlacionadas entre sí.
- Una media móvil de 7 días y otra de 8 días son prácticamente la misma columna.
- El lag de rotura de 1 día es casi igual que el propio flag de rotura (ya detectado arriba).

Cuando dos predictoras dicen casi lo mismo, los coeficientes se vuelven inestables y el modelo pierde interpretabilidad (y puede sobreajustar). Por eso hay que **elegir pocas y buenas**, y eso se decide en la fase de *Preselección de variables*.

### Por qué no basta con la serie de ventas sola

Un método que solo mira el histórico de ventas (una media móvil, un ARIMA básico) asume que el futuro repite los números del pasado. En retail eso falla por cuatro lados:

1. **Ciego ante el precio y las promociones:** si mañana el precio sube un 40 %, predice lo mismo que si nada hubiera cambiado. Y el bache que deja una subida se cuela en la media móvil y se arrastra hacia adelante (el 300 que pasa a 90 de arriba). Con `sell_price`, el modelo lo atribuye al precio y no predice a la baja cuando el precio vuelve a su sitio.
2. **Confunde "nadie lo quiere" con "no había producto":** 10 días a 0 por falta de stock le hacen creer que el producto murió y proyecta ceros. Con `rotura_stock_*_lag1` entiende que fue falta de producto y que, al reponer, la demanda vuelve. Es un parche: si hubiera inventario diario fiable, bastaría con él y esta variable sobraría.
3. **Ciego al calendario:** no sabe qué es Navidad o el Super Bowl. Un día de tienda cerrada (ventas 0) le baja la estimación de los días siguientes sin entender que fue un cierre puntual.
4. **No aprende de otras series:** una serie aislada no aprovecha nada de las demás. Un modelo con las 20 series juntas aprende reglas comunes a productos y tiendas parecidos.

---

## 5. Ventanas móviles: min, max y media ponderada

Además de mirar un solo día atrás (lags), se resumen **bloques de días** recientes de ventas. Para cada tamaño de ventana (de 2 a 15 días) se crean tres columnas:

| Columna | Qué es | Para qué |
|---|---|---|
| `ventasmin{n}` | El **mínimo** de los últimos n días | Ver el suelo: cómo de malo fue el bache más cercano |
| `ventasmax{n}` | El **máximo** de los últimos n días | Ver el techo: picos recientes (promos, festivos) |
| `ventasmmp{n}` | **Media móvil ponderada** (los días recientes pesan más) | El nivel "vivo" de la serie: sigue la tendencia sin saltar con un solo día raro |

En total: 14 tamaños (2 → 15) × 3 estadísticos = **42 columnas**.

### La regla de oro: `shift(1)` o fuga de información

Todas las ventanas se calculan con **`shift(1)` antes del `rolling`/`ewm`**: primero se desplaza la serie un día hacia abajo y **solo entonces** se miran las n filas anteriores. Así, la fila del día D solo ve hasta **D−1**. Si no se hiciera, la ventana incluiría **la venta del propio día que quiero predecir** → el modelo haría trampa (**fuga de información / leakage**: la pista y la respuesta estarían mezcladas).

- **Media ponderada (`ewm`)**: los días recientes pesan más que los antiguos; reacciona antes a los cambios sin saltar con cada día suelto.
- **min / max**: capturan extremos que la media esconde (un día a 0, un pico de promoción).

### ¿Qué es `groupby(...).transform(...)`? La analogía de los 20.000 trabajadores

`df.groupby(['store_id','item_id'])['ventas'].transform(...)` es la pieza menos obvia (y más potente) de todo el notebook. En cristiano:

1. El `groupby` **parte la tabla en series** (una por producto-tienda).
2. `transform` aplica la función **dentro de cada serie**, fila a fila.
3. Y devuelve **el mismo número de filas** que entraron: no colapsa nada, cada fila se queda con su resultado.

La analogía que quedó en el notebook: imagina **20.000 trabajadores en paralelo** (uno por fila). Cada trabajador mira **hacia atrás y solo dentro de SU serie** (las n filas anteriores de su producto-tienda), calcula su número (media, mínimo, máximo) y lo escribe en su fila. Nunca mezcla tiendas ni productos distintos, y al terminar todos siguen en su sitio con su dato.

> Si se usara `agg` en vez de `transform`, cada serie se colapsaría en 1 fila (y se perdería el tablón). Si se usara `shift`/`rolling` sin `groupby`, el arranque de cada serie arrastraría datos de la serie anterior.

**Esto en SQL es una función ventana:**

```sql
... OVER (PARTITION BY store_id, item_id ORDER BY date
          ROWS BETWEEN n PRECEDING AND 1 PRECEDING)
```

- `PARTITION BY` = el groupby (partir en series).
- `ORDER BY date` = el orden temporal.
- `ROWS BETWEEN n PRECEDING AND 1 PRECEDING` = la ventana: las n filas anteriores al día actual, **sin incluir el actual** (el `shift(1)`).

---

## 6. Eliminación de variables que no van al modelo

Antes de montar el tablón final se descartaron 6 columnas, cada una por un motivo:

| Columna | Motivo |
|---|---|
| `sell_price` (precio del día objetivo) | **No existiría en el momento de predecir**: es el precio del mismo día que quiero adivinar. Su señal ya va dentro de `sell_price_lag1..7` |
| `rotura_stock_3` / `rotura_stock_7` / `rotura_stock_15` | **Redundantes con su versión lag1**: los flags crudos solo se conservan como `..._lag1`, que es lo que se conocería al predecir |
| `dia_ind` | **Redundante con la fecha**: índice del día construido en el EDA; su información ya está en `date`, `year`, `month`, `wday`... |
| `wm_yr_wk` | **Redundante con la fecha** (semana del año); además es un entero continuo que confunde más que informa |

**La regla de oro detrás de todo esto (forecasting):** solo entran columnas que **se conocerían de verdad** en el momento de predecir. Todo lo que sea "del futuro" o una copia de algo que ya está, fuera.

---

## 7. Qué pasó con los NaN (los de calentamiento)

- **Al principio de cada serie:** los lags y las ventanas dejan `NaN` en las primeras filas (no hay pasado que mirar). Con ~20 series, afecta a las **primeras 15 filas de cada una**.
- **Solución aplicada:** `dropna()` → de **21.209 filas se pasó a 20.909** (−300 filas, **−1,4 %**). No es pérdida real: son justo las filas donde faltarían las pistas, y un modelo no puede aprender de una fila sin pasado.
- **Al final no se pierde nada:** el target de cada fila es la venta de ese mismo día, ya observada. Lo de apartar los últimos días como "días a predecir" es cosa de la fase de modelización (split temporal), no de esta transformación.
- **Rango final de fechas:** 2013-01-16 → 2015-11-30.

---

## 8. Codificación de categóricas: One-Hot Encoding

Las categóricas de texto (`year`, `month`, `wday`, `weekday`, `event_name_1`, `event_type_1`) hay que convertirlas a números. La técnica elegida fue **One-Hot Encoding (OHE)**: por cada categoría, una columna 0/1 ("pertenece / no pertenece").

### ¿Por qué OHE y no una simple numeración (Ordinal Encoding)?

- Todas nacieron como **nominales**: sin orden real entre sus valores. Para el modelo, `Friday` no es "más" que `Monday`; numerarlas inventaría un orden falso (un 6 > 1 que no existe en los datos).
- Con árboles (LightGBM/XGBoost), las dummies dejan que **cada categoría se trate por separado**, sin imponer monotonías.
- Se comprobó en el EDA que no había relación monótona con la target → OHE de cabeza.
- **Excepción apuntada (no aplicada):** `month` sí tiene estacionalidad real (temporada de mango en Q1/Q4). Un Ordinal Encoding (1→12) le dejaría "ver" la continuidad entre meses vecinos; con OHE esa pista se pierde. Queda como observación para la preselección.

### Las dos decisiones finas del encoder

1. **`drop='first'` — la trampa de las dummies.** Si una variable tiene k categorías y se crean k dummies, la última es **combinación perfecta de las demás** (100 % predecible desde las otras) → información duplicada y **multicolinealidad perfecta**. La regla es **k−1 dummies**: la categoría que se elimina queda como "categoría base" (aquí, p. ej., enero es la base de `month`, viernes la de `weekday` y 2013 la de `year`).
2. **`handle_unknown='ignore'` — pensando en producción.** En el futuro llegarán categorías que el encoder no vio al entrenar (un evento nuevo...). Con esta opción, el encoder **no revienta**: pone **todas las dummies de esa variable a 0**, que es exactamente "lo trato como la categoría base". Con el comportamiento por defecto (`error`), el pipeline se caería en producción.

### Resultado

6 variables categóricas → **59 columnas binarias**: `year` 2 · `month` 11 · `wday` 6 · `weekday` 6 · `event_name_1` 30 · `event_type_1` 4.

⚠️ **Para repasar:** `event_name_1` es la de mayor cardinalidad (30 dummies, muchas de eventos raros). Ahí la preselección tiene trabajo: dummies casi constantes o de poca importancia.

---

## 9. Sin escalado ni normalización: ¿por qué no hizo falta?

Decisión registrada en el notebook: **no se reescala ni se normaliza nada**. Motivo: el modelo previsto es **LightGBM/XGBoost** y los árboles **parten por umbrales** ("¿ventas_lag15 > 210?"). Para un árbol, lo que importa es el **orden** de los valores, no su magnitud: da igual que una columna esté en miles y otra en 0/1.

- **Lo que sí importa en árboles:** que las columnas estén bien construidas (lags sin fuga, codificaciones correctas). La escala, no.
- **Nota por si cambia el modelo:** si algún día se prueba un modelo lineal o una red neuronal (sí sensibles a escala y distribución), habría que volver aquí y aplicar `StandardScaler`/`RobustScaler` a las numéricas. Hoy no aplica.
- Las dummies 0/1 y los flags de rotura no se escalan jamás (ya son binarios).

---

## 10. Unión final y validaciones

### Cómo se montó el tablón

1. `cat` y `num` salen del mismo dataframe (`dfo`) y en el mismo orden → el resultado del OHE se alinea con el índice de `cat`.
2. Se junta todo con `pd.concat(..., axis=1)`:
   - **Claves**: `store_id`, `item_id`.
   - **Numéricas**: 42 ventanas móviles + 25 lags.
   - **OHE**: 59 dummies de calendario y eventos.
   - **Target**: `ventas`.
3. `date` deja de ser índice y pasa a **columna** (`reset_index`) → viaja en el tablón para trazabilidad y futuros cortes train/test por tiempo (no la usan los árboles directamente).
4. `assert` de cierre: mismo número de filas que la tabla de numéricas y **cero nulos**. Si algo se descuadra, el assert lo para en seco.

### Validaciones realizadas (comprobadas)

- ✅ Los lags se calculan dentro de cada serie → no se mezclan productos ni tiendas.
- ✅ `df` y `df_lags` comprobados con **el mismo número y el mismo orden de filas** (`df.index.equals(...)`) → `pd.concat([df, df_lags], axis=1)` es seguro. **No** usar `.join()` ni `merge` por índice: `date` se repite entre series.
- ✅ Tras `dropna()`: **20.909 filas** (300 menos, solo el calentamiento).
- ✅ Tablón final: **20.909 filas × 130 columnas**, **sin nulos** y con la target presente.
- ✅ Nº de unos reales de cada flag de rotura comprobado (tabla del apartado 1).

---

## 11. Mapa final de columnas (versiones intermedias y finales)

Siguiendo la regla "solo versiones finales al tablón":

| Bloque original | Original fuera | Intermedias fuera | Finales en el tablón | Justificación |
|---|---|---|---|---|
| `sell_price` | `sell_price` (día objetivo) | — | `sell_price_lag1..7` | El precio "de hoy" no existiría al predecir; la señal vive en los lags |
| `rotura_stock_3/7/15` | las 3 columnas crudas | — | `rotura_stock_{3,7,15}_lag1` | Flag pegajoso; solo su versión "de ayer" se conoce al predecir |
| `ventas` | — | — | `ventas` (target) + `ventas_lag1..15` + 42 ventanas móviles | La venta es la respuesta; sus versiones pasadas son pistas |
| Fecha | `dia_ind`, `wm_yr_wk` | — | `date` (trazabilidad) + dummies de calendario | Redundantes con `date`; el modelo no lee fechas ni textos |
| Eventos | — | `event_name_1`, `event_type_1` (texto) | 34 dummies de evento | Ídem: hay que convertirlos a números |

**Composición final (20.909 × 130):**

| Bloque | Columnas |
|---|---|
| `date` + claves (`store_id`, `item_id`) | 3 |
| Ventanas móviles (42) + lags (25) | 67 |
| Dummies OHE (calendario + eventos) | 59 |
| Target `ventas` | 1 |
| **Total** | **130** ✅ |

> Las funciones de esta fase (`crear_lags`, `rotura_stock`, `estadistico_movil_serie`, `media_movil_ponderada_serie`) viven también en `04_scripts/utils.py`, pensadas para reutilizarlas en las fases de preproducción.

---

## 12. Riesgos y traspaso a la preselección de variables

**Riesgos heredados de esta fase:**

- **Multicolinealidad alta:** conviven versiones casi idénticas (15 lags consecutivos, ventanas de 7 vs 8 días, lag de rotura ≈ flag). Los árboles lo toleran mejor que un modelo lineal, pero la importancia se reparte entre clones que se estorban.
- **Dimensionalidad del OHE:** 59 dummies; las de eventos raros aportan poco.
- **Fleco del lag de rotura:** coherencia con el horizonte final (apartado 2).
- **`month` con OHE pierde continuidad estacional:** revisar si un encoding ordinal/numérico aporta más.

**Recomendaciones (conceptuales) para la preselección:**

- Usar la importancia de un modelo rápido de árboles para agrupar clones (lags vs ventanas) y quedarse con "pocas y buenas".
- Podar el bloque de ventanas móviles por tamaños representativos antes que por estadísticos duplicados.
- Mantener un **split temporal** (no aleatorio) en el entrenamiento: es forecasting; cualquier fuga temporal se paga en producción.

---

## 13. Para repasar

1. **`shift(1)` antes de `rolling`: sin él, habría fuga.** Las ventanas terminan "1 PRECEDING", nunca en la fila actual.
2. **`groupby(...).transform(...)`** calcula por serie **sin colapsar filas**; en SQL, `OVER (PARTITION BY ...)`. La analogía de los 20.000 trabajadores.
3. **Un lag no predice: traslada el pasado a la fila.** Regla del tamaño: lag ≥ horizonte. El caso del lag de rotura (1 día) quedó en revisión para la preselección.
4. **OHE con `drop='first'`** (trampa de las dummies: k−1) y **`handle_unknown='ignore'`** (categoría nueva → todo 0 = cae en la categoría base; producción no se cae).
5. **Sin escalado por LightGBM:** los árboles comparan umbrales, no magnitudes. Si algún día cambia el tipo de modelo, revisar.
6. **Solo entra lo que se conocería al predecir:** por eso salieron `sell_price`, `dia_ind` y `wm_yr_wk` (el precio vive en sus lags).
7. **El calendario "ficticio" (dummies de fecha/eventos) es lo que captura estacionalidad y festivos;** con solo ventas, el modelo "repite el pasado".
8. **`date` sigue en `str`** y solo viaja por trazabilidad; si se necesita para cortes temporales, convertir a `datetime` en la fase que toque.
