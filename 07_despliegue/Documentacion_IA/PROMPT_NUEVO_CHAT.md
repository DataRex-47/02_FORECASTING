# 🤖 PROMPT LISTO PARA PEGAR EN UN CHAT NUEVO

> Copia todo el bloque de abajo y pégalo como primer mensaje en el chat nuevo.

---

## ✂️ COPIAR DESDE AQUÍ

Hola. Estoy trabajando en el proyecto **`02_FORECASTING`** (forecasting de ventas retail, 20 modelos
LightGBM tienda × producto). Ya tengo funcionando un tablero de Power BI (`Tablero_Ventas_v2_DisenoIA.pbix`)
y ahora quiero **una SEGUNDA PÁGINA** en ese mismo tablero.

**ANTES DE HACER NADA, lee estos archivos en este orden:**

1. `07_despliegue/Documentacion_IA/CONTEXTO_TABLERO_Y_ERRORES.md`
   → Modelo semántico, las 20 medidas con su DAX, cómo está montado el informe, el sistema de
   diseño visual (paleta, tarjetas, tipografía), el flujo para modificar el `.pbix` y **la bitácora
   de errores ya resueltos (leerla evita romper el archivo)**.
2. `07_despliegue/Documentacion_IA/EL_MISTERIO_DEL_PBIX.md`
   → La historia de por qué un `.pbix` modificado por fuera "no abre" (SecurityBindings). Lectura
   obligatoria antes de tocar el archivo.
3. `07_despliegue/instrucciones/explicacion.md`
   → Cómo funciona la carpeta 07_despliegue (scripts, CSV de entrada, predicciones).
4. La sección **"ESTADO ACTUAL DEL PROYECTO"** de `.github/copilot-instructions.md`.

**Reglas del proyecto (obligatorias):**
- Entorno con **UV** (`uv add`, `uv run python 04_scripts/<archivo>.py`). Nunca `pip install`.
- Bucles `for` tradicionales (nada de comprehensions ni lambdas para lógica).
- Rutas con `pathlib`, nunca concatenando strings.
- Comentarios de sección con el formato `# ── Título ─────────`.
- Antes de escribir funciones de análisis, revisar `04_scripts/utils.py` (catálogo del vault).
- `02_datos/01_Originales/` es de solo lectura.
- Responder siempre en español.

**Reglas críticas para este tablero (aprendidas a la mala):**
- El `.pbix` **no se edita con Power BI abierto**: primero se cierra Power BI, se modifica el archivo
  y luego se vuelve a abrir para verificar.
- Al reempaquetar el `.pbix` hay que **neutralizar `SecurityBindings`** (ponerlo a ceros del mismo
  tamaño) o Power BI dirá "archivo dañado o versión no reconocida". Detalles en los docs 1 y 2.
- Los JSON del reporte se escriben **minificados, UTF-8 sin BOM y con saltos de línea LF**.
- Para verificar sin "ver" la pantalla: abrir el `.pbix` con `Start-Process` y comprobar el **título
  de la ventana** (`Sin título - Power BI Desktop` = falló), analizar píxeles de una captura y/o
  hacer **OCR** con el motor de Windows (ver doc 1, sección "Técnicas de verificación").
- El modelo tiene las medidas nuevas guardadas; puedes conectarte por el MCP
  `powerbi-authoring-local` (operation `ListLocalInstances` y luego `Connect`) para leer/crear medidas.

**Cómo quiero que trabajes (MUY IMPORTANTE — este es el reparto de tareas):**
- **Yo mando en el contenido**: yo decido qué medidas, campos y visuales van en la página 2, y voy
  añadiendo/cambiando cosas sobre la marcha. Tú NO inventes visuales ni medidas que yo no haya pedido.
- **Tú adaptas el diseño**: cada cosa que yo ponga debe quedar con el MISMO sistema visual de la
  página 1 (fondo claro azulado suave, tarjetas blancas con borde y esquinas redondeadas, título con emoji, tipografía,
  acentos de color, lienzo 1920×1080). La receta exacta está en el doc 1, sección
  **"Cómo adaptar el diseño a medidas/visuales nuevos"**.
- **Antes de construir**: léete el modelo por MCP (`measure_operations List` y `table_operations List`)
  y dime qué medidas/columnas reales vas a usar. Si algo que pido no existe, propónmelo y espera mi OK
  antes de crearlo (si te digo que sí, puedes crearlo por MCP).
- **No des nada por cerrado sin enseñármelo**: el trabajo se entrega cuando yo lo vea funcionando.

**Mi idea para la segunda página** (ajústala conmigo antes de construir):
> _(escribe aquí tu idea: p. ej. "detalle por tienda y producto", "comparación de los 20 modelos",
> "histórico real vs pronóstico por producto", "calidad del pronóstico"…)_

**Tarea:** aplícame el diseño de la página 1 a una **segunda página** (1920×1080, `FitToPage`) con lo
que yo te vaya diciendo: te iré pasando las medidas/campos que quiero y tú los colocas con el mismo
estilo, con los slicers que correspondan. Yo pondré o pediré las medidas que hagan falta; tú las
integras y **me muestras el resultado antes de dar nada por cerrado**.

## ✂️ HASTA AQUÍ

---

## 📎 Notas para Andrés (no hace falta pegarlas)

- Si quieres, en el hueco de la idea puedes dejar una frase simple, por ejemplo:
  *"quiero una página 2 con el detalle por producto y tienda, la comparación real vs predicho por
  producto y un panel de los productos con más riesgo"*.
- El chat nuevo necesitará que **Power BI Desktop esté abierto con el tablero** solo si va a usar el
  MCP para leer/crear medidas. Para editar el archivo, mejor cerrado.
- El tablero de trabajo es `Tablero_Ventas_v2_DisenoIA.pbix` (el único `.pbix` de `07_despliegue`).
  El diseño preliminar anterior quedó archivado en
  `99_otros/Diseno_Tablero_PBI/_Respaldos/Tablero_Ventas_original_2026-10-08.pbix`.
  Cuando el nuevo chat toque el archivo, que trabaje sobre una
  copia y te pida cerrar Power BI antes.
