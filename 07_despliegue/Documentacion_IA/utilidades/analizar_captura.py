# -*- coding: utf-8 -*-
"""Analiza una captura del tablero para verificar (sin ojos) que el diseno se dibuja.

Uso:  uv run python analizar_captura.py <ruta_captura.png>

Con el tema CLARO actual los valores esperados son aproximadamente:
  - media RGB del canvas: alta (blanco azulado)
  - % de pixeles claros: > 60
  - % de blanco puro (tarjetas): > 40
  - % de texto oscuro: entre 4 y 20
  - acentos violeta/cian: > 0.1 % cada uno
Si sale mayoritariamente oscuro: o no termino el render, o hay un panel de la UI
(p. ej. la barra de formulas DAX) encima del lienzo.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def analizar(ruta):
    imagen = np.asarray(Image.open(ruta).convert("RGB")).astype(int)
    alto, ancho, _ = imagen.shape
    canvas = imagen[int(alto * 0.20):int(alto * 0.98), int(ancho * 0.06):int(ancho * 0.80)]

    rojo, verde, azul = canvas[:, :, 0], canvas[:, :, 1], canvas[:, :, 2]
    suma = canvas.sum(axis=2)
    media = canvas.reshape(-1, 3).mean(axis=0).round(1)
    claros = float((suma > 600).mean()) * 100
    blancos = float((suma > 720).mean()) * 100
    texto = float((suma < 400).mean()) * 100
    violeta = float(((azul > 180) & (rojo > 140) & (rojo < 230) & (verde < 170) & (verde > 110)).mean()) * 100
    cian = float(((azul > 140) & (verde > 120) & (rojo < 110)).mean()) * 100

    print(f"tamano: {imagen.shape}  media canvas: {media}")
    print(f"pixeles claros: {claros:.1f}%   blanco puro: {blancos:.1f}%   texto oscuro: {texto:.2f}%")
    print(f"acentos -> violeta: {violeta:.2f}%   cian: {cian:.2f}%")

    bien = claros > 55 and 3 < texto < 25
    mensaje = "tema claro renderizado OK" if bien else "revisar: no parece el tema claro (o hay UI encima)"
    print("=> DIAGNOSTICO:", mensaje)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("uso: python analizar_captura.py <captura.png>")
        raise SystemExit(1)
    analizar(Path(sys.argv[1]))
