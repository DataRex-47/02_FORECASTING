
#Importaciones
import pandas as pd

#funciones necesarias para el reentrenamiento
from funciones import calidad_datos, crear_variables, lanzar_entrenamiento


#Cargar datos de entrenamiento
df = pd.read_pickle("train.pkl")

x = calidad_datos(df)
x = crear_variables(x)
lanzar_entrenamiento(x)   #guarda ohe_retail.pkl y lista_modelos_retail.pkl