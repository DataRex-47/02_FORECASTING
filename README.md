# Forecasting Retail

## Objetivo de negocio
_(Qué problema de negocio resuelve, no qué modelo usa)_

## Estructura
| Carpeta | Contenido |
|---|---|
| `01_Documentos/` | Documentación, briefings, actas |
| `02_datos/` | Originales · Validación · Entrenamiento · Cachés |
| `03_notebooks/` | Pipeline de análisis, numerado por fases |
| `04_scripts/` | Código reutilizable y de producción |
| `05_modelos/` | Modelos serializados (.pkl / .joblib) |
| `06_resultados/` | Salidas, gráficos y entregables |
| `07_despliegue/` | API, app o proceso batch |

## Puesta en marcha
```bash
uv sync                                    # reproduce el entorno exacto
uv run jupyter lab                         # abrir los notebooks
uv run python 04_scripts/<archivo>.py      # ejecutar un script
```
