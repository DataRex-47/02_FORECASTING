---
mode: agent
description: Crea la estructura completa de un proyecto de Machine Learning con entorno UV, dependencias, .gitignore, instrucciones de agente y notebooks del pipeline.
---

# OBJETIVO

Configurar desde cero un proyecto de Machine Learning en Python con estructura profesional, entorno gestionado con **UV** y el pipeline de notebooks listo para trabajar.

# REGLAS DE EJECUCIÓN

- Ejecuta los pasos **en orden**. Si un paso falla, **detente, muestra el error y corrígelo** antes de seguir.
- Usa siempre la **terminal integrada**, un comando cada vez, esperando a que termine.
- El **nombre del proyecto** es el nombre de la carpeta actual. Sustitúyelo donde aparezca `<nombre_proyecto>`.
- Si alguna dependencia no se puede instalar, **continúa con el resto** y deja un aviso al final indicando cuáles fallaron.
- Al terminar, imprime un **resumen** de lo creado y de lo que haya quedado pendiente.

---

## PASO 1 — VERIFICAR UV

```bash
uv --version
```

Si el comando falla, UV no está instalado. Instálalo y vuelve a verificar:

```bash
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

> Tras instalar puede hacer falta **abrir una terminal nueva** para que el PATH se actualice.

---

## PASO 2 — ESTRUCTURA DE CARPETAS

Crea esta estructura exacta:

```
01_Documentos/
02_datos/01_Originales/
02_datos/02_Validacion/
02_datos/03_Entrenamiento/
02_datos/04_Caches/
03_notebooks/
04_scripts/
05_modelos/
06_resultados/
07_despliegue/
99_otros/
.github/prompts/
.github/agents/
```

Añade un archivo vacío **`.gitkeep`** dentro de cada carpeta de datos, modelos y resultados. Sin él, Git no conserva carpetas vacías y la estructura se pierde al clonar.

---

## PASO 3 — ENTORNO Y DEPENDENCIAS CON UV

UV crea el entorno virtual y resuelve las dependencias en un solo flujo. **No uses `pip install` directamente** ni actives el entorno a mano: `uv` lo gestiona.

```bash
uv init --python 3.12
```

Esto genera `pyproject.toml` y `.python-version`. **Si crea un `main.py` o `hello.py` de ejemplo, bórralo.**

### 3.1 — Núcleo (siempre)

Lo que se usa en el 100% de los proyectos. Nada más.

```bash
uv add numpy pandas matplotlib seaborn scikit-learn pyjanitor python-dotenv joblib
```

```bash
uv add --dev jupyter ipykernel ruff
```

> `scipy` no hace falta pedirla: **viene como dependencia de scikit-learn**, así que ya la tienes.

### 3.2 — Bloques opcionales

**PREGUNTA al usuario qué bloques necesita** antes de instalar nada más. Instala solo los que confirme.

| Bloque | Comando | Cuándo lo necesitas |
|---|---|---|
| **A · Boosting** | `uv add xgboost lightgbm` | Vas a usar gradient boosting o comparar algoritmos entre sí. **Es el bloque más pesado con diferencia** |
| **B · Desbalanceo y encoding** | `uv add imbalanced-learn category_encoders` | Clasificación con clases desbalanceadas, o categóricas de alta cardinalidad (Target Encoding) |
| **C · Estadística y diagnóstico** | `uv add statsmodels yellowbrick` | Contrastes de hipótesis, supuestos de regresión, o el gráfico de umbrales de corte |
| **D · Datos externos** | `uv add sqlalchemy openpyxl requests` | Los datos vienen de base de datos, Excel o API. Si son solo CSV, no hace falta |
| **E · Visualización interactiva** | `uv add plotly` | Gráficos interactivos o dashboards |
| **F · Despliegue** | `uv add streamlit fastapi uvicorn` | Vas a montar una app o una API. **Casi nunca al empezar** |

> [!TIP] La regla: instala corto y añade cuando lo necesites
> **Con UV, añadir una librería después cuesta un `uv add` y unos segundos.** No hay ninguna ventaja en instalar por si acaso, y sí tres inconvenientes: más peso, más superficie de conflictos al resolver, y un `pyproject.toml` que no refleja lo que el proyecto usa de verdad.
>
> Instalar todo de entrada era una costumbre razonable con conda, donde añadir algo más tarde significaba esperar al solver y arriesgarse a romper el entorno. **Con UV esa razón ya no existe.**

> **Sobre el peso real:** una librería instalada y no importada **no ralentiza nada en ejecución** — Python solo carga lo que le pides. El coste es de disco e instalación. Y UV mantiene una **caché global con enlaces duros**, así que a partir del segundo proyecto que use `xgboost` no se vuelve a descargar ni ocupa espacio nuevo.

### 3.3 — Registrar el kernel de Jupyter

```bash
uv run python -m ipykernel install --user --name=<nombre_proyecto> --display-name "Python (<nombre_proyecto>)"
```

> **No instales `pathlib`**: forma parte de la librería estándar de Python desde la 3.4.

---

## PASO 4 — ARCHIVOS DE CONFIGURACIÓN

### 4.1 — `.gitignore` en la raíz

```gitignore
# Sistema
desktop.ini
Thumbs.db
.DS_Store

# Entornos y dependencias
.env
.venv/
venv/
__pycache__/
*.py[cod]

# Jupyter
.ipynb_checkpoints/

# Datos — se ignora el contenido pero se conserva la estructura
02_datos/**
!02_datos/**/
!02_datos/**/.gitkeep

# Modelos entrenados y artefactos
05_modelos/**
!05_modelos/.gitkeep
*.pkl
*.pickle
*.joblib

# Resultados y entregables
06_resultados/**
!06_resultados/.gitkeep

# Formatos de datos sueltos
*.csv
*.xlsx
*.parquet
*.feather
*.db
*.sqlite
*.duckdb

# Logs
*.log

# IDE
.vscode/
.idea/
```

> **`uv.lock` SÍ se versiona.** Es el archivo que garantiza que el entorno sea reproducible: no lo añadas al `.gitignore`.

### 4.2 — `.env` vacío en la raíz

Créalo vacío. Es donde irán credenciales y rutas sensibles, y ya está ignorado por Git.

### 4.3 — `.github/copilot-instructions.md`

```markdown
- Responde siempre en español.
- Comienza cada mensaje con el emoji 🤖
- Genera el código para el script o notebook abierto, nunca para la ventana interactiva, salvo que se indique lo contrario.
- La ventana interactiva solo se usa para verificar resultados o mensajes de error.
- No expliques el código salvo que se pida.

## Convenciones de este proyecto
- Entorno gestionado con **UV**. Para añadir una dependencia: `uv add <paquete>`. Nunca `pip install`.
- Para ejecutar cualquier script: `uv run python 04_scripts/<archivo>.py`
- **Bucles tradicionales** (`for` + `append`) en lugar de comprehensions y lambdas.
- Comentarios de sección con el formato `# ── Título ─────────`
- Rutas siempre con `pathlib`, nunca concatenando strings.
- Los datos crudos de `02_datos/01_Originales/` son de **solo lectura**: nunca se sobrescriben.
- **Funciones reutilizables**: antes de escribir una función de análisis, comprobar si ya existe en `04_scripts/utils.py`. Se importan: `from utils import frecuencias_cat`. No reescribir equivalentes. Las altas y los cambios los gestiona el agente `A_00_Bibliotecario`.
```

### 4.4 — `README.md` en la raíz

```markdown
# <nombre_proyecto>

## Objetivo de negocio
_(Qué problema de negocio resuelve, no qué modelo usa)_

## Estructura
| Carpeta | Contenido |
|---|---|
| `01_Documentos/` | Documentación, briefings, actas |
| `02_datos/` | Originales · Validación · Entrenamiento · Cachés |
| `03_notebooks/` | Pipeline de análisis, numerado por fases |
| `04_scripts/` | Código reutilizable y de producción, incluido `utils.py` |
| `05_modelos/` | Modelos serializados (.pkl / .joblib) |
| `06_resultados/` | Salidas, gráficos y entregables |
| `07_despliegue/` | API, app o proceso batch |

## Puesta en marcha
```bash
uv sync                                    # reproduce el entorno exacto
uv run jupyter lab                         # abrir los notebooks
uv run python 04_scripts/<archivo>.py      # ejecutar un script
```
```

### 4.5 — `04_scripts/utils.py` (el catálogo de funciones, importable)

El proyecto no arranca con `04_scripts/` vacío: arranca con las funciones que ya existen.
Así no se reescribe por cuarta vez la que agrupa categorías raras.

**De dónde sale:** de `00_CATALOGO_FUNCIONES.md` en el vault, que es la **fuente canónica**.
`utils.py` es código generado desde ese catálogo, nunca al revés.

1. Copia el `utils.py` del último proyecto a `04_scripts/`. Si no hay ninguno a mano,
   se genera extrayendo los bloques de código del catálogo, sección por sección.
2. Copia también `A_00_Bibliotecario.agent.md` a `.github/agents/`. Es el agente que
   da de alta funciones nuevas y mantiene el catálogo y `utils.py` sincronizados.

**Cómo se usa** (desde un notebook de `03_notebooks/`):

```python
import sys
sys.path.append(str(RAIZ / '04_scripts'))

from utils import frecuencias_cat, graficos_eda_categoricos
```

> [!WARNING] La regla que evita el desastre silencioso
> Si editas `utils.py` en el proyecto y no devuelves el cambio al catálogo, cada
> proyecto acaba con su propia versión de la misma función y deja de haber una sola
> verdad. Todo cambio entra por el catálogo; `utils.py` se regenera.

> [!NOTE] Cuatro funciones del catálogo no son importables tal cual
> `limpiar_columnas_texto`, `ranking_mi`, `log` y `validar_schema` leen variables
> globales que en su origen venían del notebook (`BASURA`, `x`, `CONFIG`,
> `COLUMNAS_OBLIGATORIAS`). Están marcadas en la cabecera de `utils.py`. Funcionan en
> cuanto se les pasa esa variable por parámetro.


### 4.6 · Plantillas Excel de variables (`01_Documentos/`)

Son el mapa de qué proceso necesita cada variable (tipos, nulos, encoding, tiempo). Se rellenan durante el proyecto y se usan para refactorizar en la preproducción.

1. Copia las dos plantillas vacías del vault a `01_Documentos/`, quitándoles el prefijo `Plantilla_`:

```powershell
$V = "C:\Users\Admin\Desktop\Desktop\CarpetaFisica\Data Detective\Obsidian\Python & SQL\Python & SQL\Agentes_ML\Plantillas_Excel"
Copy-Item "$V\Plantilla_FaseDesarrollo_Transformaciones.xlsx" "01_Documentos\FaseDesarrollo_PlantillaTransformaciones.xlsx"
Copy-Item "$V\Plantilla_FaseProduccion_Procesos.xlsx" "01_Documentos\FaseProduccion_PlantillaProcesos.xlsx"
```

2. Copia también `A_00_Excelizador.agent.md` a `.github/agents/`. Es el agente que las rellena: la de desarrollo al cerrar la transformación y la de producción antes de la preproducción.
3. Si la ruta del vault no existe en esta máquina, avisa en el resumen final y sigue con el resto.
---

## PASO 5 — NOTEBOOKS DEL PIPELINE

Crea en `03_notebooks/` los siguientes archivos vacíos, que corresponden a las fases del pipeline:

```
01_Importacion_Datos.ipynb
02_Calidad_Datos.ipynb
03_EDA.ipynb
04_Transformacion_Datos.ipynb
05_Preseleccion_Variables.ipynb
06_Balanceo_Clases.ipynb
07_Modelizacion.ipynb
08_Preproduccion.ipynb
```

En **`01_Importacion_Datos.ipynb`** añade esta primera celda:

```python
# ── Librerías ─────────────────────────────────────────────────────────
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import janitor
import sqlalchemy as sa
import os
from pathlib import Path
from dotenv import load_dotenv

%matplotlib inline

# ── Opciones de visualización ─────────────────────────────────────────
# Desactivar notación científica
pd.set_option('display.float_format', '{:.3f}'.format)
np.set_printoptions(suppress=True)

# Ver todas las columnas al imprimir un DataFrame
pd.set_option('display.max_columns', None)

# ── Rutas del proyecto ────────────────────────────────────────────────
# Se resuelven desde la ubicación del notebook, así funcionan
# igual en cualquier máquina
RAIZ = Path.cwd().parent

ORIGINALES   = RAIZ / '02_datos' / '01_Originales'
VALIDACION   = RAIZ / '02_datos' / '02_Validacion'
ENTRENAMIENTO = RAIZ / '02_datos' / '03_Entrenamiento'
CACHES       = RAIZ / '02_datos' / '04_Caches'
MODELOS      = RAIZ / '05_modelos'
RESULTADOS   = RAIZ / '06_resultados'

# ── Variables de entorno ──────────────────────────────────────────────
load_dotenv(RAIZ / '.env')

print('✅ Entorno listo')
print(f'   Raíz del proyecto: {RAIZ}')
```

> `pd.set_option('display.float_format', '{:.3f}'.format)` sustituye a la versión con `lambda`: hace lo mismo y es más legible.

---

## PASO 6 — VERIFICACIÓN FINAL

Comprueba que todo funciona:

```bash
uv run python -c "import numpy, pandas, sklearn, janitor; print('✅ Núcleo correcto')"
```

Y que `utils.py` importa sin errores:

```bash
uv run python -c "import sys; sys.path.insert(0, '04_scripts'); import utils; print('✅ utils.py importa')"
```

Y comprueba **solo los bloques que se hayan instalado**. Por ejemplo, si se instaló el bloque A:

```bash
uv run python -c "import xgboost, lightgbm; print('✅ Bloque A correcto')"
```

Y muestra el resumen final con:

1. La estructura de carpetas creada.
2. El núcleo y **qué bloques opcionales** se instalaron, más cuáles fallaron si alguna.
3. El nombre del kernel de Jupyter registrado, y si `utils.py` importó correctamente.
4. Los siguientes pasos sugeridos: colocar los datos en `02_datos/01_Originales/` y abrir `03_notebooks/01_Importacion_Datos.ipynb`.
