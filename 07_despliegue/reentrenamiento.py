
#Importaciones
import numpy as np
import pandas as pd
from dotenv import load_dotenv
import os
from pathlib import Path
import openpyxl
from sklearn.feature_selection import mutual_info_regression
from sklearn.model_selection import TimeSeriesSplit
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.pipeline import Pipeline
from sklearn.model_selection import RandomizedSearchCV
from sklearn.metrics import mean_absolute_error
from sklearn.preprocessing import OneHotEncoder

#funciones necesarias para el reentrenamiento
from funciones import *


#Cargar datos de entrenamiento
df = pd.read_pickle("train.pkl")

#Variables madre segun el Excel de procesos: solo estas entran al proceso
VAR_MADRE = ['store_id', 'item_id', 'event_name_1', 'event_type_1', 'month', 'sell_price', 'ventas', 'weekday']


x = calidad_datos(df)
x = crear_variables(x)
lanzar_entrenamiento(x)   #guarda ohe_ret