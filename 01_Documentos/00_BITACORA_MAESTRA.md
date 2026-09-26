---
tags: [bitacora, forecasting, caso-ml, contexto]
aliases: [Bitácora Forecasting, Contexto del Proyecto 2]
date: 2026-09-24
updated: 2026-09-24
status: 🌱 (Seed)
---

# 🧭 Bitácora Maestra — Caso 2 · Forecasting Retail

> [!SUMMARY] Para qué sirve
> Reengancharte en 3 minutos y practicar sin releer los notebooks.
> Cada fase trae: pregunta de recall → qué pasó → qué quedó en disco → ⚙️ cómo se hizo → 🏋️ ejercicio.
> **El contexto del caso (negocio, jerarquía, reconciliación) no está aquí**: está en la nota del vault `Casos_ML/Caso_02_Forecasting_Retail.md`. Aquí solo va el seguimiento.

---

## 📍 Dónde estoy

**Arranque del proyecto — 24/09/2026.** Carpeta creada con la estructura estándar, notebooks 01→08 vacíos, PDF del caso leído y contexto documentado.

**Siguiente acción:** importación de datos (A_01) desde la base SQL con 3 años de histórico.

---

## 🔗 La cadena

```
A_01 Import ─► A_02 Calidad ─► A_03 EDA ─► A_04 Transform ─► A_05 Preselección ─► A_07 Modelo ─► A_08/A_09 Preproducción ─► A_10 Batch
   📍 AQUÍ         ⬜             ⬜            ⬜                  ⬜                 ⬜                  ⬜                      ⬜
```

**Diferencia con el caso 1:** aquí la salida no es una API, es un **proceso batch** que deja una tabla de predicciones a 8 días, y encima un tablero (Power BI, Tableau o Excel).

---

## 📊 Números del caso

| Dato | Valor |
|---|---|
| Histórico | 3 años |
| Horizonte a predecir | 8 días |
| Granularidad | tienda × producto × día |
| Alcance | 1 retailer · 1 categoría (alimentación) · 2 tiendas · 10 productos por tienda |
| Series a modelar | 20 (2 × 10) |

*(Se irá completando con métricas de error a medida que avancen las fases.)*

---

## 🧱 Los cuatro retos del caso — estado

| Reto | Dónde se resuelve | Estado |
|---|---|---|
| Forecasting jerárquico + reconciliación | Transformación / modelización | ⬜ |
| Demanda intermitente | Calidad + EDA (distinguir los dos tipos de cero) | ⬜ |
| Modelización masiva de SKU | Modelización | ⬜ |
| Horizonte a 8 días | Modelización (estrategia multi-horizonte) | ⬜ |

---

## 1️⃣ Importación · A_01 ⬜

*(Pendiente. Al cerrar el notebook: pregunta de recall → qué pasó → qué quedó en disco → ⚙️ cómo se hizo → 🏋️ practica.)*

---

## ⚠️ Deuda abierta

| # | Asunto | Estado |
|:--:|---|---|
| 1 | Decidir el nivel de modelización (bottom-up, top-down o híbrida) y por tanto el método de reconciliación | 🔵 por decidir |
| 2 | Definir cómo se distinguen los ceros de falta de demanda y los de rotura de stock | 🔵 por decidir |
| 3 | Elegir la métrica de error del proyecto (y si se mide por serie o agregada) | 🔵 por decidir |
| 4 | Decidir la herramienta del tablero final: Power BI, Tableau o Excel | 🔵 por decidir |

---

## 🔗 Conexiones

- **Contexto del caso** → `Casos_ML/Caso_02_Forecasting_Retail.md` (vault)
- PDF del caso → `01_Documentos/Forecasting Retail.pdf` · estructura de datos → `CasoRetail_EstructuraRelaciones.jpg`
- Agentes → `.github/`

> [!NOTE] Cómo se actualiza
> Al cerrar cada notebook: mover el 📍, añadir su bloque completo, actualizar la tabla de números y los cuatro retos, y subir a deuda abierta lo que quede vivo.
