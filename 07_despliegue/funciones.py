
#Importaciones de librerías necesarias para el procesamiento de datos y modelado

import numpy as np
import pandas as pd
import joblib
from sklearn.feature_selection import mutual_info_regression
from sklearn.model_selection import TimeSeriesSplit
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.pipeline import Pipeline
from sklearn.model_selection import RandomizedSearchCV
from sklearn.preprocessing import OneHotEncoder


#Variables madre segun el Excel de procesos: solo estas entran al proceso
VAR_MADRE = ['store_id', 'item_id', 'event_name_1', 'event_type_1', 'month', 'sell_price', 'ventas', 'weekday']

# Las madres de las dummies finales (Excel de procesos)
VAR_OHE = ['event_name_1', 'event_type_1', 'month', 'weekday']

#Donde se guardan el encoder y la lista con los 20 modelos entrenados (junto al script)
RUTA_OHE = 'ohe_retail.pkl'
RUTA_MODELOS = 'lista_modelos_retail.pkl'

#dias a predecir (el horizonte del pedido)
HORIZONTE = 8

def calidad_datos(x):
    temp = x[VAR_MADRE].copy()
    #modificar tipos: solo month, porque month_2 es variable final y el OHE se entreno con month en texto
    #(year y wday no llegan a ninguna variable final, convertirlas no sirve para nada)
    temp['month'] = temp['month'].astype('str')
    #imputar nulos de eventos, event_type_1_Sin_evento es variable final
    temp.fillna({'event_name_1': 'Sin_evento', 'event_type_1': 'Sin_evento'}, inplace=True)
    #eliminar registros sin precio (pre lanzamiento, como los 71 de FOODS_3_288), sin reset_index para no perder date
    temp = temp.dropna(subset=['sell_price'])
    return temp

def crear_variables(x):
    #demanda intermitente
    def rotura_stock(ventas, n):
        a = (ventas==0).astype(int)
        b = a.rolling(n).sum()
        return(b==n).astype(int)

    #Por si acaso se ordena el dataframe antes de agrupar
    x = x.sort_values(['store_id', 'item_id', 'date'])
    nivelPxT = x.groupby(['store_id', 'item_id'])['ventas']

    for n in (3, 7, 15):
        x[f'rotura_stock_{n}'] = nivelPxT.transform(rotura_stock, n=n)

    # ── Lags ─────────────────────────────────────────────────────────────
    # 'columna_original': [lags en dias] -> para añadir/quitar lags solo se toca esto
    CONFIG_LAGS = {
        'ventas':          list(range(1, 16)),
        'sell_price':      list(range(1, 8)),
        'rotura_stock_3':  [1],
        'rotura_stock_7':  [1],
        'rotura_stock_15': [1],
    }

    #Creacion de lags
    def crear_lags(df, config, cols_serie=('store_id', 'item_id'), col_fecha='date'):
        """Lags dentro de cada serie producto-tienda. Devuelve un df de lags (sin unir)."""
        df = df.sort_values(list(cols_serie) + [col_fecha])
        grupos = df.groupby(list(cols_serie))
        resultado = pd.DataFrame(index=df.index)

        for columna in config:
            for lag in config[columna]:
                resultado[f'{columna}_lag{lag}'] = grupos[columna].shift(lag)

        return resultado

    df_lags = crear_lags(x, CONFIG_LAGS)

    #Ventanas moviles
    #Estadisticos min y max y media movil ponderada
    def estadistico_movil_serie(ventas, n, estadistico):
        return ventas.shift(1).rolling(n).agg(estadistico)

    def media_movil_ponderada_serie(ventas, n):
        return ventas.shift(1).ewm(span=n, min_periods=n).mean()

    for n in range(2, 16):
        x['ventasmin' + str(n)] = nivelPxT.transform(estadistico_movil_serie, n=n, estadistico='min')
        x['ventasmax' + str(n)] = nivelPxT.transform(estadistico_movil_serie, n=n, estadistico='max')
        x['ventasmmp' + str(n)] = nivelPxT.transform(media_movil_ponderada_serie, n=n)

    #unir todos los lags con el dataframe original
    x = pd.concat([x, df_lags], axis=1)
    #Eliminar las FILAS que quedaron con nulos por los lags (los primeros 15 dias de cada serie)
    #con subset para no depender de otras columnas con nulos como event_name_2
    x = x.dropna(subset=df_lags.columns)
    #Variables que ya no se van a necesitar (las originales)
    x = x.drop(columns=['sell_price','rotura_stock_3','rotura_stock_7','rotura_stock_15'])
    # Se crea una sola variable para el producto debido a que se haran 20 modelos, una por cada
    # producto-tienda, se eliminan entonces las columnas 'item_id' y 'store_id'
    # mismo orden que en la modelizacion (tienda_producto) para que coincida con lista_modelos
    x['producto'] = x['store_id'] + '_' + x['item_id']
    x = x.drop(columns=['item_id', 'store_id'])
    return x

def aplicar_ohe(x, ohe):
    # Cambia las categoricas por sus dummies; index=x.index para que cada dummy caiga en su fila
    dummies = pd.DataFrame(ohe.transform(x[VAR_OHE]), columns=ohe.get_feature_names_out(), index=x.index)
    return pd.concat([x.drop(columns=VAR_OHE), dummies], axis=1)


def transformar_variables_entrenamiento(x):
    # Entrenar: el encoder aprende las categorias de TODO el historico y se guarda
    ohe = OneHotEncoder(sparse_output=False, drop='first', handle_unknown='ignore').fit(x[VAR_OHE])
    joblib.dump(ohe, RUTA_OHE)
    return aplicar_ohe(x, ohe)


def transformar_variables_ejecucion(x):
    # Ejecutar: se usa el encoder guardado y no uno nuevo, para que salgan las mismas columnas del entrenamiento
    ohe = joblib.load(RUTA_OHE)
    return aplicar_ohe(x, ohe)

def preseleccion_variables(x, y, n_variables=75):
    #Solo en entrenamiento: se queda con las n variables con mas mutual information contra las ventas
    x = x.drop(columns=['producto'], errors='ignore')
    #un valor de MI por columna, con el nombre de la variable como indice
    mi = pd.Series(mutual_info_regression(x, y, random_state = 42), index=x.columns)
    #las n mas altas
    entran = mi.nlargest(n_variables).index
    return x[entran]


def modelizar(x_producto, y):
    '''
    Esta función es la que hace la modelización individual.

    Recibe los datos de las x y la y de un producto.

    Encuentra los parámetros óptimos para ese producto.

    Devuelve el mejor modelo.
    '''
    #Excluye el producto como variable de modelización
    #y preselecciona con MI las variables de ESTE producto (cada serie elige las suyas)
    x_mod = preseleccion_variables(x_producto, y)

    #Define la validación cruzada
    time_cv = TimeSeriesSplit(5, test_size = 8)

    #Define la parrilla de algoritmos
    pipe = Pipeline([('algoritmo',HistGradientBoostingRegressor(random_state = 42))])

    grid = [
         {'algoritmo': [HistGradientBoostingRegressor(random_state = 42)]
#          'algoritmo__learning_rate': [0.01,0.025,0.05,0.1],
#          'algoritmo__max_iter': [50,100,200],
#          'algoritmo__max_depth': [5,10,20,50],
#          'algoritmo__scoring': ['neg_mean_absolute_error'],   #OJO: no descomentar, el scoring va en el buscador, no en el algoritmo
#          'algoritmo__l2_regularization': [0,0.25,0.5,0.75,1]
         }

    ]

    #Crea los modelos
    random_search = RandomizedSearchCV(estimator = pipe,
                                   param_distributions = grid,
                                   n_iter = 1,
                                   cv = time_cv,
                                   scoring = 'neg_mean_absolute_error',
                                   verbose = 0,
                                   n_jobs = -1,
                                   random_state = 42)   #para que el sorteo de combinaciones se pueda repetir

    random_search.fit(x_mod, y)

    #Reentrena el mejor sobre todos los datos
    #(no hace falta otro .fit: RandomizedSearchCV ya lo hace solo con refit=True, que viene por defecto)
    modelo_final = random_search.best_estimator_

    #Devuelve como salida el mejor modelo
    return modelo_final

def lanzar_entrenamiento(df):

    '''
    Esta función va recorriendo todos los productos y llamando a modelizar() para crear una lista total con todos los modelos de todos los productos.

    Recibe el dataframe que sale de crear_variables(): limpio, con la columna producto y con la target (ventas) dentro.

    No devuelve nada, si no que guarda en disco el objeto ya entrenado con todos los modelos.
    '''

    #Transforma UNA sola vez con todo el historico: el encoder aprende de las 20 series juntas y se guarda una vez
    df = transformar_variables_entrenamiento(df)

    lista_productos = list(df['producto'].unique())

    lista_modelos = []

    for cada in lista_productos:

        #Renombra por claridad
        producto = cada
        target = 'ventas'

        #x e y de este producto, sacadas de sus propias filas (la fecha se repite entre series, isin no sirve)
        x = df.loc[df['producto'] == producto].drop(columns=target).copy()
        y = df.loc[df['producto'] == producto, target].copy()

        #Llama a la funcion de modelizar (dentro ya hace la preseleccion con MI de este producto)
        modelo = modelizar(x, y)

        #Añade el modelo final a la lista
        lista_modelos.append((producto, modelo))

    #Guarda la lista de modelos entrenados
    joblib.dump(lista_modelos, RUTA_MODELOS)


def lanzar_ejecucion(df):
    '''
    Predice todos los productos, pero solo el dia que toca.
    Recibe el dataframe que sale de crear_variables().
    '''
    #carga la lista [(producto, modelo), ...] que guardo lanzar_entrenamiento
    lista_modelos = joblib.load(RUTA_MODELOS)

    #transforma una sola vez con el encoder guardado (igual que en el entrenamiento)
    df = transformar_variables_ejecucion(df)

    lista_predicciones = []

    for cada in lista_modelos:
        #renombra por claridad
        producto = cada[0]
        modelo = cada[1]

        #filas de este producto, solo con las variables que eligio su modelo (y en el mismo orden)
        x = df.loc[df.producto == producto, modelo.feature_names_in_]

        #prediccion de este producto, con la fecha en el indice
        #clip(min=0): la regresion no tiene piso y no existen ventas negativas
        predicciones = pd.DataFrame({'producto': producto,
                                     'prediccion': modelo.predict(x).clip(min = 0).astype('int')},
                                    index = x.index)

        lista_predicciones.append(predicciones)

    #junta las predicciones de los 20 productos
    predicciones_df = pd.concat(lista_predicciones)

    #el dia que toca es la fecha mas baja que sobrevivio al dropna de los lags
    predicciones_df = predicciones_df.loc[predicciones_df.index == predicciones_df.index.min()]

    #date pasa a columna para el CSV que va a Power BI
    return predicciones_df.reset_index()

def forecasting_autorregresivo(x):
    '''
    No reentrena nada: usa los modelos ya entrenados, como un CRM que pide un scoring a la API.
    Los ultimos 15 dias se aplanan en una sola fila (ventas_lag1 a ventas_lag15) y el modelo da un dia.
    Como mañana no existe, cada prediccion se escribe como venta y se repite hasta completar el HORIZONTE.
    Recibe 15 dias de historia mas los 8 dias a predecir.
    '''
    for cada in range(0, HORIZONTE):
        #prepara la fila de cada producto igual que en el entrenamiento y predice el dia que toca
        paso1_df = calidad_datos(x)
        paso2_df = crear_variables(paso1_df)
        f = lanzar_ejecucion(paso2_df)

        #la prediccion pasa a ser la venta de ese dia, para que el shift la meta en los lags de la siguiente vuelta
        #(cada fila busca la de su producto por nombre, asi no depende del orden)
        prediccion_por_producto = f.set_index('producto')['prediccion']
        dia = f['date'].iloc[0]
        es_dia = x.index == dia
        producto_fila = x.loc[es_dia, 'store_id'] + '_' + x.loc[es_dia, 'item_id']
        x.loc[es_dia, 'ventas'] = producto_fila.map(prediccion_por_producto).values

        #regla de negocio: en Navidad la tienda cierra y la venta es 0
        #(en 3 años el modelo solo vio 2 navidades por producto, muy pocas para aprenderlo solo)
        if (x.loc[es_dia, 'event_name_1'] == 'Christmas').any():
            x.loc[es_dia, 'ventas'] = 0

        #se borra el dia mas antiguo: si no, el mismo dia seguiria con sus 15 lags completos y se predeciria otra vez
        #al borrarlo, la fecha mas baja completa pasa a ser el dia siguiente y la ventana avanza
        x = x.loc[x.index != x.index.min()]

    return x
