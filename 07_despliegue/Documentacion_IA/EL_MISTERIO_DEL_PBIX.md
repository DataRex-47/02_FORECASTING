# 🕵️ El misterio del `.pbix` que no abría (la historia en cristiano)

**Fecha:** 8 de octubre de 2026, madrugada 🌙
**Protagonista:** el archivo `Tablero_Ventas.pbix` (hoy, tras el rediseño, vive como
`Tablero_Ventas_v2_DisenoIA.pbix`)
**Estado:** ✅ Resuelto. Existe una versión rediseñada que abre perfectamente:
`07_despliegue/Tablero_Ventas_v2_DisenoIA.pbix`

---

## 1. Resumen en 30 segundos

Estábamos rediseñando el tablero de forecasting (al principio con un tema oscuro "muy IA" — el
resultado final fue un **tema claro y suave**, más descansado para la vista —, tarjetas, panel de
insights automáticos y la **fecha de cierre dinámica** en el título). Pero cada vez que intentaba
abrir el tablero rediseñado, Power BI decía:

> *"Este archivo está dañado o se ha creado con una versión no reconocida de Power BI Desktop y no
> se puede abrir."*

**Ese mensaje era un engaño.** El archivo no estaba dañado ni era de otra versión. Lo que pasa es
que Power BI guarda dentro del `.pbix` una especie de **precinto de seguridad**
(`SecurityBindings`). Si alguien modifica el contenido desde fuera (como hice yo para aplicar el
diseño), el precinto ya no cuadra y Power BI, por precaución, se niega a abrirlo.

**La solución:** al reconstruir el archivo se anula el precinto (se rellena de ceros). Power BI lo
acepta y genera uno nuevo cuando tú lo guardas desde la aplicación.

---

## 2. La analogía del lacre

Un `.pbix` es como una **caja fuerte con un lacre** (el sello de cera de los documentos antiguos):

- Cuando tú guardas, Power BI sella la caja con un lacre hecho a medida del contenido.
- Si alguien abre la caja y cambia cualquier cosa —aunque sea una coma— el lacre ya no coincide.
- Power BI ve el lacre roto y piensa: *"aquí ha pasado algo raro, no abro esto"*. Y como no sabe
  explicarlo bien, suelta el dramático *"archivo dañado o versión no reconocida"*.

Yo cambiaba el diseño **desde fuera** (sin la aplicación abierta), así que el lacre siempre quedaba
roto… hasta que aprendí a **derretir el lacre** (rellenarlo de ceros) antes de devolver la caja.

---

## 3. La investigación, paso a paso 🔍

Pruebas controladas: en cada una metía **una sola pieza** del rediseño y abría el archivo.

| # | Prueba | Resultado |
|---|--------|-----------|
| 1 | Tu archivo original, tal cual | ✅ Abre |
| 2 | Archivo reconstruido **sin cambiar nada** | ✅ Abre |
| 3 | Solo cambiar el **tema de colores** | ❌ No abre |
| 4 | Solo cambiar el **fondo con imagen** | ❌ No abre |
| 5 | Solo cambiar los **16 visuales nuevos** | ❌ No abre |
| 6 | Solo añadir **un cuadro de texto** ("🏪 Tienda") | ❌ No abre |
| 7 | Solo cambiar el **color de fondo de la página** | ❌ No abre |
| 8 | Un cambio mínimo **+ precinto a cero** | ✅ **Abre** 🎉 |
| 9 | Un cambio mínimo **+ precinto eliminado** | ✅ **Abre** 🎉 |
| 10 | **Rediseño completo + precinto a cero** | ✅ **Abre** 🎉🎉 |

La pista de oro fue la prueba 8: el mismo cambio que antes fallaba funcionó al neutralizar el
precinto. Culpable confeso.

**Pistas falsas** (por si sirve de aprendizaje): pensé que era el formato de los JSON (saltos de
línea de Windows, minificado, codificación) y el orden de los archivos dentro del ZIP.
**No era eso.** La clave salió de comparar lo que Power BI guarda con lo que había antes: al
guardar, **todos los JSON del reporte quedan idénticos, pero `SecurityBindings` cambia**.

---

## 4. Resultado final verificado ✅

Abrí el archivo rediseñado y comprobé (análisis de colores + OCR de la pantalla) que **todo se
dibuja**:

- 🎨 Lienzo claro y suave con acentos cian/violeta (87,7% de píxeles claros, ~74% blanco,
  textos oscuros legibles → tema claro accesible).
- 🔮 Título: "Pronóstico de Ventas · Retail".
- 📅 Subtítulo dinámico: "**Datos reales hasta el 23/12/2015 · Pronóstico 8 días: 24/12 →
  31/12/2015**" ← ¡la fecha de cierre que querías, y se actualiza sola!
- 💰 KPI: ventas predichas (~3 mil), ritmo predicho 378,3, ritmo real 458,1, variación **-17,4%**.
- 🤖 Panel de insights: producto estrella, tienda líder (CA_3, 81,2%), día pico (27/12, 488 uds.),
  ritmo a la baja.
- 🧮 Matriz producto × día, ⚖️ barras de peso por producto y 🏪 dona de reparto por tienda.
- 🎛️ Filtros arriba a la derecha: Tienda, Producto y Fecha.

---

## 5. Glosario rápido

- **`.pbix`** — El archivo de Power BI Desktop (datos + modelo + diseño). Por dentro es un ZIP.
- **PBIR / formato mejorado** — El diseño del informe guardado como carpeta de archivos JSON.
- **JSON** — Formato de texto para estructurar datos; es lo que se editó para el diseño.
- **`SecurityBindings`** — El "precinto" del que habla esta historia.
- **Medida (DAX)** — Fórmula calculada por Power BI (p. ej. `Fecha_Cierre`).
- **MCP** — El "puente" para conectar con Power BI abierto y crear medidas sin tocar el ratón.
- **OCR** — Leer texto de una imagen; se usó para verificar la pantalla.

---

## 6. Moraleja

> Si algún día hay que editar un `.pbix` por fuera de Power BI: **derretir el lacre**
> (poner `SecurityBindings` a ceros) y **guardar desde Power BI** al final para que selle de nuevo.
> Y si Power BI dice "archivo dañado", desconfiar: puede ser simplemente el precinto.
