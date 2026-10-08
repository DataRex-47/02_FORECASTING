# 🧠 Contexto técnico del tablero + errores resueltos

> **Léelo completo antes de tocar el `.pbix`.** Aquí está todo lo que se aprendió construyendo la
> página 1 del tablero (madrugada del 8-oct-2026). Está pensado para que otro chat/agente (o tu yo
> del futuro) pueda continuar sin repetir errores.

---

## 0. Estado actual (dónde estamos)

- El tablero (`Tablero_Ventas_v2_DisenoIA.pbix`) ya tiene **20 medidas** (10 originales + 10 nuevas) y **1 página**
  rediseñada con **estilo claro accesible** (tarjetas blancas, acentos tipo "IA", pensado para no cansar
  la vista).
- Archivos:
  - `07_despliegue/Tablero_Ventas_v2_DisenoIA.pbix` → **el tablero único** (tema claro, medidas nuevas).
  - Respaldo del diseño preliminar anterior: `99_otros/Diseno_Tablero_PBI/_Respaldos/Tablero_Ventas_original_2026-10-08.pbix`.
- Scripts que generan y empaquetan el diseño: `99_otros/Diseno_Tablero_PBI/`
  (`generar_diseno.py`, `empaquetar_pbix.py`) → **ojo: tienen rutas temporales dentro; hay que
  ajustar las constantes de rutas antes de reutilizarlos.**

---

## 1. De dónde salen los datos (flujo de producción)

```
Sistemas → consulta_entrada_ejecucion.sql → DatosParaProduccion.csv ┐
                                                                    ├→ ejecuciones.py → predicciones.csv
modelos entrenados (ohe_retail.pkl + lista_modelos_retail.pkl) ─────┘
```

- `DatosParaProduccion.csv` (separador `;`, fecha `dd/mm/yyyy`): 15 días reales + los días a predecir.
- `predicciones.csv` (coma): solo los 8 días predichos (`date,store_id,item_id,ventas`).
- Power BI lee **ambos CSV** por Power Query (expresiones M: `RutaBase`, `DatosParaProduccion`,
  `predicciones`). Si cambian columnas/formato, el tablero puede fallar en la actualización.

---

## 2. Modelo semántico

**Tablas**

| Tabla | Origen | Contenido |
|-------|--------|-----------|
| `hechos` | M: `Table.Combine({DatosParaProduccion, predicciones})` | `date`, `ventas`, `store_id`, `item_id`, `Tipo` |
| `Tiendas` | M: distinct de `hechos[store_id]` | `store_id` |
| `Productos` | M: distinct de `hechos[item_id]` | `item_id` |
| `dim_calendario` | Calculada: `CALENDAR(MIN(hechos[date]), MAX(hechos[date]))` | `Date`, `Anio`, `Mes`, `MesNombre`, `DiaSemanaNumero`, `DiaSemanaNombre`, `FechaTexto` |
| `Fecha-Corte` | M: lee `predicciones.csv` y toma la fecha **mínima** | 1 columna, valor **24/12/2015** (primer día predicho; ⚠️ NO es el cierre) |
| `Medidas` | M: tabla vacía contenedora | aquí viven todas las medidas |

**Datos clave (estado actual del CSV de ejemplo)**

- `Tipo = "Real"` → 09/12/2015 a 23/12/2015 (15 días, 300 filas).
- `Tipo = "Prediccion"` → 24/12/2015 a 31/12/2015 (8 días, 160 filas).
- 2 tiendas (`CA_3`, `CA_4`) × 10 productos.
- ⚠️ Ojo: `Fecha-Corte` (tabla) = primer día predicho = 24/12/2015.
  El **cierre real de datos** es 23/12/2015 y se obtiene con la medida `Fecha_Cierre`.

**Relaciones** (todas 1→muchos, filtro en una dirección)

- `hechos[store_id]` → `Tiendas[store_id]`
- `hechos[item_id]` → `Productos[item_id]`
- `hechos[date]` → `dim_calendario[Date]`
- `hechos[date]` → `Fecha-Corte[Fecha-Corte]`
- (`Fecha-Corte` arrastra una tabla de fecha automática oculta; no tocar)

---

## 3. Las 20 medidas (DAX)

### Originales de Andrés
| Medida | DAX |
|--------|-----|
| `Ventas_Reales` | `CALCULATE(SUM(hechos[ventas]), hechos[Tipo] = "Real")` |
| `Ventas_Predichas` | `CALCULATE(SUM(hechos[ventas]), hechos[Tipo] = "Prediccion")` |
| `Promedio_Diario_Real` | `DIVIDE([Ventas_Reales], CALCULATE(DISTINCTCOUNT(hechos[date]), hechos[Tipo]="Real"), 0)` |
| `Promedio_Diario_Predicho` | `DIVIDE([Ventas_Predichas], CALCULATE(DISTINCTCOUNT(hechos[date]), hechos[Tipo]="Prediccion"), 0)` |
| `Var_Ritmo_Pct` | `DIVIDE([Promedio_Diario_Predicho] - [Promedio_Diario_Real], [Promedio_Diario_Real], 0)` |
| `Peso_Producto` | `DIVIDE([Ventas_Predichas], CALCULATE([Ventas_Predichas], ALL(Productos)), 0)` |
| `Peso_Tienda` | `DIVIDE([Ventas_Predichas], CALCULATE([Ventas_Predichas], ALL(Tiendas)), 0)` |
| `Peso_CA_3` / `Peso_CA_4` | versiones fijas de tienda (ocultas) |
| `Peso_Generico` | peso con `ALL(Tiendas[store_id])` (manual de Andrés) |

### Nuevas (carpeta "Contexto" e "Insights")

| Medida | DAX |
|--------|-----|
| `Fecha_Cierre` | `CALCULATE(MAX(hechos[date]), hechos[Tipo] = "Real")` → **23/12/2015** |
| `Fecha_Fin_Pronostico` | `CALCULATE(MAX(hechos[date]), hechos[Tipo] = "Prediccion")` |
| `Dias_Pronostico` | `CALCULATE(DISTINCTCOUNT(hechos[date]), hechos[Tipo] = "Prediccion")` |
| `Dias_Historial` | `CALCULATE(DISTINCTCOUNT(hechos[date]), hechos[Tipo] = "Real")` |
| `Fecha_Cierre_Txt` | `FORMAT([Fecha_Cierre], "dd/mm/yyyy")` |
| `Subtitulo_Cierre` | `"📅 Datos reales hasta el " & FORMAT([Fecha_Cierre],"dd/mm/yyyy") & "   ·   🔮 Pronóstico " & [Dias_Pronostico] & " días: " & FORMAT([Fecha_Cierre]+1,"dd/mm") & " → " & FORMAT([Fecha_Fin_Pronostico],"dd/mm/yyyy")` |
| `Insight_Producto` | `VAR Filas = ADDCOLUMNS(VALUES(Productos[item_id]), "@Ventas", [Ventas_Predichas])  VAR TopFila = TOPN(1, Filas, [@Ventas], DESC)  VAR Producto = MAXX(TopFila, Productos[item_id])  VAR Ventas = MAXX(TopFila, [@Ventas])  VAR Total = CALCULATE([Ventas_Predichas], ALL(Productos))  RETURN "🎯 Producto estrella: " & Producto & "  ·  " & FORMAT(DIVIDE(Ventas, Total),"0.0%") & " de la proyección"` |
| `Insight_Tienda` | igual que la anterior con `Tiendas[store_id]` y `ALL(Tiendas)` |
| `Insight_Dia` | igual con `hechos[date]`; devuelve p. ej. `"📅 Día pico proyectado: domingo 27/12  ·  488 uds."` |
| `Insight_Ritmo` | `VAR Ritmo = [Var_Ritmo_Pct]  VAR Tendencia = IF(Ritmo >= 0, "📈 al alza", "📉 a la baja")  RETURN "⚡ Ritmo proyectado " & FORMAT(Ritmo, "+0.0%;-0.0%;0.0%") & " frente al promedio real  ·  " & Tendencia` |

> Nota DAX: no uses `VAR Top` (da error de sintaxis). Usa `TopFila`.

---

## 4. El informe (formato PBIR)

El `.pbix` guarda el diseño como **carpeta de archivos JSON** (`Report/definition/...`) — formato
"mejorado" (PBIR). Estructura:

```
Report/definition/report.json              → informe (tema base + tema propio + resourcePackages)
Report/definition/pages/pages.json         → orden de páginas
Report/definition/pages/<pagina>/page.json → tamaño 1920x1080, fondo
Report/definition/pages/<pagina>/visuals/<id>/visual.json → cada visual
Report/StaticResources/RegisteredResources/RexIA_Forecast.json → tema propio
Report/StaticResources/RegisteredResources/fondo_forecast.png  → fondo (1920x1080)
```

**Página 1 "🔮 Pronóstico" — 16 visuales**

| Visual | x | y | ancho | alto |
|--------|---|---|-------|------|
| Encabezado (textbox + valor dinámico `Subtitulo_Cierre`) | 28 | 24 | 1176 | 124 |
| Etiquetas filtros 🏪/📦/📅 | 1222 / 1450 / 1678 | 30 | 216 | 26 |
| Slicers Tienda / Producto / Fecha (dropdown) | 1220 / 1448 / 1676 | 58 | 216 | 76 |
| KPI 💰 `Ventas_Predichas` | 28 | 172 | 448 | 144 |
| KPI 📈 `Promedio_Diario_Predicho` | 500 | 172 | 448 | 144 |
| KPI 🧾 `Promedio_Diario_Real` | 972 | 172 | 448 | 144 |
| KPI ⚡ `Var_Ritmo_Pct` | 1444 | 172 | 448 | 144 |
| Línea 📈 Real vs pronóstico (`dim_calendario[Date]` × `Ventas_Reales`+`Ventas_Predichas`) | 28 | 340 | 1250 | 360 |
| Panel 🤖 insights (textbox, 4 valores dinámicos) | 1302 | 340 | 590 | 360 |
| Matriz 🧮 producto × día (`Ventas_Predichas`) | 28 | 724 | 1090 | 332 |
| Barras ⚖️ `Peso_Producto` por producto | 1142 | 724 | 372 | 332 |
| Dona 🏪 `Peso_Tienda` por tienda | 1536 | 724 | 356 | 332 |

**Sistema de diseño**

| Elemento | Valor |
|----------|-------|
| Fondo de página | `#F6F8FC` + imagen `fondo_forecast.png` (degradados suaves cian/violeta) |
| Tarjetas | fondo `#FFFFFF`, borde `#DDE5F0`, radio 14-16 |
| Panel IA | fondo `#F4F1FF`, borde violeta `#6D28D9`, texto de insights `#4338CA` |
| Acentos | cian `#0E7490`, violeta `#6D28D9`, azul `#1D4ED8`, ámbar `#B45309`, rosa `#BE123C` |
| Texto | principal `#16233A`, secundario `#42536E`, etiquetas `#5B6B84` |
| Tipografía | Segoe UI / Segoe UI Semibold |
| Emojis | 🔮 encabezado · 💰📈🧾⚡ KPIs · 🤖 insights · 🧮 matriz · ⚖️ producto · 🏪 tienda · 🎛️ filtros |

### Cómo adaptar el diseño a medidas/visuales nuevos (receta)

Andrés decide el contenido; el diseño se le aplica con este molde. **Cualquier visual nuevo debe
salir con el mismo aspecto que los de la página 1.**

**Paso 1 — Leer el modelo real antes de tocar nada** (por MCP):
`measure_operations List` para ver las medidas existentes y `table_operations List` para las tablas.
Usar los nombres reales (`Medidas.<Nombre>`, `Productos[item_id]`, `Tiendas[store_id]`,
`dim_calendario[Date]`, `hechos[date]`, etc.).

**Paso 2 — Contenedor estándar de tarjeta** (copiar tal cual en el `visual.json` del visual nuevo):

```json
"visualContainerObjects": {
  "title": [{"properties": {
    "show": {"expr": {"Literal": {"Value": "true"}}},
    "text": {"expr": {"Literal": {"Value": "'⚖️ Título con emoji'"}}},
    "fontSize": {"expr": {"Literal": {"Value": "13D"}}},
    "fontColor": {"solid": {"color": {"expr": {"Literal": {"Value": "'#16233A'"}}}}},
    "bold": {"expr": {"Literal": {"Value": "true"}}},
    "alignment": {"expr": {"Literal": {"Value": "'left'"}}}
  }}],
  "background": [{"properties": {
    "show": {"expr": {"Literal": {"Value": "true"}}},
    "color": {"solid": {"color": {"expr": {"Literal": {"Value": "'#FFFFFF'"}}}}},
    "transparency": {"expr": {"Literal": {"Value": "0D"}}}
  }}],
  "border": [{"properties": {
    "show": {"expr": {"Literal": {"Value": "true"}}},
    "color": {"solid": {"color": {"expr": {"Literal": {"Value": "'#DDE5F0'"}}}}},
    "radius": {"expr": {"Literal": {"Value": "14D"}}},
    "width": {"expr": {"Literal": {"Value": "1D"}}}
  }}],
  "dropShadow": [{"properties": {"show": {"expr": {"Literal": {"Value": "true"}}},
    "preset": {"expr": {"Literal": {"Value": "'Custom'"}}},
    "transparency": {"expr": {"Literal": {"Value": "78D"}}},
    "shadowBlur": {"expr": {"Literal": {"Value": "14D"}}},
    "shadowDistance": {"expr": {"Literal": {"Value": "3D"}}},
    "angle": {"expr": {"Literal": {"Value": "90D"}}},
    "shadowSpread": {"expr": {"Literal": {"Value": "0D"}}}}}],
  "padding": [{"properties": {
    "top": {"expr": {"Literal": {"Value": "8D"}}},
    "bottom": {"expr": {"Literal": {"Value": "8D"}}},
    "left": {"expr": {"Literal": {"Value": "8D"}}},
    "right": {"expr": {"Literal": {"Value": "8D"}}}
  }}]
}
```
> El color del borde puede cambiarse por un acento (cian/violeta/azul/ámbar/rosa) para destacar el
> visual. El radio típico es 14 (16-18 para paneles grandes como el encabezado o el panel IA).

**Paso 3 — Convenciones de estilo**
- Título con **emoji + texto corto** en español (los emojis usados están en la tabla de arriba).
- KPI: `visualType: "cardVisual"`, con la medida proyectada y `"displayName"` que incluya el emoji
  (ej.: `"💰 Ventas predichas · 8 días"`). Sin título de contenedor (el displayName hace de etiqueta).
- Series de gráficos: los colores salen solos del tema (`dataColors`: cian → violeta → verde → ámbar…).
- Paleta para cualquier color manual: cian `#0E7490`, violeta `#6D28D9`, azul `#1D4ED8`,
  ámbar `#B45309`, rosa `#BE123C`; textos `#16233A`/`#42536E`/`#5B6B84`.
- Accesibilidad: mantener textos oscuros sobre tarjetas blancas y no aclarar más los acentos
  (están elegidos para contraste AA). Los insights del panel usan `#4338CA`.
- Posiciones: mantener márgenes de 28 px y separaciones de 16-24 px entre tarjetas (ver tabla de la
  página 1 como referencia de rejilla).

**Paso 4 — Texto dinámico (mostrar una medida dentro de un textbox)**
El run del texto lleva:
`"value": {"propertyIdentifier": {"objectName": "values", "propertyName": "expr"}, "selector": {"id": "Value"}}`
y en `visual.objects` va el objeto `values` con la medida (estructura `Aggregation`/`Column`/`Subquery`/
`Select`; ver un ejemplo ya funcionando en el visual `a0010000000000000001` o `a0020000000000000002`
de la página 1). Los `selector.id` deben ser únicos por visual (`Value`, `Value 2`, `Value 3`…).

**Paso 5 — Medidas nuevas (si hacen falta)**
- Crear por MCP **sin** `dataType` (da error).
- Nombres con guion bajo y sin espacios (`Mi_Medida_Nueva`), `formatString` adecuado
  (`#,##0`, `#,##0.0`, `0.0%`, `dd/mm/yyyy`…) y `displayFolder` (`Contexto` / `Insights`).
- En DAX: no usar `VAR Top` (error de sintaxis; usar `TopFila`), y referirse al tipo como
  `hechos[Tipo]` (`"Real"` / `"Prediccion"`).
- Validar la medida con `dax_query_operations Execute` antes de usarla en un visual.

**Paso 6 — Empaquetar y verificar** (sección 5 + técnicas de la sección 7):
reempaquetar con `SecurityBindings` a ceros → abrir con `Start-Process` → comprobar título de ventana
→ captura + análisis de píxeles → OCR para confirmar textos.

---

## 5. Flujo correcto para modificar el informe por fuera de Power BI

1. **Cerrar Power BI Desktop** (si no, bloquea archivos y sobrescribe cambios al guardar).
2. Copiar el `.pbix` a una carpeta de trabajo (nunca editar el original a pelo).
3. Extraerlo como ZIP y editar `Report/definition/**` (JSON **minificado, UTF-8 sin BOM, LF**).
4. Reempaquetar:
   - Conservar todas las entradas no-`Report/` tal cual (DataModel, Settings, Version, etc.).
   - Reemplazar toda la carpeta `Report/`.
   - Si se añaden PNG: `<Default Extension="png" ContentType="" />` en `[Content_Types].xml`.
   - **⚠️ Neutralizar `SecurityBindings`**: escribir el mismo número de bytes, todos a cero.
     Sin esto, Power BI rechaza el archivo con "está dañado o es de una versión no reconocida".
5. Abrir con `Start-Process <ruta.pbix>` y comprobar el **título de la ventana**:
   `Sin título - Power BI Desktop` = falló; el nombre del archivo = abrió bien.
6. Para dejarlo "oficial": abrir en Power BI y **Ctrl+S** (así se regenera el precinto).

---

## 6. ⚠️ BITÁCORA DE ERRORES RESUELTOS (leer antes de tocar nada)

| # | Error / síntoma | Causa real | Solución |
|---|-----------------|------------|----------|
| 1 | **"Este archivo está dañado o se ha creado con una versión no reconocida de Power BI Desktop y no se puede abrir"** al abrir un `.pbix` modificado por fuera | `SecurityBindings`: firma que Power BI escribe al guardar y que se invalida con **cualquier** cambio externo (aunque sea una letra) | Escribir `SecurityBindings` con el mismo tamaño pero **relleno de ceros** al reempaquetar. Verificado con pruebas A/B. |
| 2 | El mensaje anterior también aparecía cuando en realidad faltaba un archivo declarado (tema o imagen registrados pero ausentes) | El mensaje es **genérico y engañoso**; cubre cualquier fallo de carga | Regla: todo recurso declarado en `report.json` debe existir en `Report/StaticResources/...` |
| 3 | Los JSON escritos con Python salían **multilínea con CRLF** | `json.dump` en modo texto de Windows | Escribir con `json.dumps(..., separators=(",",":"))` y `write_bytes` (minificado, LF, sin BOM) |
| 4 | `PermissionError [WinError 32] ... está siendo utilizado por otro proceso` al regenerar | Power BI tenía abierto un `.pbix` de prueba | Cerrar Power BI antes de regenerar/empaquetar; separar carpetas de trabajo de las de respaldo |
| 5 | MCP: `Cannot set the data type of a new measure explicitly` | El MCP no acepta `dataType` al crear medidas | No enviar `dataType` al crear (Power BI lo infiere) |
| 6 | DAX: `The syntax for 'Top' is incorrect` | `VAR Top = TOPN(...)` choca con la sintaxis | Renombrar la variable (p. ej. `TopFila`) |
| 7 | Valor dinámico (medida) dentro de un textbox: **no está definido en el esquema público** | Microsoft no documenta esa parte del formato | Estructura real (verificada en 4 repositorios): el run lleva `"value": {"propertyIdentifier": {"objectName":"values","propertyName":"expr"}, "selector": {"id":"Value"}}` y en `visual.objects.values[]` va el `Aggregation/Column/Subquery/Select` con `selector.id` coincidente |
| 8 | Fondo de página con imagen: estructura exacta desconocida | Igual que el punto 7 | `objects.background[0].properties.image.image` = `{name: literal, url: ResourcePackageItem(PackageName=RegisteredResources, **PackageType=1**, ItemName=archivo), scaling: 'Fit'}`, + item `type:"Image"` en `resourcePackages`, + PNG en `RegisteredResources/`, + `Default Extension="png"` en `[Content_Types].xml` |
| 9 | Abrir el `.pbix` lanzando `PBIDesktop.exe "<ruta>"` mostraba "Sin título" (documento en blanco) | El paso del argumento con comillas no funciona igual vía alias de la Store | Abrir con `Start-Process "<ruta.pbix>"` (asociación de archivos) |
| 10 | `ListLocalInstances` devolvía 0 instancias aunque Power BI estaba abierto | Power BI aún estaba cargando | Esperar a que la ventana muestre el título del archivo antes de conectar el MCP |
| 11 | El lienzo del informe no expone su contenido por **UI Automation** (solo aparece la ventana) | El contenido se dibuja en WebView con accesibilidad limitada | Verificar con: título de ventana + análisis de píxeles (captura) + **OCR de Windows** (ver utilidades) |
| 12 | OCR: `Windows.Media.Ocr` funciona desde PowerShell con el patrón `AsTask`/`Await` de WinRT | — | Script de ejemplo: `07_despliegue/Documentacion_IA/utilidades/ocr_captura.ps1` |
| 13 | Capturar la ventana con `CopyFromScreen` daba imágenes que no correspondían a Power BI | Captura por región de pantalla según el z-order real | Usar `PrintWindow(hwnd, hdc, 2)` sobre el handle de la ventana: `utilidades/capturar_ventana.ps1` |
| 14 | El ZIP del `.pbix` exige orden/serialización concretos | Falso: probado y **no** es un problema (reempaquetado idéntico y con orden cambiado abren bien) | El único requisito crítico es el punto 1 (SecurityBindings) |

**Pruebas A/B que demostraron la causa (por si se repite):**
`cambio mínimo + SecurityBindings intacto` → ❌ falla ·
`cambio mínimo + SecurityBindings a ceros` → ✅ abre ·
`cambio mínimo + SecurityBindings eliminado` → ✅ abre ·
`sin cambios + escrita idéntica` → ✅ abre.

---

## 7. Técnicas de verificación (sin poder "ver" la pantalla)

1. **Título de ventana**: `Get-Process PBIDesktop | Select MainWindowTitle`.
2. **Captura real de la ventana**: `PrintWindow` (ver `utilidades/capturar_ventana.ps1`).
3. **Análisis de píxeles** con numpy: con el tema claro los valores esperados son ~88% claro,
   ~74% blanco puro, ~10% texto oscuro y algo de acento violeta (panel). Si sale mayoritariamente
   oscuro: o no terminó el render o hay un panel de la UI encima (p. ej. la barra de fórmulas DAX).
4. **OCR** (`utilidades/ocr_captura.ps1`): leer el texto renderizado. Sirvió para confirmar:
   `"Datos reales hasta el 23/12/2015 · Pronóstico 8 días: 24/12 → 31/12/2015"`, `-17,4%`, `458,1`,
   `378,3`, `CA_3 - 81.2%`, `Día pico 27/12 - 488`.
5. **MCP** (`powerbi-authoring-local`): `ListLocalInstances` → `Connect` → `measure_operations List`
   o `dax_query_operations Execute` para validar medidas.

---

## 8. Ideas para la página 2 (por decidir con Andrés)

- Detalle por producto × tienda (matriz o tabla con real vs predicho y variación).
- Comparación del **ritmo** de cada producto (barras con `Var_Ritmo_Pct`).
- Top/peores productos y su peso (`Peso_Producto`).
- Histórico real (15 días) vs pronóstico (8 días) por tienda.
- Panel de "calidad del modelo" si más adelante hay datos de validación.
- Mantener: encabezado con `Subtitulo_Cierre` (mismo estilo), paleta y emojis.

---

## 9. Inventario rápido de la carpeta

| Archivo/carpeta | Qué es |
|-----------------|--------|
| `Tablero_Ventas_v2_DisenoIA.pbix` | **El tablero** (página 1, tema claro accesible, con las medidas nuevas) |
| `99_otros/Diseno_Tablero_PBI/_Respaldos/Tablero_Ventas_original_2026-10-08.pbix` | Respaldo del diseño preliminar (archivado, no usar salvo emergencia) |
| `predicciones.csv` | Salida de `ejecuciones.py` (8 días) |
| `DatosParaProduccion.csv` | Entrada de sistemas (15 reales + días a predecir) |
| `funciones.py`, `reentrenamiento.py`, `ejecuciones.py` | Pipeline local |
| `instrucciones/` | Chuleta de uso + programación de tareas |
| `Documentacion_IA/` | Esta documentación + prompt para nuevos chats + utilidades |
