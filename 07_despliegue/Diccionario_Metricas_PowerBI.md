# Diccionario de métricas del dashboard de forecasting retail

Cada medida del informe se documenta con la misma ficha. Se escribe primero en palabras (qué pregunta responde) y después la fórmula. Una medida solo se marca como verificada cuando coincide con el número calculado en Python.

## Plantilla de ficha

1. Nombre de la medida.
2. Pregunta de negocio que responde.
3. Definición en palabras, pensada para alguien que no sabe DAX.
4. Qué filtros respeta y cuáles ignora a propósito.
5. Fórmula DAX, con comentarios que expliquen el porqué y no solo el qué.
6. Control: valor esperado calculado fuera de Power BI.
7. Estado: pendiente, en revisión o verificada.

# Medidas de la página 1: Pronóstico

## Ventas_Reales

1. Pregunta: ¿cuánto se vendió de verdad en los últimos 15 días?
2. Definición: suma de unidades vendidas en los días con venta real registrada.
3. Respeta: fecha, tienda y producto. Ignora a propósito el filtro de Tipo, porque ya lo fija ella misma.
4. Control: 6.871 unidades sin filtros.
5. Estado: verificada.

```dax
// Suma de las ventas reales.
// CALCULATE fija Tipo en Real y reemplaza cualquier selección de Tipo que venga del informe.
Ventas_Reales =
CALCULATE(
    SUM(hechos[ventas]),
    hechos[tipo] = "Real"
)
```

## Ventas_Predichas

1. Pregunta: ¿cuánto se espera vender en los próximos 8 días?
2. Definición: suma de unidades pronosticadas por el modelo para los 8 días siguientes al corte.
3. Respeta: fecha, tienda y producto. Ignora a propósito el filtro de Tipo.
4. Control: 3.026 unidades sin filtros. El 25 de diciembre aparece en 0 por regla de negocio (la tienda cierra).
5. Estado: verificada.

```dax
// Suma del pronóstico.
// Igual que Ventas_Reales, pero fija Tipo en Prediccion (así está escrito en los datos, sin tilde).
Ventas_Predichas =
CALCULATE(
    SUM(hechos[ventas]),
    hechos[tipo] = "Prediccion"
)
```

## Peso_Producto

1. Pregunta: ¿qué parte de las ventas esperadas es de cada producto?
2. Definición: ventas predichas del grupo que dibuja el visual divididas entre las ventas predichas de todos los productos.
3. Respeta: tienda, fecha y demás filtros. Ignora a propósito el filtro de producto en el denominador.
4. Control: FOODS_3_586 18,2 % y FOODS_3_120 17,5 % sin otros filtros.
5. Estado: verificada.

```dax
Peso_Producto =
DIVIDE(
    // Arriba: las ventas predichas del grupo que dibuja el visual (la barra o la celda).
    [Ventas_Predichas],

    // Abajo: la misma medida, pero sin tener en cuenta el filtro de producto.
    // Así el total es de todos los productos y sobre ese total se saca el porcentaje.
    CALCULATE([Ventas_Predichas], ALL(dim_producto)),

    0  // si el total llega vacío o en cero, devuelve 0 y no un error
)
```

## Peso_Tienda

1. Pregunta: ¿qué parte de las ventas esperadas es de cada tienda?
2. Definición: ventas predichas del grupo que dibuja el visual divididas entre las ventas predichas de todas las tiendas.
3. Respeta: producto, fecha y demás filtros. Ignora a propósito el filtro de tienda en el denominador.
4. Control: CA_3 81,2 % y CA_4 18,8 % sin otros filtros.
5. Estado: verificada.

```dax
Peso_Tienda =
DIVIDE(
    // Arriba: las ventas predichas del grupo que dibuja el visual.
    [Ventas_Predichas],

    // Abajo: la misma medida, sin tener en cuenta el filtro de tienda.
    CALCULATE([Ventas_Predichas], ALL(Tiendas)),

    0
)
```

## Promedio_Diario_Real

1. Pregunta: ¿a qué ritmo se vendió en los últimos 15 días?
2. Definición: ventas reales divididas entre los días con venta real. Es el punto de comparación del ritmo del pronóstico.
3. Respeta: tienda y producto. La fecha también, pero la fórmula debe contar solo los días reales, no los 23 del modelo.
4. Control: 458,1 unidades por día sin filtros (6.871 entre 15).
5. Estado: en revisión. La fórmula de abajo es la versión de referencia. Si la versión final del informe cuenta los días de otra forma, se pega aquí.

```dax
// Ritmo diario de lo que ya pasó.
// El denominador cuenta solo los días con venta real. Si contara todas las fechas
// de hechos (23 días) mezclaría los días del pronóstico y el promedio saldría mal.
Promedio_Diario_Real =
DIVIDE(
    [Ventas_Reales],
    CALCULATE(DISTINCTCOUNT(hechos[date]), hechos[tipo] = "Real"),
    0
)
```

## Promedio_Diario_Predicho

1. Pregunta: ¿a qué ritmo se espera vender los próximos 8 días?
2. Definición: ventas predichas divididas entre los días del pronóstico.
3. Respeta: tienda, producto y fecha.
4. Control: 378,2 unidades por día sin filtros (3.026 entre 8). Incluye el 25 de diciembre en cero.
5. Estado: en revisión, igual que la anterior.

```dax
// Mismo cálculo que el ritmo real, pero con los días del pronóstico.
Promedio_Diario_Predicho =
DIVIDE(
    [Ventas_Predichas],
    CALCULATE(DISTINCTCOUNT(hechos[date]), hechos[tipo] = "Prediccion"),
    0
)
```

## Var_Ritmo_Pct

1. Pregunta: ¿el pronóstico va por encima o por debajo del ritmo reciente?
2. Definición: diferencia entre el ritmo diario predicho y el real, como porcentaje del real. Negativo significa que se espera vender menos por día que en los últimos 15 días.
3. Respeta: los mismos filtros que las dos medidas que usa.
4. Control: menos 17,4 % sin filtros. Ojo: el 25 de diciembre cerrado en cero arrastra este número hacia abajo. Sin ese día, los 7 días abiertos promedian 432,3 y la variación sería menos 5,6 %.
5. Estado: verificada.

```dax
Var_Ritmo_Pct =
// Se guardan las dos medidas en variables para leer la fórmula como una frase.
VAR Real_Diario = [Promedio_Diario_Real]
VAR Pred_Diario = [Promedio_Diario_Predicho]
RETURN
    // (predicho menos real) entre real. Si el real es cero, devuelve 0 y no un error.
    DIVIDE(Pred_Diario - Real_Diario, Real_Diario, 0)
```

# Medidas de la página 2: Confiabilidad

Todas salen de la tabla `backtest` (640 filas: 4 ventanas de 8 días de diciembre de 2015, con las columnas fecha_corte, date, horizonte, store_id, item_id, real, pred y pred_base). `pred_base` es la regla simple de comparación: lo que esa serie vendió hace 7 días.

Ninguna de las cinco usa CALCULATE. Es a propósito: deben responder a lo que llegue del filtro (ventana, tienda, producto, día del horizonte) y CALCULATE sirve para cambiar o quitar filtros, que aquí no se quiere. Para que funcione, `backtest` debe estar relacionada con `Tiendas` y `dim_producto`, y los filtros deben construirse con columnas de esas dimensiones.

## Error_Abs_Total

1. Pregunta: ¿cuántas unidades se equivocó el modelo en total?
2. Definición: suma del error de cada fila sin signo, para que los errores por exceso y por defecto no se cancelen.
3. Respeta: ventana, tienda, producto y día del horizonte.
4. Control: 5.615 unidades sin filtros.
5. Estado: verificada.

```dax
// Suma fila por fila de la diferencia entre lo predicho y lo real, sin signo.
// SUMX recorre cada fila de backtest, calcula el error y recién después suma.
Error_Abs_Total =
SUMX(backtest, ABS(backtest[pred] - backtest[real]))
```

## MAE_Modelo

1. Pregunta: ¿cuántas unidades se equivoca el modelo, en promedio, por serie y por día?
2. Definición: error absoluto total dividido entre el número de filas. Es la nota del modelo.
3. Respeta: los mismos filtros que Error_Abs_Total.
4. Control: 8,77 sin filtros. Por ventana: 9,55 (corte 30 de noviembre), 7,89 (8 de diciembre), 8,97 (16 de diciembre) y 8,69 (23 de diciembre).
5. Estado: verificada.

```dax
// Es el MAE con el que el modelo se califica: el error absoluto total entre el número de filas.
// backtest sale de un script de Python (exportar_backtest.py) que repite la evaluación del notebook 08.
MAE_Modelo =
DIVIDE([Error_Abs_Total], COUNTROWS(backtest), 0)
```

## MAE_Base

1. Pregunta: ¿cuánto se equivocaría una regla simple, la de repetir lo que se vendió hace 7 días?
2. Definición: el mismo cálculo del MAE, pero con la columna pred_base. Sirve de vara para saber si el modelo aporta algo.
3. Respeta: los mismos filtros que MAE_Modelo.
4. Control: 10,30 sin filtros. Por ventana: 16,17, 8,31, 6,91 y 9,81.
5. Estado: verificada.

```dax
// Igual que MAE_Modelo, cambiando la predicción del modelo por la de la regla simple.
MAE_Base =
DIVIDE(
    SUMX(backtest, ABS(backtest[pred_base] - backtest[real])),
    COUNTROWS(backtest)
)
```

## Mejora_Vs_Base

1. Pregunta: ¿el modelo vale la pena frente a la regla simple, y cuánto?
2. Definición: 1 menos el cociente entre el error del modelo y el de la regla simple. Positivo, el modelo mejora. Negativo, la regla simple es mejor.
3. Respeta: los mismos filtros que las dos medidas que usa.
4. Control: 14,8 % sin filtros. Por ventana: 40,9 %, 5,1 %, menos 29,8 % y 11,4 %.
5. Estado: verificada. Lleva formato condicional: verde si es mayor que 0, rojo si es menor que 0.

```dax
// Compara el MAE del modelo contra el de la regla simple, a ver si es mejor.
// 0,148 se lee: el modelo se equivoca un 14,8 % menos.
Mejora_Vs_Base =
1 - DIVIDE([MAE_Modelo], [MAE_Base], 0)
```

## Sesgo

1. Pregunta: ¿el modelo se pasa o se queda corto en promedio?
2. Definición: unidades predichas menos unidades reales, como porcentaje de las reales. Positivo, sobreestima. Negativo, subestima. No usa valor absoluto, porque aquí interesa el sentido del error.
3. Respeta: ventana, tienda, producto y día del horizonte.
4. Control: más 1,9 % sin filtros. CA_3 menos 4,4 %, CA_4 más 35,3 %. Casi todo ese 35,3 % viene de FOODS_3_090, que dejó de venderse en diciembre. En la tabla por producto, ese artículo muestra más 501 %.
5. Estado: verificada. Formato condicional: neutro entre menos 5 % y más 5 %, ámbar fuera de ese rango.

```dax
// Dice si el modelo se pasa o se queda corto en promedio.
// Aquí no hay ABS a propósito: los errores por exceso y por defecto deben poder cancelarse
// para mostrar hacia dónde tiende a equivocarse el modelo.
Sesgo =
DIVIDE(
    SUM(backtest[pred]) - SUM(backtest[real]),
    SUM(backtest[real]),
    0
)
```

# Tablas del modelo de datos

1. `hechos`: una fila por fecha, tienda y producto. Junta los 15 días reales y los 8 del pronóstico. La columna `tipo` vale Real o Prediccion (sin tilde, así está en los datos).
2. `backtest`: una fila por ventana de prueba, día, tienda y producto. Trae lo real, lo predicho por el modelo y lo predicho por la regla simple.
3. Dimensiones: `Tiendas`, `dim_producto` y `dim_calendario`. Los filtros de ambas páginas se construyen con sus columnas.
4. Parámetros: `RutaBase` guarda la carpeta donde están los CSV (sin barra final) y `Fecha-Corte` es el primer día del pronóstico, calculado desde `predicciones.csv`.
5. Las medidas viven en la tabla `Medidas`.

## Reglas de contexto que conviene recordar

1. Los segmentadores y cada grupo de un visual (eje, filas, columnas) son filtros. La medida se calcula una vez por cada grupo, con esos filtros puestos.
2. CALCULATE reemplaza solo los filtros de las columnas que menciona. Por eso Tipo igual a Prediccion cambia el tipo, pero la tienda, el producto y la fecha de cada barra o punto siguen activos y la agrupación funciona.
3. ALL apaga únicamente los filtros de la tabla o columna que se le indica. Si el filtro viene de una dimensión, el ALL debe apuntar a la dimensión. Por eso los segmentadores se construyen con columnas de las dimensiones (tienda, producto, calendario) y no con columnas de hechos.
4. Porcentaje sobre el total. La medida se adapta al grupo que dibuja el visual (la barra o la celda) y se divide entre la misma medida con un no tengas en cuenta ese filtro, para tener un total general sobre el que sacar el porcentaje. Se apaga el filtro de la dimensión por la que se agrupa. Con ALL el total ignora también los segmentadores de esa dimensión, con ALLSELECTED respeta los que el usuario dejó seleccionados. Atajo sin medida: Mostrar valor como, porcentaje del total general, en el propio visual.
5. Una línea con dos medidas que viven en fechas distintas deja un hueco entre ellas. No es un error: la serie real termina el 23 de diciembre, el pronóstico empieza el 24 y no hay un punto que las una.
6. Una medida en una tarjeta, sin segmentador, devuelve el total de todo. Un peso sin filtros da 1, y eso es correcto.
7. El formato (porcentaje, separador de miles, decimales) se fija en la medida y no en cada visual.
8. Dónde va cada cosa en un visual: las medidas solo van en Valores (o Campos, en una tarjeta). El eje, la leyenda, las filas, las columnas y los segmentadores aceptan columnas, no medidas.
9. Un iterador (la familia SUMX) calcula una expresión fila por fila y suma después. Es la forma de medir errores sin crear columnas calculadas, y se comporta como una medida más, o sea que responde a los filtros.
10. CALCULATE es para cambiar o quitar filtros. Si una medida debe obedecer a lo que el usuario elige, no lleva CALCULATE.
11. Un porcentaje de sesgo grande puede venir de una sola serie. Antes de culpar al modelo, conviene abrir el detalle por producto.
