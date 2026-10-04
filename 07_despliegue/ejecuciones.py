import warnings
warnings.filterwarnings("ignore", message="X has feature names")
import numpy as np
import pandas as pd

# funciones necesarias para la ejecucion
from funciones import forecasting_autorregresivo, HORIZONTE


# la entrada la genera Sistemas con la consulta SQL: 15 dias reales mas los dias a predecir
entrada = pd.read_csv("DatosParaProduccion.csv", sep=";")

# la fecha pasa a texto aaaa-mm-dd (igual que en el entrenamiento) y queda como indice
entrada["date"] = pd.to_datetime(entrada["date"], dayfirst=True).dt.strftime("%Y-%m-%d")
entrada = entrada.set_index("date")

# los eventos sin valor pueden llegar como 0: se dejan vacios para que calidad_datos los vuelva Sin_evento
entrada[["event_name_1", "event_type_1"]] = entrada[["event_name_1", "event_type_1"]].replace({0: np.nan, "0": np.nan})

# ultimo dia con ventas reales: justo antes de los HORIZONTE dias a predecir
fecha_corte = entrada.index.unique().sort_values()[-(HORIZONTE + 1)]

# el recursivo predice los dias del horizonte, sobrescribiendo los 0 de ventas con sus predicciones
resultado = forecasting_autorregresivo(entrada)

# solo los dias predichos, con lo que necesita Power BI
predicciones = resultado.loc[resultado.index > fecha_corte, ["store_id", "item_id", "ventas"]].reset_index()
predicciones.to_csv("predicciones.csv", index=False)

print(f"predicciones guardadas: {len(predicciones)} filas")
