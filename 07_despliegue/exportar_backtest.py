"""
Exporta el backtest para la pagina 2 de Power BI.

Repite la evaluacion del notebook 08: cuatro cortes de diciembre de 2015,
con los modelos entrenados hasta el 30 de noviembre (05_modelos) y 15 dias
reales de historia en cada corte. Los 8 dias siguientes se tapan, el
recursivo los predice y se comparan con lo que realmente se vendio.

Salida: backtest.csv (una fila por corte x dia x tienda x producto)
  fecha_corte, date, horizonte, store_id, item_id, real, pred, pred_base

Uso (desde la carpeta 07_despliegue):  python exportar_backtest.py
"""
import os
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
TRAIN = RAIZ / "02_datos" / "03_Entrenamiento" / "train.pkl"
VALIDACION = RAIZ / "02_datos" / "02_Validacion" / "validacion.pkl"
MODELOS = RAIZ / "05_modelos"

CORTES = ["2015-11-30", "2015-12-08", "2015-12-16", "2015-12-23"]
HORIZONTE = 8
DIAS_HISTORIA = 15

# funciones.py busca los .pkl con ruta relativa: se corre desde 05_modelos
import sys
sys.path.insert(0, str(AQUI))
os.chdir(MODELOS)
from funciones import forecasting_autorregresivo  # noqa: E402

train = pd.read_pickle(TRAIN)
val = pd.read_pickle(VALIDACION)
print("train llega hasta:", train.index.max(), "(debe ser 2015-11-30)")

completo = pd.concat([train, val]).sort_index()

# modelo base: lo que esa serie vendio hace 7 dias
c = completo.reset_index().sort_values(["store_id", "item_id", "date"])
c["pred_base"] = c.groupby(["store_id", "item_id"])["ventas"].shift(7)
base = c.set_index(["date", "store_id", "item_id"])["pred_base"]

salida = []
for corte in CORTES:
    f_corte = pd.Timestamp(corte)
    ini = (f_corte - pd.Timedelta(days=DIAS_HISTORIA - 1)).strftime("%Y-%m-%d")
    fin = (f_corte + pd.Timedelta(days=HORIZONTE)).strftime("%Y-%m-%d")

    historia = completo.loc[ini:corte]
    futuro = completo.loc[corte:fin]
    futuro = futuro[futuro.index > corte].copy()

    reales = futuro[["store_id", "item_id", "ventas"]].reset_index()
    futuro["ventas"] = np.nan  # se tapan para que el recursivo las prediga

    entrada = pd.concat([historia, futuro])
    resultado = forecasting_autorregresivo(entrada)

    pred = resultado.loc[resultado.index > corte, ["store_id", "item_id", "ventas"]].reset_index()
    comp = reales.merge(pred, on=["date", "store_id", "item_id"], suffixes=("_real", "_pred"))
    comp = comp.rename(columns={"ventas_real": "real", "ventas_pred": "pred"})

    comp["fecha_corte"] = corte
    comp["horizonte"] = (pd.to_datetime(comp["date"]) - f_corte).dt.days
    comp["pred_base"] = comp.set_index(["date", "store_id", "item_id"]).index.map(base)
    salida.append(comp)

    mae = (comp["real"] - comp["pred"]).abs().mean()
    mae_b = (comp["real"] - comp["pred_base"]).abs().mean()
    print(f"corte {corte}: filas {len(comp)}  MAE modelo {mae:.2f}  MAE base {mae_b:.2f}")

out = pd.concat(salida, ignore_index=True)
out = out[["fecha_corte", "date", "horizonte", "store_id", "item_id", "real", "pred", "pred_base"]]
out.to_csv(AQUI / "backtest.csv", index=False)
print("backtest.csv:", len(out), "filas (esperadas 640)")
