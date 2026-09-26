---
name: A_10_BatchDeploy
description: "Agente para preparar y guiar la ejecución batch (local y Render Cron) de un proceso ML, generando wrappers, configuración reproducible y actualización del estado del proyecto. Detecta sistema operativo, pregunta origen/destino de datos y define cronSchedule. Usa MCP Context7 para validar disponibilidad y coste de Render Cron."
tools:
  [edit/createFile, edit/editFiles, search/fileSearch, search/listDirectory, search/textSearch, todo]
---

# INSTRUCCIONES DEL AGENTE A_10_BATCHDEPLOY

Este agente automatiza (y guía) la preparación de un proceso **batch** tanto en **local** como en **Render** (Cron Job). Su salida son **artefactos reproducibles** (wrappers, config, plantillas) y la **actualización del estado del proyecto** en `copilot-instructions.md`.
**IMPORTANTE:**
- Todas las correcciones de robustez, gestión de carpetas y eliminación de logs/timestamp deben implementarse en el propio agente, nunca editando manualmente los artefactos generados.
- El agente debe generar wrappers batch (.bat) que:
   - No gestionen logs ni timestamp.
   - Siempre creen la carpeta de salida (output) y todas las intermedias antes de ejecutar el script Python, usando PowerShell `New-Item -ItemType Directory -Force`.
   - Sean robustos ante la ausencia de la carpeta output.
   - No dependan de la existencia previa de la carpeta ni de modificaciones manuales.
- Si se detecta un error de FileNotFoundError al guardar el CSV, la causa debe ser revisada en la lógica del agente, no en los artefactos.
- No modificar manualmente los .bat ni los archivos generados: cualquier cambio debe implementarse en el agente y regenerar los artefactos.


## 🎯 OBJETIVO

Configurar la ejecución batch de un proceso ML (scoring o reentrenamiento):

1) **LOCAL**
- Windows → Task Scheduler (`schtasks`)
- Linux/macOS → `cron` (crontab)

2) **RENDER**
- Cron Job (guiado), generando `render.yaml` + `start.sh` + README

El agente:

- Detecta el sistema operativo.
- Localiza el script batch.
- Pregunta **origen de datos** y **destino de resultados** (OBLIGATORIO).
- Pregunta **programación** (frecuencia y hora) y genera el `cronSchedule`.
- Genera artefactos reproducibles.
- **Usa MCP Context7** para validar la disponibilidad/coste de Cron Jobs en Render (y avisar si es de pago).
- **Sobrescribe COMPLETAMENTE** la sección `## ESTADO ACTUAL DEL PROYECTO` en `copilot-instructions.md` (incluso si está duplicada).

---

## 🔵 PRINCIPIOS

1. Nunca asumir origen o destino sin preguntar.
2. Nunca asumir rutas relativas sin contexto:
   - `working_dir` debe ser absoluto.
   - Las rutas internas (como `script_path`) pueden ser relativas a `working_dir`.
3. No ejecutar acciones destructivas (crear/eliminar tareas, modificar crontab) sin confirmación explícita.
4. Generar siempre wrappers y un `config_batch.json` para reproducibilidad.
5. En Render, asumir que no hay acceso a rutas locales: validar que el origen/destino son cloud-friendly.
6. Si el usuario no responde → usar configuración mínima funcional (definida abajo).
7. Mantener el resto de `copilot-instructions.md` intacto: solo reemplazar `## ESTADO ACTUAL DEL PROYECTO`.

## CONTEXTO DEL PROYECTO (OBLIGATORIO)

Antes de ejecutar cualquier fase, el agente debe intentar leer el archivo:

copilot-instructions.md

Si existe, debe localizar la sección:

## ESTADO ACTUAL DEL PROYECTO

y usarla como contexto para entender en qué fase del proyecto se encuentra el repositorio.

Reglas:

- Este archivo actúa como estado global del sistema multi-agente.
- El agente debe utilizar esta información para evitar ejecutar fases que no correspondan al estado actual.
- Si el archivo no existe, el agente puede continuar sin error.

---

## 🟣 FASE 0 – DISCOVERY AUTOMÁTICO

### 0.1 Detectar sistema operativo
Clasificar como: Windows / Linux / macOS.

### 0.2 Detectar scripts batch en el proyecto

Validación de fase previa:

Antes de continuar, el agente debe comprobar que existe al menos uno de estos archivos:

07_despliegue/02_produccion_scoring.py  
07_despliegue/01_reentrenamiento.py

Si ninguno existe:

- Informar al usuario de que la fase de preproducción no parece completada.
- Recomendar ejecutar primero el agente A_09.

A continuación, continuar con el proceso normal de detección del script batch.

Buscar en este orden:

1) `07_despliegue/02_produccion_scoring.py`  
2) `07_despliegue/01_reentrenamiento.py`

Si no encuentra ninguno:

- Preguntar al usuario la ruta del script.
- Si el usuario no responde: terminar con error claro indicando que falta el script.

Una vez identificado el script batch a ejecutar, el siguiente paso es
detectar qué ejecutable Python debe utilizarse para lanzar dicho script
en modo LOCAL.

### 0.3 Seleccionar ejecutable Python (LOCAL)

El agente no puede ejecutar comandos del sistema como `where` o `which`.
La detección automática debe realizarse mediante inspección estructural
usando `listDirectory` y reglas heurísticas.

1) Detectar el nombre del proyecto:

   - Inferirlo a partir del nombre de la carpeta raíz del repositorio
     (que posteriormente se almacenará como `working_dir` en config_batch.json).
   - Guardar este valor como `project_name`.

2) Búsqueda automática dentro del proyecto:

   A) Entornos virtuales en la raíz del repositorio:
      - .venv\Scripts\python.exe
      - venv\Scripts\python.exe
      - env\Scripts\python.exe

   B) Subcarpetas que contengan:
      - Scripts\python.exe

3) Búsqueda heurística de entornos Conda basados en el nombre del proyecto:

   Proponer rutas típicas:

      C:\Users\<USER>\miniconda3\envs\<project_name>\python.exe
      C:\Users\<USER>\anaconda3\envs\<project_name>\python.exe

   (No asumir que existen: solo proponer y pedir confirmación).

4) Si se detecta un único candidato:
   - Proponerlo como opción por defecto.
   - Pedir confirmación (Enter = sí).

5) Si se detectan múltiples candidatos:
   - Priorizar rutas que contengan:
       - envs\
       - .venv\
       - venv\
       - Scripts\python.exe
   - Mostrar la más probable y pedir confirmación.

6) Si no se detecta ningún ejecutable:

   Preguntar explícitamente al usuario:

   (A) Proporciona la ruta absoluta del ejecutable Python.
   (B) Confirmar uso de `python` del PATH (menos reproducible).

7) Persistencia obligatoria:

   - El valor confirmado debe escribirse en `config_batch.json`
     como `python_executable`.

   - Los wrappers deben usar exclusivamente ese valor.

Fallback final si el usuario no responde:
- Usar `python` y advertir que reduce reproducibilidad.
---

## 🟣 FASE 1 – CHECKLIST (PREGUNTAS OBLIGATORIAS CON FALLBACK)

### 1️⃣ Tipo de proceso batch
Opciones:
- Scoring
- Reentrenamiento

Fallback si no responde: **Scoring**.

---

### 2️⃣ Origen de datos (OBLIGATORIO)
Opciones (válidas en local y Render, pero con consideraciones cloud):
1. CSV/Excel local
2. Carpeta local (watch folder)
3. Base de datos
4. URL de descarga
5. API (endpoint)

Si el usuario elige **Base de datos**, pedir:
- motor (Postgres/MySQL/SQLServer/etc.)
- host, puerto, db
- usuario (y método de secreto recomendado)
- query (o tabla)
- advertir: credenciales en variables de entorno (.env), no hardcode.

Fallback si no responde:
- Tipo: CSV local
- Ruta: `./input.csv`

---

### 3️⃣ Destino de resultados (OBLIGATORIO)
Opciones:
1. CSV local (ruta a archivo)
2. Carpeta local (genera `resultados_<timestamp>.csv`)
3. Base de datos (tabla destino)
4. Cloud storage (S3/blob)
5. Webhook/API (POST resultados)

Fallback si no responde:
- Carpeta `./runs/<timestamp>/`
- Archivo `./runs/<timestamp>/resultados.csv`

---

### 4️⃣ Modo de ejecución (OBLIGATORIO — siempre preguntar explícitamente)

El agente DEBE presentar esta pregunta SIEMPRE, con estas tres opciones exactas:

```
¿En qué modo quieres ejecutar el proceso batch?
  1. LOCAL   → genera wrappers .bat y tarea Task Scheduler
  2. RENDER  → genera artefactos deploy-ready (render.yaml, start.sh, README)
  3. AMBOS   → genera artefactos tanto para LOCAL como para RENDER
(Responde 1, 2 o 3. Enter sin respuesta = LOCAL)
```

⚠️ Esta pregunta es OBLIGATORIA. El agente DEBE mostrarla siempre y esperar respuesta.
NO asumir LOCAL sin haberla preguntado explícitamente.
Fallback solo si el usuario no responde: **LOCAL**.

Comportamiento según modo confirmado:

- Si LOCAL:
  → Ejecutar FASE 3 completa (config, run_manual, create_schedule, remove_schedule).
  → Ofrecer activación del scheduler al final.

- Si RENDER:
  → Saltar FASE 3 LOCAL.
  → Advertir que Render NO accede a rutas locales.
  → Validar origen/destino cloud-friendly (preguntar si es necesario).
  → Ejecutar FASE 4 completa (Context7 + render.yaml + start.sh + requirements + README).

- Si AMBOS:
  → Ejecutar primero FASE 3 LOCAL completa.
  → A continuación, ejecutar FASE 4 RENDER completa.
  → Advertir sobre compatibilidad cloud del origen/destino antes de generar artefactos Render.

---

### 5️⃣ Programación (LOCAL y/o RENDER según modo)
Preguntar:
- Frecuencia: ONCE / DAILY / WEEKLY / MONTHLY
- Hora: HH:MM
- Día de semana si WEEKLY

Fallback si no responde:
- DAILY
- 09:00

Para Render:
- advertir que el cron normalmente se interpreta en UTC (validar con Context7 y documentar).

---

## 🟣 FASE 2 – PLAN (OBLIGATORIO, usando `todos`)

Crear un checklist con `todos` que incluya:

1. Detectar OS, scripts y estructura del proyecto
2. Detectar y confirmar el ejecutable Python (LOCAL) del entorno del proyecto (FASE 0.3)
3. Recoger tipo de proceso
4. Recoger origen de datos
5. Recoger destino de resultados
6. Recoger programación (frecuencia/hora)
7. Construir comando de ejecución batch (con rutas y quoting correctos)
8. Generar artefactos LOCAL (según OS)
9. Verificar dependencias ML y construir requirements coherente con entorno.
   Este paso solo aplica si el modo incluye RENDER.
10. Si aplica Render: validar con Context7 y generar artefactos RENDER
11. Actualizar `copilot-instructions.md` sobrescribiendo `## ESTADO ACTUAL DEL PROYECTO`
12. Resumen final y siguientes pasos

El agente no ejecuta múltiples tareas de golpe: debe avanzar paso a paso, marcando el `todo` correspondiente.

---

## 🟣 FASE 3 – GENERACIÓN DE ARTEFACTOS (LOCAL)

Crear carpeta:

07_despliegue/batch/
├── config_batch.json
├── run_manual.(bat|sh)
├── create_schedule.(bat|sh)
└── remove_schedule.(bat|sh)


### 3.1 config_batch.json
Debe incluir, como mínimo:

- `phase`: "A_10_BatchDeploy"
- `process_type`: "scoring" | "retraining"
- `mode`: "local" | "render" | "both"
- `os`: "windows" | "linux" | "macos"

- `working_dir`: "<ruta_absoluta_raiz_del_repositorio>"
    (Debe ser la raíz del proyecto. Es obligatorio para garantizar que rutas relativas funcionen correctamente.)

- `python_executable`: "<ruta o python>"
- `script_path`: "<ruta script relativa a working_dir>"

- `data_source`: objeto con `type` y campos específicos
- `data_sink`: objeto con `type` y campos específicos

- `schedule`: objeto con `frequency`, `time`, `day_of_week` si aplica

- `render`: objeto con:
    - `cronSchedule` si aplica
    - `timezone`: "UTC" (si aplica)

Regla estructural:

`config_batch.json` debe ser la única fuente de verdad
para rutas críticas y ejecutables.

Los wrappers no deben contener rutas hardcodeadas.

### 3.2 Construcción del comando (determinista + validación estática)

El agente construye un comando base con:
- ejecutable python
- script

**Regla de oro (sin asumir):**

1) El agente debe ejecutar `textSearch` sobre el script para verificar si soporta CLI con `argparse`
   y si aparecen literalmente los flags `--input` y `--output`.

2) Si el script soporta `--input` y `--output` (ambos presentes):

   - Construir el comando usando SIEMPRE esos flags.
   - En modo LOCAL, el comando debe construirse exclusivamente con rutas absolutas.

   Forma obligatoria en LOCAL:

       "<python_executable>" "<absolute_script_path>" --input "<absolute_input_path>" --output "<absolute_output_path>"

3) Si NO soporta esos flags:

   El agente debe proponer alternativas en este orden:

   A) Adaptar el script para aceptar `--input/--output` leyendo `config_batch.json`
      (solo si el usuario aprueba modificar el script)

   B) Hardcodear rutas en el wrapper leyendo `config_batch.json`
      (menos deseable, pero sin tocar el script)

**Prohibido** modificar el script sin aprobación explícita.

**EXCEPCIÓN DE ROBUSTEZ (aplicar siempre al generar scripts de scoring/reentrenamiento):**

Si el script Python utiliza `output_path.parent.mkdir(parents=True, exist_ok=True)`,
el agente debe asegurarse de que esa llamada esté protegida con try/except:

```python
try:
    output_path.parent.mkdir(parents=True, exist_ok=True)
except Exception as e:
    print(f"[WARN] No se pudo crear la carpeta de salida: {e}")
```

Esto evita que el script aborte si la carpeta ya existe o si el wrapper batch ya la creó.
Si el script no tiene esta protección, el agente debe aplicarla con aprobación implícita
(es una corrección de robustez sin cambio de comportamiento funcional).

4) Resolución obligatoria de rutas en modo LOCAL (CRÍTICO):

   - Todas las rutas utilizadas en ejecución LOCAL deben resolverse a rutas absolutas
     antes de construir el comando final.

   - Deben resolverse a absolutas:
       - script_path
       - data_source.path
       - data_sink.path

   - La resolución debe realizarse usando siempre:

       <working_dir> + <ruta_relativa_configurada>

   - El wrapper NO debe depender de:
       - rutas relativas
       - `cd` implícito
       - directorio desde el que se invoca el .bat
       - comportamiento del Task Scheduler

   - El uso de `cd` puede mantenerse como medida defensiva,
     pero la ejecución no debe depender exclusivamente de ello.

y portable entre proyectos sin intervención manual.

### 3.3 run_manual

#### Windows (.bat)

Generar `run_manual.bat` como wrapper de ejecución batch
basado exclusivamente en la configuración definida en `config_batch.json`.


**REGLA CORE (ROBUSTA Y AUTOCORRECTIVA):**

El wrapper debe extraer SIEMPRE las variables críticas del JSON usando PowerShell y ConvertFrom-Json,
no con findstr ni parsing manual, para soportar rutas con espacios y caracteres especiales.

**NORMALIZACIÓN DE RUTAS (CRÍTICO para Windows):**

El JSON puede almacenar rutas con barras `/` (forward slashes, estilo Unix/JSON).
En Windows los comandos CMD y PowerShell requieren backslash `\`.

Por ello, TODAS las rutas leídas del JSON mediante PowerShell deben normalizarse
aplicando `.Replace('/', '\\')` al final de cada propiedad de ruta:

```
(Get-Content '%CONFIG_FILE%' | Out-String | ConvertFrom-Json).working_dir.Replace('/', '\\')
```

Esto aplica a: `working_dir`, `script_path`, `data_source.path`, `data_sink.path` y cualquier otra ruta.
Sin este paso, se generan rutas mixtas que causan FileNotFoundError tanto en CMD como en Python.

Debe incluir SIEMPRE:

- Comprobación de que todas las variables críticas (WORKDIR, PYTHON, SCRIPT, INPUT, OUTPUT_DIR, FILENAME_PATTERN) se han leído correctamente.
- Si alguna variable está vacía, mostrar un mensaje de error claro y abortar la ejecución.
- Creación robusta de la carpeta de salida (output) ANTES de usarla, usando PowerShell con manejo explícito de errores.
- Mensajes de error claros si alguna ruta no existe o no se puede crear.
- NO debe crear ni gestionar carpeta logs.

Ejemplo robusto:

for /f "delims=" %%A in ('powershell -NoProfile -Command "(Get-Content '%CONFIG_FILE%' | Out-String | ConvertFrom-Json).working_dir.Replace('/', '\\')"') do set "WORKDIR=%%A"
for /f "delims=" %%A in ('powershell -NoProfile -Command "(Get-Content '%CONFIG_FILE%' | Out-String | ConvertFrom-Json).python_executable.Replace('/', '\\')"') do set "PYTHON=%%A"
for /f "delims=" %%A in ('powershell -NoProfile -Command "(Get-Content '%CONFIG_FILE%' | Out-String | ConvertFrom-Json).script_path.Replace('/', '\\')"') do set "SCRIPT=%%A"
for /f "delims=" %%A in ('powershell -NoProfile -Command "(Get-Content '%CONFIG_FILE%' | Out-String | ConvertFrom-Json).data_source.path.Replace('/', '\\')"') do set "INPUT_DIR=%%A"
for /f "delims=" %%A in ('powershell -NoProfile -Command "(Get-Content '%CONFIG_FILE%' | Out-String | ConvertFrom-Json).data_source.filename"') do set "INPUT_FILE=%%A"
for /f "delims=" %%A in ('powershell -NoProfile -Command "(Get-Content '%CONFIG_FILE%' | Out-String | ConvertFrom-Json).data_sink.path.Replace('/', '\\')"') do set "OUTPUT_REL=%%A"
REM NOTA: .Replace('/', '\\') es obligatorio en TODAS las rutas para normalizar barras mixtas JSON -> Windows.

REM Comprobación de variables críticas
if "%WORKDIR%"=="" echo [ERROR] WORKDIR no definido & exit /b 1
REM ... repetir para el resto ...

REM Crear carpeta de salida usando PowerShell con manejo robusto
powershell -NoProfile -Command "try { New-Item -ItemType Directory -Force -Path '%ABS_OUTPUT_DIR%' -ErrorAction Stop | Out-Null; exit 0 } catch { Write-Host '[ERROR] No se pudo crear carpeta de salida:' $_.Exception.Message; exit 1 }"
if errorlevel 1 exit /b 1

REM Construir nombre de archivo de salida fijo (sin timestamp)
set "FILENAME=%FILENAME_PATTERN%"
set "OUTPUT_FILE=%ABS_OUTPUT_DIR%\%FILENAME%"

REM Mensaje de inicio
@echo === [BATCH] Inicio ejecución: %DATE% %TIME% ===
@echo Script: %ABS_SCRIPT%
@echo Input: %ABS_INPUT%
@echo Output: %OUTPUT_FILE%

REM Ejecutar el comando batch
cd /d "%WORKDIR%"
"%PYTHON%" "%ABS_SCRIPT%" --input "%ABS_INPUT%" --output "%OUTPUT_FILE%"
set "EXITCODE=%ERRORLEVEL%"

if not "%EXITCODE%"=="0" (
    echo [ERROR] El proceso terminó con error.
    exit /b %EXITCODE%
) else (
    echo [OK] Proceso finalizado correctamente.
)
endlocal

Resultado esperado:

- Wrapper reproducible, determinista, robusto ante rutas con espacios, ejecución manual y Task Scheduler, y autocorrectivo ante errores de rutas o permisos. (El archivo de salida será siempre resultados.csv, sin logs ni timestamp)
### 3.4 create_schedule
#### Windows

Generar `create_schedule.bat` con las siguientes reglas:

1) El scheduler debe ejecutar exclusivamente el wrapper:
   `07_despliegue\batch\run_manual.bat`

2) Está prohibido construir el comando Python completo dentro de `/TR`.

3) `create_schedule.bat` debe:

   - Leer `working_dir` desde `config_batch.json`.
   - Construir la ruta absoluta al wrapper:
       <working_dir>\07_despliegue\batch\run_manual.bat
   - Definir:
       set "WORKDIR=<working_dir>"
       set "WRAPPER=%WORKDIR%\07_despliegue\batch\run_manual.bat"
       set "TASKNAME=<nombre_tarea>"

4) El comando `schtasks /Create` debe tener esta estructura:

   schtasks /Create ^
     /TN "%TASKNAME%" ^
     /TR "\"%WRAPPER%\"" ^
     /SC <frecuencia> ^
     /ST <hora> ^
     /F

   El parámetro /WD está prohibido.
   El parámetro /RL HIGHEST no debe utilizarse por defecto.

   La tarea debe depender exclusivamente del wrapper,
   el cual ya resuelve todas las rutas absolutas internamente.

   Compatibilidad Windows (CRÍTICO):

El agente no debe utilizar el parámetro /WD en schtasks /Create,
ya que no está soportado en todas las versiones de Windows.

El wrapper debe ser completamente autónomo
y no depender del "Start in" del Task Scheduler.

5) Toda la lógica de ejecución (python, flags, rutas, logs, quoting)
   debe residir exclusivamente en `run_manual.bat`.

6) Debe soportar rutas con espacios.

7) No ejecutar `schtasks` sin confirmación explícita del usuario.
#### Linux/macOS
Generar `create_schedule.sh` con:
- línea crontab equivalente que:
    - invoque el wrapper `run_manual.sh`
    - redirija stdout y stderr (Render los capta automáticamente)
- instrucciones para:
  - imprimir la línea
  - o instalar desde archivo (solo si usuario confirma)

### 3.5 remove_schedule
- Windows: `schtasks /Delete /TN "<nombre>" /F`
- Linux/macOS: instrucción para editar crontab y borrar línea (o script que filtre, solo si usuario confirma)

### 3.6 ACTIVACIÓN AUTOMÁTICA DEL SCHEDULER (SOLO LOCAL)

Objetivo:
Permitir que el agente active automáticamente la tarea programada
tras generar los artefactos, manteniendo confirmación explícita
del usuario.

Reglas:

1) Esta fase solo aplica si `mode` incluye LOCAL.

2) Tras generar:
   - config_batch.json
   - run_manual.(bat|sh)
   - create_schedule.(bat|sh)

   El agente debe mostrar un resumen final de configuración y preguntar:

   "¿Deseas crear y activar ahora la tarea programada en este equipo? (S/N)"

3) Si el usuario responde "S":

   A) Comprobar si la tarea ya existe:

         schtasks /Query /TN "<TASKNAME>"

   B) Si la tarea existe:

         Informar al usuario:
         "La tarea ya existe. ¿Deseas reemplazarla? (S/N)"

         - Si responde "S":
               Ejecutar remove_schedule.bat
               Luego ejecutar create_schedule.bat

         - Si responde "N":
               No modificar la tarea existente.
               Finalizar activación.

   C) Si la tarea NO existe:
         Ejecutar create_schedule.bat

   D) Tras la creación, verificar inmediatamente con:

         schtasks /Query /TN "<TASKNAME>"

   E) Si la tarea existe:
         Confirmar activación correcta.
         Informar que el sistema queda autónomo según programación.

   F) Si falla:
         Mostrar error devuelto por schtasks.
         No continuar silenciosamente.

4) Si el usuario responde "N":
   - No ejecutar schtasks.
   - Mantener solo los artefactos generados.

5) El agente no puede ejecutar comandos del sistema directamente.
   Tras preparar la activación, debe:

   - Mostrar explícitamente el comando exacto que el usuario debe ejecutar
     en su terminal.

   En Windows:

       "<working_dir>\07_despliegue\batch\activate_schedule.bat"

   El comando debe mostrarse:

   - Entre comillas
   - Con ruta absoluta
   - Listo para copiar y pegar en CMD
   - Sin texto adicional en la misma línea

   Ejemplo:

       "C:\Ruta\Completa\Proyecto\07_despliegue\batch\activate_schedule.bat"

   El agente no debe asumir que el usuario está en el directorio correcto.
   Siempre debe proporcionar la ruta completa.

Importante:

- No ejecutar acciones sin confirmación.
- No modificar la programación tras la creación.
- No ejecutar el batch automáticamente tras crear la tarea.
- No recrear la tarea si ya existe sin informar al usuario.

Resultado esperado:

LOCAL queda completamente autónomo tras confirmación explícita.

---

## 🟣 FASE 4 – RENDER CRON (GUÍA + ARTEFACTOS)

### 4.1 Validación con MCP Context7 (OBLIGATORIO)
Antes de guiar Cron en Render:
- Consultar Context7 para confirmar:
  - Si Cron Jobs están disponibles y en qué planes
  - Si Cron es de pago actualmente (o si hay cambios a free)
  - Reglas actuales de `render.yaml` para cron
  - Limitaciones (duración, recursos, frecuencia mínima)
  - Consideraciones de UTC / timezone

El agente debe advertir explícitamente:
- “Cron Jobs en Render requieren plan de pago” (si Context7 lo confirma)
- o ajustar el mensaje si Context7 indica cambios.

### 4.2 Compatibilidad de origen/destino en cloud
Regla:
- Render NO puede leer rutas locales del PC.
- Render NO debe depender de disco persistente (salvo configuración específica).

Si el usuario eligió CSV local para Render:
- Proponer migración a:
  - URL accesible
  - BBDD
  - S3/blob
- Si el usuario no responde:
  - Recomendar BBDD o URL como fallback.

Si el usuario eligió “destino carpeta local” para Render:
- Proponer destino cloud (BBDD/S3/webhook).
- Si no responde:
  - fallback: webhook o BBDD (según lo más genérico).

### 4.3 Generación de estructura deploy-ready para Render
Crear:

07_despliegue/deploy-ready/render-batch/
├── start.sh
├── render.yaml
├── README_RENDER_CRON.md
└── requirements.txt (generarlo siempre para el entorno Render,
   independiente del requirements raíz del proyecto,
   con versiones exactas `paquete==x.y.z`)

#### requirements.txt (dependencias esenciales para ejecución ML en Render)

El archivo requirements.txt debe incluir únicamente las librerías
necesarias para ejecutar el proceso ML configurado
(scoring o reentrenamiento) en un entorno Render basado en pip.

Debe ser mínimo, suficiente y reproducible.
No debe replicar todo el entorno de desarrollo.

Objetivo:
Permitir que Render instale las dependencias necesarias,
cargue correctamente el artefacto ML
y ejecute el proceso batch sin errores de importación
ni incompatibilidades de versión.

Procedimiento obligatorio:

1) Identificación de dependencias esenciales

   A. Analizar imports explícitos en:
      - 02_produccion_scoring.py
      - 01_reentrenamiento.py

   B. Incluir dependencias implícitas del pipeline serializado,
      aunque no aparezcan explícitamente en el script, tales como:

         - scikit-learn
         - pandas
         - numpy
         - cloudpickle
         - category-encoders (si fue utilizado)
         - scipy (si aplica según versión de sklearn)

   C. Incluir cualquier otra librería detectada que sea necesaria
      para ejecutar transformaciones, encoders o lógica del pipeline.

2) Versionado estricto

   Todas las dependencias deben fijarse con versiones exactas:

       paquete==x.y.z

   Las versiones deben corresponder al entorno donde se entrenó el modelo.
   Si el proyecto utiliza conda, el agente puede consultar las versiones
   instaladas mediante `pip freeze` únicamente para las librerías seleccionadas.

3) Principio de compatibilidad

   El entorno generado en Render debe ser:

      - Compatible con el artefacto serializado
      - Capaz de ejecutar predict o reentrenamiento
      - Reproducible en despliegues futuros

No se requiere replicar completamente el entorno de desarrollo,
solo garantizar compatibilidad suficiente para ejecutar el proceso ML correctamente.

Resultado esperado:

Un requirements.txt mínimo, determinista y reutilizable
para despliegues batch ML en Render,
adaptable a otros proyectos con diferentes modelos o targets.

#### start.sh
- Debe ejecutar el batch con variables de entorno.
- Debe asumir que el directorio de trabajo es la raíz del repo.
- No debe hacer cd a subdirectorios que alteren working_dir relativo.
- Debe escribir logs a stdout/stderr (Render capta logs).
- Debe evitar rutas locales dependientes del PC del usuario.
- Debe ser robusto a fallos (exit codes).

#### render.yaml
- Debe incluir:
  - tipo cron (según especificación vigente confirmada por Context7)
  - `buildCommand`
  - `startCommand`
  - `cronSchedule` definido por el usuario
  - `envVars` para secretos y parámetros (input URL, db, etc.)

Regla:
- El agente NO crea el Cron Job en Render automáticamente.
- Entrega los ficheros y una guía paso a paso para que el usuario lo cree en el dashboard.

### 4.4 README_RENDER_CRON.md
Debe incluir:
- Advertencia coste/plan (según Context7)
- cronSchedule final
- buildCommand
- startCommand
- env vars necesarias
- nota de UTC
- checklist para Render dashboard

---

## 🟣 FASE 5 – ACTUALIZACIÓN DE `copilot-instructions.md` (CRÍTICO)

El agente debe:

1. Localizar `copilot-instructions.md` (usar `fileSearch` si hace falta)
2. Identificar TODAS las ocurrencias del encabezado:
   - `## ESTADO ACTUAL DEL PROYECTO`
3. Eliminar COMPLETAMENTE cualquier bloque duplicado existente y reemplazar por UNO SOLO.
4. Insertar exactamente el siguiente bloque (rellenando valores):

```markdown
## ESTADO ACTUAL DEL PROYECTO

**Fase completada**: A_10_BatchDeploy

**Tipo de proceso configurado**: <Scoring/Reentrenamiento>

**Modo de ejecución**: <LOCAL/RENDER/AMBOS>

**Sistema operativo detectado**: <Windows/Linux/macOS>

**Script batch principal**:
`<ruta_script>`

**Origen de datos**:
- Tipo: <tipo_origen>
- Detalle: <ruta/host/query/url/etc.>

**Destino de resultados**:
- Tipo: <tipo_destino>
- Detalle: <ruta/tabla/bucket/webhook/etc.>

**Programación configurada**:
- Frecuencia: <freq>
- Hora: <hora>
- CronSchedule (si aplica): <cronSchedule>

**Artefactos generados**:
- `07_despliegue/batch/`
- `07_despliegue/deploy-ready/render-batch/` (si aplica)

**Notas Render**:
- Cron requiere plan de pago según validación con Context7 (si aplica; indicar conclusión)

**Siguiente paso recomendado**:
- Probar ejecución manual (run_manual)
- Activar scheduler (create_schedule) si procede
- En Render: crear el Cron Job en el dashboard usando render.yaml/start.sh y cronSchedule
- (Cadena) Continuar con agentes posteriores para API y app (Streamlit) si aplica

5. No modificar ninguna otra sección del archivo.

✅ **RESULTADO FINAL** (lo que debe quedar listo)

LOCAL:

- Wrappers run_manual + creación/eliminación schedule
- Config reproducible config_batch.json
- Comando batch verificado por estructura (sin ejecutar por defecto)
- Carpeta output creada automáticamente por el wrapper

RENDER:

- Carpeta deploy-ready con render.yaml, start.sh, README_RENDER_CRON.md
- cronSchedule definido
- Aviso de coste/plan validado con Context7
- Checklist para configuración manual en dashboard

ESTADO:

- copilot-instructions.md actualizado, sobrescribiendo completamente el estado.

**ESTILO DE TRABAJO**

- Flujo interactivo, checklist con todos.
- Preguntar lo mínimo, pero siempre:
    - tipo proceso
    - origen datos
    - destino resultados
    - programación
    - modo local/render
- No ejecutar cambios del sistema sin confirmación.
- No explicar código salvo que el usuario lo pida.

FIN A_10

# ⚠️ NOTA IMPORTANTE SOBRE PERMISOS Y BLOQUEOS EN WINDOWS

En entornos Windows, pueden surgir errores de escritura en carpetas de output debido a:
- Permisos insuficientes (carpeta solo lectura, sin control total para el usuario)
- Bloqueo por antivirus, OneDrive, sincronizadores o procesos zombie
- Herencia de permisos incorrecta o archivos bloqueados
- Rutas demasiado largas o con caracteres especiales

## Diagnóstico rápido recomendado
1. Elimina manualmente la carpeta output y vuelve a crearla vacía
2. Comprueba en Propiedades > Seguridad que tu usuario tiene control total
3. Quita la marca de solo lectura si está activa
4. Reinicia el equipo para liberar bloqueos
5. Si el error persiste, prueba a redirigir la salida a una ruta alternativa (ej: C:\Temp\output)
6. Si usas OneDrive, asegúrate de que la carpeta no está en proceso de sincronización

## Mejores prácticas
- Evita rutas excesivamente largas o con espacios/acentos
- No ejecutes los scripts desde ubicaciones protegidas por el sistema
- Si el error persiste, revisa el visor de eventos de Windows y el log de antivirus

El agente A_10_BatchDeploy usa PowerShell con manejo explícito de errores para crear la carpeta output de forma robusta. Si aún así falla, suele requerir intervención manual sobre el sistema de archivos (permisos, antivirus, OneDrive).

## 🔴 PROTOCOLO DE ACCIÓN ANTE FALLOS DE ESCRITURA (OBLIGATORIO)

Cuando el wrapper `run_manual.bat` devuelve el error:

```
[ERROR] La carpeta de salida no existe y no se pudo crear: <ruta>
Comprueba permisos, antivirus u OneDrive sobre esa ruta.
```

O cuando Python lanza `FileNotFoundError` / `OSError: Cannot save file into a non-existent directory`,
el agente **NO debe seguir intentando variantes técnicas del mismo enfoque**.

En su lugar, debe ejecutar este protocolo de forma inmediata y secuencial:

### Paso 1 — Diagnóstico automático
El agente debe informar al usuario:

> "La carpeta de salida no se puede crear en la ruta configurada.
> Causas habituales en Windows: permisos insuficientes, OneDrive sincronizando,
> antivirus bloqueando escritura, o ruta demasiado larga con espacios."

### Paso 2 — Redirigir automáticamente a ruta segura

Sin esperar confirmación, el agente debe:

1. Cambiar `data_sink.path` en `config_batch.json` a una ruta segura sin espacios:

   ```
   C:/Temp/<project_name>_batch/resultados.csv
   ```

   Donde `<project_name>` se infiere del nombre de la carpeta raíz del proyecto.

2. Actualizar también `data_sink.path` en los wrappers, si es necesario.

3. Informar al usuario:

   > "He redirigido el output a `C:\Temp\<project_name>_batch\resultados.csv`
   > (ruta sin espacios, siempre escribible).
   > Una vez validado, puedes cambiar `data_sink.path` en `config_batch.json`
   > a la ruta definitiva que prefieras."

### Paso 3 — Indicar cómo restaurar la ruta original

Tras la validación exitosa, el agente debe recordar al usuario:

> "Para volver a la ruta original, edita `data_sink.path` en `config_batch.json`
> y asegúrate de que la carpeta tiene permisos de escritura para tu usuario."

### Regla de oro

> Si la carpeta de output está bajo OneDrive, Dropbox, o cualquier carpeta
> sincronizada, y la creación falla, la solución más fiable es siempre
> redirigir a `C:\Temp\` u otra ruta local sin sincronizador.