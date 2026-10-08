# -*- coding: utf-8 -*-
"""Empaqueta el pbix rediseñado.

Lee el pbix REAL (ya guardado por Power BI Desktop, con las medidas nuevas),
sustituye TODA la carpeta Report/ por el diseno generado y escribe:
  - C:\\...\\pbi_reporte\\Tablero_Ventas_nuevo.pbix   (para verificar)
No toca el original.
"""
import shutil
import zipfile
from pathlib import Path

PBX_ORIGINAL = Path(r"c:\Users\Admin\Desktop\Desktop\CarpetaFisica\Data Detective\Mis Casos(Importante)\PROYECTO 5 - FORECASTING RETAIL\02_FORECASTING\07_despliegue\Tablero_Ventas.pbix")
STAGING = Path(r"C:\Users\Admin\AppData\Local\Temp\pbi_reporte\Report")
SALIDA = Path(r"C:\Users\Admin\AppData\Local\Temp\pbi_reporte\Tablero_Ventas_nuevo.pbix")
RESPALDO = Path(r"C:\Users\Admin\AppData\Local\Temp\pbi_reporte\Tablero_Ventas_original.pbix")

CONTENT_TYPES_PNG = b'<Default Extension="png" ContentType="" />'


def entrada_ordenada(nombres):
    """[Content_Types].xml primero, el resto igual; Report/ se reemplaza."""
    resto = []
    for nombre in nombres:
        if nombre.startswith("Report/"):
            continue
        if nombre == "[Content_Types].xml":
            continue
        resto.append(nombre)
    return resto


def main():
    if not PBX_ORIGINAL.exists():
        raise SystemExit("No existe el pbix original")
    if not STAGING.exists():
        raise SystemExit("No existe el diseno generado")

    shutil.copy2(PBX_ORIGINAL, RESPALDO)

    with zipfile.ZipFile(PBX_ORIGINAL, "r") as z:
        nombres = z.namelist()
        if "Report/definition/report.json" not in nombres:
            raise SystemExit("El pbix guardado NO usa formato PBIR (no hay Report/definition/report.json). Hay que adaptar el plan.")
        contenido = {}
        for nombre in nombres:
            contenido[nombre] = z.read(nombre)

    content_types = contenido["[Content_Types].xml"].decode("utf-8")
    if 'Extension="png"' not in content_types:
        content_types = content_types.replace("</Types>", CONTENT_TYPES_PNG.decode("utf-8") + "</Types>")
    contenido["[Content_Types].xml"] = content_types.encode("utf-8")

    # SecurityBindings es una firma del paquete que Desktop genera al guardar:
    # cualquier cambio en el reporte la invalida y el archivo se rechaza.
    # Se neutraliza (mismo tamano) y Desktop la regenera al guardar.
    contenido["SecurityBindings"] = bytes(len(contenido["SecurityBindings"]))

    with zipfile.ZipFile(SALIDA, "w", zipfile.ZIP_DEFLATED) as z_out:
        z_out.writestr("[Content_Types].xml", contenido["[Content_Types].xml"])
        for nombre in entrada_ordenada(nombres):
            z_out.writestr(nombre, contenido[nombre])
        for ruta in sorted(STAGING.rglob("*")):
            if ruta.is_file():
                nombre_zip = "Report/" + ruta.relative_to(STAGING).as_posix()
                z_out.writestr(nombre_zip, ruta.read_bytes())

    with zipfile.ZipFile(SALIDA, "r") as z:
        malos = z.testzip()
        if malos is not None:
            raise SystemExit("Zip corrupto en " + str(malos))
        print("entradas:", len(z.namelist()))
        for nombre in z.namelist():
            if nombre.startswith("Report/definition/pages") and nombre.endswith(".json"):
                print("   ", nombre)

    print("OK ->", SALIDA)
    print("respaldo ->", RESPALDO)


if __name__ == "__main__":
    main()
