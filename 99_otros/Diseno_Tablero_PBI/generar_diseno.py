# -*- coding: utf-8 -*-
"""Genera el nuevo diseno del reporte (PBIR) para Tablero_Ventas.pbix.

Escribe en DESTINO la carpeta Report/ lista para copiar sobre el pbix real.
"""
import json
import shutil
import struct
import zlib
from pathlib import Path

import numpy as np

ORIGEN = Path(r"C:\Users\Admin\AppData\Local\Temp\pbix_extract")
DESTINO = Path(r"C:\Users\Admin\AppData\Local\Temp\pbi_reporte\Report")
PAGINA = "0eedf0bd9a2c3545bc68"

SCHEMA_REPORT = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.3.0/schema.json"
SCHEMA_PAGES = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json"
SCHEMA_PAGE = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json"
SCHEMA_VISUAL = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.13.0/schema.json"

# ── Paleta (tema claro accesible) ─────────
FONDO_PAGINA = "#F6F8FC"
FONDO_TARJETA = "#FFFFFF"
BORDE_TARJETA = "#DDE5F0"
CIAN = "#0E7490"
VIOLETA = "#6D28D9"
AZUL = "#1D4ED8"
AMBAR = "#B45309"
ROSA = "#BE123C"
TEXTO = "#16233A"
TEXTO_SUAVE = "#42536E"
TEXTO_LABEL = "#5B6B84"
INDIGO_INSIGHT = "#4338CA"

USAR_IMAGEN_FONDO = True


def leer_json(ruta):
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def guardar_json(ruta, datos):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(datos, ensure_ascii=False, separators=(",", ":"))
    ruta.write_bytes(texto.encode("utf-8"))


def lit(valor):
    return {"expr": {"Literal": {"Value": valor}}}


def color(hex_):
    return {"solid": {"color": {"expr": {"Literal": {"Value": "'" + hex_ + "'"}}}}}


def estilo_contenedor(titulo=None, fondo=FONDO_TARJETA, borde=BORDE_TARJETA, radio=14,
                      transparencia=0, padding=8, tam_titulo="13D", color_titulo=TEXTO,
                      sombra=True):
    cont = {}
    if titulo is not None:
        cont["title"] = [{"properties": {
            "show": lit("true"),
            "text": lit("'" + titulo + "'"),
            "fontSize": lit(tam_titulo),
            "fontColor": color(color_titulo),
            "bold": lit("true"),
            "alignment": lit("'left'"),
        }}]
    else:
        cont["title"] = [{"properties": {"show": lit("false")}}]
    if fondo is None:
        cont["background"] = [{"properties": {"show": lit("false")}}]
    else:
        cont["background"] = [{"properties": {
            "show": lit("true"),
            "color": color(fondo),
            "transparency": lit(str(transparencia) + "D"),
        }}]
    if borde is None:
        cont["border"] = [{"properties": {"show": lit("false")}}]
    else:
        cont["border"] = [{"properties": {
            "show": lit("true"),
            "color": color(borde),
            "radius": lit(str(radio) + "D"),
            "width": lit("1D"),
        }}]
    if sombra:
        cont["dropShadow"] = [{"properties": {
            "show": lit("true"),
            "preset": lit("'Custom'"),
            "transparency": lit("78D"),
            "shadowBlur": lit("14D"),
            "shadowDistance": lit("3D"),
            "angle": lit("90D"),
            "shadowSpread": lit("0D"),
        }}]
    else:
        cont["dropShadow"] = [{"properties": {"show": lit("false")}}]
    cont["padding"] = [{"properties": {
        "top": lit(str(padding) + "D"),
        "bottom": lit(str(padding) + "D"),
        "left": lit(str(padding) + "D"),
        "right": lit(str(padding) + "D"),
    }}]
    return cont


def posicion(x, y, w, h, z):
    return {"x": x, "y": y, "z": z, "height": h, "width": w, "tabOrder": z}


def ref_medida(nombre):
    return {"Measure": {"Expression": {"SourceRef": {"Entity": "Medidas"}},
                        "Property": nombre}}


def ref_columna(tabla, columna):
    return {"Column": {"Expression": {"SourceRef": {"Entity": tabla}},
                       "Property": columna}}


def proyeccion(campo, query_ref, nombre_visible=None, activo=False):
    proy = {"field": campo, "queryRef": query_ref, "nativeQueryRef": query_ref.split(".")[-1]}
    if nombre_visible is not None:
        proy["displayName"] = nombre_visible
    if activo:
        proy["active"] = True
    return proy


# ── Textbox: runs ─────────
FUENTE_NORMAL = "'Segoe UI', wf_segoe-ui_normal, helvetica, arial, sans-serif"
FUENTE_SEMIBOLD = "'Segoe UI Semibold', wf_segoe-ui_semibold, helvetica, arial, sans-serif"


def estilo_run(tam, color_hex, negrita):
    estilo = {
        "fontFamily": FUENTE_SEMIBOLD if negrita else FUENTE_NORMAL,
        "fontSize": tam,
        "color": color_hex,
    }
    if negrita:
        estilo["fontWeight"] = "bold"
    return estilo


def run_texto(texto, tam="12pt", color_hex=TEXTO_SUAVE, negrita=False):
    return {"value": texto, "textStyle": estilo_run(tam, color_hex, negrita)}


def run_medida(identificador, medida, tam="12pt", color_hex=TEXTO_SUAVE, negrita=False):
    return {
        "value": {
            "propertyIdentifier": {"objectName": "values", "propertyName": "expr"},
            "selector": {"id": identificador},
        },
        "textStyle": estilo_run(tam, color_hex, negrita),
    }


def valor_medida(identificador, medida):
    return {
        "properties": {
            "expr": {"expr": {
                "Aggregation": {
                    "Expression": {
                        "Column": {
                            "Expression": {"Subquery": {"Query": {
                                "Version": 2,
                                "From": [{"Name": "m", "Entity": "Medidas", "Type": 0}],
                                "Select": [{"Measure": {"Expression": {"SourceRef": {"Source": "m"}},
                                                        "Property": medida},
                                            "Name": "Medidas." + medida}],
                            }}},
                            "Property": "Medidas." + medida,
                        }
                    },
                    "Function": 3,
                }
            }},
        },
        "selector": {"id": identificador},
    }


def parrafo(runs, alineacion="left"):
    return {"textRuns": runs, "horizontalTextAlignment": alineacion}


def textbox(nombre, x, y, w, h, z, parrafos, contenedor, valores=None):
    objetos = {"general": [{"properties": {"paragraphs": parrafos}}]}
    if valores:
        objetos["values"] = valores
    return {
        "$schema": SCHEMA_VISUAL,
        "name": nombre,
        "position": posicion(x, y, w, h, z),
        "visual": {
            "visualType": "textbox",
            "objects": objetos,
            "visualContainerObjects": contenedor,
            "drillFilterOtherVisuals": False,
        },
    }


# ── Visuales ─────────
def visual_encabezado():
    parrafos = [
        parrafo([run_texto("🔮 Pronóstico de Ventas · Retail", tam="26pt", color_hex=TEXTO, negrita=True)]),
        parrafo([run_medida("Value", "Subtitulo_Cierre", tam="13pt", color_hex=TEXTO_SUAVE)]),
    ]
    valores = [valor_medida("Value", "Subtitulo_Cierre")]
    cont = estilo_contenedor(titulo=None, fondo=FONDO_TARJETA, borde=BORDE_TARJETA, radio=18,
                             transparencia=25, padding=16, sombra=True)
    return textbox("a0010000000000000001", 28, 24, 1176, 124, 100, parrafos, cont, valores)


def visual_panel_ia():
    parrafos = [
        parrafo([run_texto("🤖 Lectura automática del pronóstico", tam="13pt", color_hex=TEXTO, negrita=True)]),
        parrafo([run_texto(" ", tam="4pt")]),
        parrafo([run_medida("Value", "Insight_Producto", tam="12pt", color_hex=INDIGO_INSIGHT)]),
        parrafo([run_medida("Value 2", "Insight_Tienda", tam="12pt", color_hex=INDIGO_INSIGHT)]),
        parrafo([run_medida("Value 3", "Insight_Dia", tam="12pt", color_hex=INDIGO_INSIGHT)]),
        parrafo([run_medida("Value 4", "Insight_Ritmo", tam="12pt", color_hex=INDIGO_INSIGHT)]),
    ]
    valores = [
        valor_medida("Value", "Insight_Producto"),
        valor_medida("Value 2", "Insight_Tienda"),
        valor_medida("Value 3", "Insight_Dia"),
        valor_medida("Value 4", "Insight_Ritmo"),
    ]
    cont = estilo_contenedor(titulo=None, fondo="#F4F1FF", borde=VIOLETA, radio=16,
                             transparencia=0, padding=16, sombra=True)
    return textbox("a0020000000000000002", 1302, 340, 590, 360, 310, parrafos, cont, valores)


def visual_etiqueta(nombre, texto, x, y, w):
    parrafos = [parrafo([run_texto(texto, tam="11pt", color_hex=TEXTO_LABEL, negrita=True)])]
    cont = estilo_contenedor(titulo=None, fondo=None, borde=None, sombra=False, padding=0)
    return textbox(nombre, x, y, w, 26, 110, parrafos, cont)


def visual_slicer(nombre, tabla, columna, x, y, w, h, z):
    return {
        "$schema": SCHEMA_VISUAL,
        "name": nombre,
        "position": posicion(x, y, w, h, z),
        "visual": {
            "visualType": "slicer",
            "query": {"queryState": {"Values": {"projections": [
                proyeccion(ref_columna(tabla, columna), tabla + "." + columna, activo=True)
            ]}}},
            "objects": {
                "data": [{"properties": {"mode": lit("'Dropdown'")}}],
                "header": [{"properties": {"show": lit("false")}}],
                "items": [{"properties": {"textSize": lit("12D")}}],
            },
            "visualContainerObjects": estilo_contenedor(titulo=None, fondo=FONDO_TARJETA,
                                                        borde=BORDE_TARJETA, radio=12,
                                                        padding=4, sombra=False),
            "drillFilterOtherVisuals": True,
        },
    }


def visual_kpi(nombre, medida, etiqueta, acento, x, y):
    return {
        "$schema": SCHEMA_VISUAL,
        "name": nombre,
        "position": posicion(x, y, 448, 144, 200),
        "visual": {
            "visualType": "cardVisual",
            "query": {"queryState": {"Data": {"projections": [
                proyeccion(ref_medida(medida), "Medidas." + medida, nombre_visible=etiqueta)
            ]}}},
            "objects": {},
            "visualContainerObjects": estilo_contenedor(titulo=None, fondo=FONDO_TARJETA,
                                                        borde=acento, radio=16,
                                                        padding=10, sombra=True),
            "drillFilterOtherVisuals": True,
        },
    }


def visual_linea():
    return {
        "$schema": SCHEMA_VISUAL,
        "name": "c0010000000000000001",
        "position": posicion(28, 340, 1250, 360, 300),
        "visual": {
            "visualType": "lineChart",
            "query": {
                "queryState": {
                    "Category": {"projections": [proyeccion(ref_columna("dim_calendario", "Date"), "dim_calendario.Date", activo=True)]},
                    "Y": {"projections": [
                        proyeccion(ref_medida("Ventas_Reales"), "Medidas.Ventas_Reales"),
                        proyeccion(ref_medida("Ventas_Predichas"), "Medidas.Ventas_Predichas"),
                    ]},
                },
                "sortDefinition": {"sort": [{"field": ref_columna("dim_calendario", "Date"),
                                             "direction": "Ascending"}], "isDefaultSort": True},
            },
            "objects": {
                "lineStyles": [{"properties": {"lineChartType": lit("'linear'")}}],
                "labels": [{"properties": {"show": lit("false")}}],
            },
            "visualContainerObjects": estilo_contenedor(titulo="📈 Real vs pronóstico", padding=8),
            "drillFilterOtherVisuals": True,
        },
    }


def visual_matriz():
    return {
        "$schema": SCHEMA_VISUAL,
        "name": "e0010000000000000001",
        "position": posicion(28, 724, 1090, 332, 400),
        "visual": {
            "visualType": "pivotTable",
            "query": {"queryState": {
                "Rows": {"projections": [proyeccion(ref_columna("Productos", "item_id"), "Productos.item_id", activo=True)]},
                "Columns": {"projections": [proyeccion(ref_columna("dim_calendario", "Date"), "dim_calendario.Date")]},
                "Values": {"projections": [proyeccion(ref_medida("Ventas_Predichas"), "Medidas.Ventas_Predichas",
                                                      nombre_visible="Pronóstico (uds.)")]},
            }},
            "objects": {},
            "visualContainerObjects": estilo_contenedor(titulo="🧮 Pronóstico por producto y día · unidades", padding=8),
            "drillFilterOtherVisuals": True,
        },
    }


def visual_barra_productos():
    return {
        "$schema": SCHEMA_VISUAL,
        "name": "f0010000000000000001",
        "position": posicion(1142, 724, 372, 332, 500),
        "visual": {
            "visualType": "clusteredBarChart",
            "query": {
                "queryState": {
                    "Category": {"projections": [proyeccion(ref_columna("Productos", "item_id"), "Productos.item_id", activo=True)]},
                    "Y": {"projections": [proyeccion(ref_medida("Peso_Producto"), "Medidas.Peso_Producto")]},
                },
                "sortDefinition": {"sort": [{"field": ref_medida("Peso_Producto"),
                                             "direction": "Descending"}], "isDefaultSort": True},
            },
            "objects": {
                "labels": [{"properties": {"show": lit("true"),
                                           "enableValueDataLabel": lit("true"),
                                           "fontSize": lit("9D"),
                                           "color": color(TEXTO_SUAVE)}}],
            },
            "visualContainerObjects": estilo_contenedor(titulo="⚖️ Peso por producto", padding=8),
            "drillFilterOtherVisuals": True,
        },
    }


def visual_dona_tiendas():
    return {
        "$schema": SCHEMA_VISUAL,
        "name": "f0020000000000000002",
        "position": posicion(1536, 724, 356, 332, 510),
        "visual": {
            "visualType": "donutChart",
            "query": {
                "queryState": {
                    "Category": {"projections": [proyeccion(ref_columna("Tiendas", "store_id"), "Tiendas.store_id", activo=True)]},
                    "Y": {"projections": [proyeccion(ref_medida("Peso_Tienda"), "Medidas.Peso_Tienda")]},
                },
                "sortDefinition": {"sort": [{"field": ref_medida("Peso_Tienda"),
                                             "direction": "Descending"}], "isDefaultSort": True},
            },
            "objects": {
                "labels": [{"properties": {"show": lit("true"), "fontSize": lit("10D"),
                                           "color": color(TEXTO)}}],
                "legend": [{"properties": {"show": lit("true"), "position": lit("'BottomCenter'"),
                                           "fontSize": lit("10D"), "labelColor": color(TEXTO_SUAVE)}}],
            },
            "visualContainerObjects": estilo_contenedor(titulo="🏪 Reparto por tienda", padding=8),
            "drillFilterOtherVisuals": True,
        },
    }


def construir_visuales():
    visuales = {}
    visuales["a0010000000000000001"] = visual_encabezado()
    visuales["a0020000000000000002"] = visual_panel_ia()
    visuales["a0030000000000000003"] = visual_etiqueta("a0030000000000000003", "🏪 Tienda", 1222, 30, 216)
    visuales["a0040000000000000004"] = visual_etiqueta("a0040000000000000004", "📦 Producto", 1450, 30, 216)
    visuales["a0050000000000000005"] = visual_etiqueta("a0050000000000000005", "📅 Fecha", 1678, 30, 216)
    visuales["a0060000000000000006"] = visual_slicer("a0060000000000000006", "Tiendas", "store_id", 1220, 58, 216, 76, 120)
    visuales["a0070000000000000007"] = visual_slicer("a0070000000000000007", "Productos", "item_id", 1448, 58, 216, 76, 121)
    visuales["a0080000000000000008"] = visual_slicer("a0080000000000000008", "hechos", "date", 1676, 58, 216, 76, 122)
    visuales["b0010000000000000001"] = visual_kpi("b0010000000000000001", "Ventas_Predichas",
                                                  "💰 Ventas predichas · 8 días", CIAN, 28, 172)
    visuales["b0020000000000000002"] = visual_kpi("b0020000000000000002", "Promedio_Diario_Predicho",
                                                  "📈 Ritmo diario predicho", VIOLETA, 500, 172)
    visuales["b0030000000000000003"] = visual_kpi("b0030000000000000003", "Promedio_Diario_Real",
                                                  "🧾 Ritmo diario real · 15 días", AZUL, 972, 172)
    visuales["b0040000000000000004"] = visual_kpi("b0040000000000000004", "Var_Ritmo_Pct",
                                                  "⚡ Variación de ritmo", AMBAR, 1444, 172)
    visuales["c0010000000000000001"] = visual_linea()
    visuales["e0010000000000000001"] = visual_matriz()
    visuales["f0010000000000000001"] = visual_barra_productos()
    visuales["f0020000000000000002"] = visual_dona_tiendas()
    return visuales


# ── Tema ─────────
def construir_tema():
    return {
        "name": "RexIA Forecast",
        "dataColors": [CIAN, VIOLETA, "#047857", AMBAR, ROSA, AZUL, "#DB2777", "#4D7C0F"],
        "foreground": "#1B2A41",
        "foregroundNeutralSecondary": "#5B6B84",
        "background": "#FFFFFF",
        "backgroundLight": "#F4F7FC",
        "backgroundNeutral": "#E8EDF6",
        "tableAccent": VIOLETA,
        "good": "#047857",
        "neutral": AMBAR,
        "bad": ROSA,
        "maximum": CIAN,
        "center": AMBAR,
        "minimum": ROSA,
        "textClasses": {
            "callout": {"fontSize": 40, "fontFace": "Segoe UI Semibold", "color": "#0F1B2D"},
            "title": {"fontSize": 13, "fontFace": "Segoe UI Semibold", "color": "#24344D"},
            "header": {"fontSize": 12, "fontFace": "Segoe UI Semibold", "color": "#3A4B66"},
            "label": {"fontSize": 11, "fontFace": "Segoe UI", "color": TEXTO_LABEL},
        },
        "visualStyles": {
            "cardVisual": {"*": {
                "value": [{"fontSize": 34, "fontFamily": "Segoe UI Semibold",
                           "color": {"solid": {"color": "#12203A"}}}],
                "label": [{"fontSize": 12, "fontFamily": "Segoe UI",
                           "color": {"solid": {"color": TEXTO_LABEL}}}],
            }},
            "lineChart": {"*": {
                "labels": [{"fontSize": 10, "color": {"solid": {"color": TEXTO_LABEL}}}],
                "legend": [{"fontSize": 10, "labelColor": {"solid": {"color": TEXTO_SUAVE}}}],
                "categoryAxis": [{"labelColor": {"solid": {"color": TEXTO_LABEL}}, "gridlineShow": False}],
                "valueAxis": [{"labelColor": {"solid": {"color": TEXTO_LABEL}},
                               "gridlineColor": {"solid": {"color": "#E3EAF3"}}}],
            }},
            "pivotTable": {"*": {
                "rowHeaders": [{"fontColor": {"solid": {"color": "#24344D"}}}],
                "columnHeaders": [{"fontColor": {"solid": {"color": TEXTO_SUAVE}}}],
                "values": [{"fontColorPrimary": {"solid": {"color": "#16233A"}}}],
                "grid": [{"gridVerticalColor": {"solid": {"color": "#E3EAF3"}},
                          "gridHorizontalColor": {"solid": {"color": "#E3EAF3"}}}],
            }},
        },
    }


# ── Imagen de fondo ─────────
def escribir_png(ruta, rgb):
    alto, ancho, _ = rgb.shape
    crudo = np.zeros((alto, ancho * 3 + 1), dtype=np.uint8)
    crudo[:, 1:] = rgb.reshape(alto, ancho * 3)
    comprimido = zlib.compress(crudo.tobytes(), 9)

    def bloque(tipo, datos):
        return (struct.pack(">I", len(datos)) + tipo + datos
                + struct.pack(">I", zlib.crc32(tipo + datos) & 0xFFFFFFFF))

    png = b"\x89PNG\r\n\x1a\n"
    png += bloque(b"IHDR", struct.pack(">IIBBBBB", ancho, alto, 8, 2, 0, 0, 0))
    png += bloque(b"IDAT", comprimido)
    png += bloque(b"IEND", b"")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "wb") as f:
        f.write(png)


def generar_fondo():
    alto, ancho = 1080, 1920
    yy, xx = np.mgrid[0:alto, 0:ancho].astype(np.float64)
    t = (yy / (alto - 1))[..., None]
    imagen = np.array([250, 252, 255]) * (1 - t) + np.array([232, 238, 249]) * t

    def brillo(img, cx, cy, radio, tono, alfa):
        dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        factor = np.clip(1 - dist / radio, 0, 1) ** 2
        a = (factor * alfa)[..., None]
        return img * (1 - a) + np.array(tono)[None, None, :] * a

    imagen = brillo(imagen, 300, 110, 780, (14, 165, 233), 0.06)
    imagen = brillo(imagen, 1560, 1010, 950, (124, 58, 237), 0.05)
    imagen = brillo(imagen, 1420, 90, 700, (99, 102, 241), 0.04)
    imagen = brillo(imagen, 950, 1090, 1000, (13, 148, 136), 0.03)

    banda = 1 + 0.05 * np.clip(1 - yy / 220, 0, 1) ** 1.6
    imagen = imagen * banda[..., None]
    return np.clip(imagen, 0, 255).astype(np.uint8)


# ── Montaje ─────────
def imagen_fondo_propiedades():
    return {
        "image": {"image": {
            "name": lit("'fondo_forecast.png'"),
            "url": {"expr": {"ResourcePackageItem": {
                "PackageName": "RegisteredResources",
                "PackageType": 1,
                "ItemName": "fondo_forecast.png",
            }}},
            "scaling": lit("'Fit'"),
        }}
    }


def construir_reporte_json():
    reporte = leer_json(ORIGEN / "Report" / "definition" / "report.json")
    reporte["themeCollection"]["customTheme"] = {
        "name": "RexIA_Forecast",
        "type": "RegisteredResources",
        "reportVersionAtImport": {"visual": "2.13.0", "report": "3.4.0", "page": "2.3.1"},
    }
    paquetes = reporte.get("resourcePackages", [])
    paquetes.append({
        "name": "RegisteredResources",
        "type": "RegisteredResources",
        "items": [
            {"name": "RexIA_Forecast", "path": "RexIA_Forecast.json", "type": "CustomTheme"},
            {"name": "fondo_forecast.png", "path": "fondo_forecast.png", "type": "Image"},
        ],
    })
    reporte["resourcePackages"] = paquetes
    return reporte


def construir_pagina_json():
    propiedades = {
        "color": color(FONDO_PAGINA),
        "transparency": lit("0D"),
    }
    if USAR_IMAGEN_FONDO:
        propiedades.update(imagen_fondo_propiedades())
    return {
        "$schema": SCHEMA_PAGE,
        "name": PAGINA,
        "displayName": "🔮 Pronóstico",
        "displayOption": "FitToPage",
        "height": 1080,
        "width": 1920,
        "objects": {"background": [{"properties": propiedades}]},
    }


def main():
    if DESTINO.exists():
        shutil.rmtree(DESTINO)
    shutil.copytree(ORIGEN / "Report" / "StaticResources", DESTINO / "StaticResources")
    (DESTINO / "definition").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ORIGEN / "Report" / "definition" / "version.json",
                 DESTINO / "definition" / "version.json")

    guardar_json(DESTINO / "definition" / "report.json", construir_reporte_json())
    guardar_json(DESTINO / "definition" / "pages" / "pages.json", {
        "$schema": SCHEMA_PAGES,
        "pageOrder": [PAGINA],
        "activePageName": PAGINA,
    })
    guardar_json(DESTINO / "definition" / "pages" / PAGINA / "page.json", construir_pagina_json())

    visuales = construir_visuales()
    for nombre, definicion in visuales.items():
        guardar_json(DESTINO / "definition" / "pages" / PAGINA / "visuals" / nombre / "visual.json", definicion)

    registered = DESTINO / "StaticResources" / "RegisteredResources"
    registered.mkdir(parents=True, exist_ok=True)
    guardar_json(registered / "RexIA_Forecast.json", construir_tema())
    if USAR_IMAGEN_FONDO:
        escribir_png(registered / "fondo_forecast.png", generar_fondo())

    print("visuales:", len(visuales))
    for ruta in sorted(DESTINO.rglob("*")):
        if ruta.is_file():
            print("  ", ruta.relative_to(DESTINO), ruta.stat().st_size)


if __name__ == "__main__":
    main()
