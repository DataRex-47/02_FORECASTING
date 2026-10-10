# Informe de EDA — Proyecto 5: Forecasting Retail

**Fase**: 03 – Análisis Exploratorio · **Fecha**: 2026-09-27
**Dataframe analizado**: `02_datos/03_Entrenamiento/train_resultado_calidad.pkl` (`df`) — 21.209 filas × 12 columnas
**Alcance**: 10 productos FOODS × 2 tiendas (CA_3, CA_4) = **20 series diarias** · 1.064 días (2013-01-01 → 2015-11-30)
**Notebook fuente**: `03_notebooks/03_EDA.ipynb`
**Transformaciones aplicadas al dataframe durante el EDA**: ninguna (el dataframe queda igual que al final de la fase de Calidad de Datos).

---

## 1. Qué hemos visto (resumen del análisis)

### 1.1 Calidad y estructura

- **No hay huecos de calendario**: las 20 series tienen sus 1.064 fechas completas. Los "cortes" que se ven en las gráficas son días con `ventas = 0`, no fechas ausentes.
- ⚠️ El índice `date` es de tipo **string** (viene así desde la fase de Calidad de Datos). Se convertirá a `datetime` en la fase de Transformación.
- `sell_price`: sin ceros y sin nulos en las 20 series.

### 1.2 Precio

- Precios **rígidos**: 13 de las 20 series (item-tienda) tienen 1-2 precios distintos en casi 3 años; los cambios son escalones permanentes (ej. 2014: `_252` 1.48→1.58, `_555`/`_586` 1.58→1.68, `_714` 1.48→1.58; `_587` baja a 2.48).
- **`FOODS_3_120`**: precio único constante (4.98) en ambas tiendas → su serie refleja demanda "pura", sin efecto precio.
- **Promoción habitual**: `_090` y `_202` (6-8 valores, dips a 1.00 y 3.00) → el precio explica parte del volumen.
- **Promos exclusivas de la tienda grande**: `_329`, `_288` y `_587` solo se promocionan en CA_3 → el precio no es igual entre tiendas.

### 1.3 Tiendas

- CA_3 = **80% de las ventas** (491.804 uds) · CA_4 = 20% (122.647 uds); el peso de CA_4 varía entre el 10,8% y el 28,9% según producto.
- El **mismo producto se comporta distinto en cada tienda**: `_329` vende 19,8 uds/día en CA_3 vs 4,4 en CA_4, con bloques de ceros y promociones distintas.
- → Justifica modelizar **a nivel tienda-producto** (agregar por producto escondería roturas y patrones distintos).

### 1.4 Estacionalidad

- **Cada producto tiene su propio calendario**: otoño (`_090`, `_120`), primavera (`_202`), verano (`_252`, `_586`, `_714`), enero (`_288`, `_329`, `_587`), plana (`_555`).
- No hay un patrón estacional común → `month` (o estacionalidad por producto) será una variable útil.
- ⚠️ El perfil de `_329` está distorsionado por su bloque de 9 meses a 0 (ver 1.5).

### 1.5 Los "0" en ventas: hay dos tipos

- **0 por falta de demanda**: ceros dispersos en series estables (`_252`, `_555`, `_586`, `_714`: menos del 1% de días con ventas 0).
- **0 por falta de disponibilidad** (rotura/descontinuación): bloques largos de ceros:
  - `_329`: **271-272 días seguidos** en 2015 (2015-01-30 → 2015-10-27/28) en **ambas** tiendas;
  - `_587` en CA_4: **361 días** (casi todo 2013);
  - `_120` en CA_4: bloques de hasta **140 días** (y en CA_3 no arranca hasta finales de mayo de 2013);
  - `_090` en CA_4: **34 días** en Navidad 2014-15.
- El dataset **no incluye la causa del 0** → no se puede distinguir "no vendí porque no había producto" de "no vendí porque nadie lo compró" con la información actual.

### 1.6 ¿Productos nuevos o demanda intermitente?

- Los arranques tardíos por tienda (`_120`-CA_3, `_587`-CA_4, `_329`…) **no parecen lanzamientos reales**: el producto existe y vende en el resto de tiendas y periodos.
- Conclusión: es **indisponibilidad / demanda intermitente**, no productos nuevos.

---

## 2. Problemas estructurales y cómo los vamos a resolver (explicado fácil)

### 2.1 Predecir a distintos niveles a la vez (forecasting jerárquico) → reconciliación

**El problema.** Distintos usos piden el mismo forecast a niveles distintos:
- **Financiero**: previsión de facturación/cashflow → interesa el **total** (o la categoría).
- **Logístico**: cuánto pedir al proveedor y qué repartir a cada tienda → interesa **tienda-producto**.

Si se entrena un modelo por nivel, las predicciones **no cuadran**: el modelo de categoría dice 1.000 unidades y la suma de los modelos de producto da 1.400. El analista entiende que es error probabilístico, pero finanzas y logística no: para ellos, el mismo concepto con dos números distintos es un problema.

**Las tres soluciones clásicas** (lo mismo que hacen, con heurísticas propias, los módulos comerciales de licencias caras; en Python/R se implementa igual):

- **Bottom-up**: modelar en el nivel más desagregado (producto-tienda) y sumar hacia arriba. La más sencilla y siempre "cuadra" (queda reconciliada). Inconveniente: acumula el error de las series pequeñas, que tienen más ruido.
- **Top-down**: manda el nivel agregado y se reparte hacia abajo con **pesos relativos** históricos. Ejemplo: la categoría predice 1.000; las tres subcategorías predecían 500+500+500 = 1.500 → se usa el % que representa cada una (~33%) sobre el 1.000 → 333/333/333. Nunca se usa el 1.500: el nivel que manda es el agregado.
- **Híbrida**: cuando existen varios niveles de agregación (p. ej. categoría y subcategoría), se modela en el nivel intermedio y en el producto; la categoría se construye sumando (bottom-up) y el producto se reparte (top-down). El error se reparte en las dos direcciones.

**Decisión en este proyecto**: la jerarquía es producto ↔ tienda (×2) ↔ total. Como las tiendas se comportan distinto, **se modeliza a nivel tienda-producto (20 series)** y, si alguien pide el total, se reconcilia agregando (bottom-up) o repartiendo con pesos históricos (top-down).

### 2.2 Demanda intermitente (días con 0 ventas)

**En un caso ideal**: tener el **inventario** como variable. "Hay stock + 0 ventas" → falta de demanda; "sin stock" → rotura. Esa variable discriminaría sola las dos situaciones. Aquí no existe.

**Qué haremos sin inventario**:

1. **Marcas de rotura/descontinuación a posteriori**: detectables por los bloques largos de ceros (sección 1.5), aunque no permitan adivinar el futuro.
2. **Modelizar a un nivel más agregado** cuando el producto-tienda es demasiado ruidoso (subcategoría, o segmentos de tiendas: rurales vs urbanas, etc.): más volumen = más capacidad estadística. Además, en un nivel agregado (p. ej. 500 uds/día) un día a 0 es raro → probablemente rotura, no falta de demanda.
3. **Variable sintética `posible_rotura` (1/0)** como variable exógena: enseña al modelo que los ceros van ligados a roturas y **libera al resto de variables** (p. ej. el día de la semana deja de "aprender" patrones falsos por culpa de los ceros); la rotura, al aparecer más veces, gana peso frente a otras predictoras menos informativas.
4. Avanzado: métodos tipo **Croston** y derivados, o un ML que prediga la **probabilidad de venta cero** de cada día.

### 2.3 Cientos o miles de productos (modelización masiva)

- Un modelo por serie no escala: aquí serían 20; en un retailer real, decenas de miles.
- **Solución adoptada**: un **modelo global con algoritmos de árboles rápidos (LightGBM)** para todas las series a la vez, usando producto y tienda como variables categóricas. Una vez entrenado, predecir es muy rápido.
- Si hacen falta niveles agregados: modelizar arriba (p. ej. subcategoría × tienda) y **bajar con top-down** usando los porcentajes históricos de cada producto dentro de su grupo (sacados de consultas al histórico de ventas).
- Si el volumen lo exige: entrenamiento en máquinas potentes / cloud.

**Variables de negocio que salen de este EDA y se crearán en Transformación**:

- `precio_relativo` (precio / precio modal del item-tienda) y `flag_promoción`;
- `month` (estacionalidad por producto);
- `posible_rotura` (demanda intermitente);
- índice `date` convertido a `datetime`.

---

## 3. Conclusiones y acciones

**Conclusiones**

- Se necesita una **estructura jerárquica** (con reconciliación) si el negocio pide varios niveles a la vez.
- **No hay productos nuevos reales**: lo que parece un lanzamiento por tienda es indisponibilidad / demanda intermitente.
- **Hay demanda intermitente** que no se puede explicar solo con la serie.

**Acciones (fase 04 → 07)**

1. **Modelizar a nivel tienda-producto**.
2. **Crear una variable que capture la demanda intermitente** (posible rotura).
3. **Usar LightGBM** (árboles, rápidos) + variables exógenas de negocio (precio, promoción, mes).
4. Convertir el índice `date` a `datetime`.

---

*Elaborado a partir del notebook `03_notebooks/03_EDA.ipynb` y de la sesión de diseño de soluciones (forecasting jerárquico, demanda intermitente y escala de SKUs).*
