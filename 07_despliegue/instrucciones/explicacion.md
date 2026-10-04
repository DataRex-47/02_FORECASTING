# Cómo usar 07_despliegue (chuleta para mí)

Regla de oro: todo se lanza desde DENTRO de 07_despliegue. Los scripts leen y escriben archivos por nombre simple, así que la carpeta de trabajo tiene que ser esta.

## Qué hay en la carpeta

1. funciones.py: la caja de herramientas. Constantes (VAR_MADRE, VAR_OHE, RUTA_OHE, RUTA_MODELOS, HORIZONTE) y las funciones. No se ejecuta solo.
2. reentrenamiento.py: lee train.pkl, limpia, crea variables y entrena los 20 modelos. Guarda ohe_retail.pkl y lista_modelos_retail.pkl.
3. ejecuciones.py: lee DatosParaProduccion.csv, predice 8 días con los modelos guardados y escribe predicciones.csv.
4. consulta_entrada_ejecucion.sql: la consulta que sistemas usa para generar DatosParaProduccion.csv.
5. train.pkl: datos históricos para reentrenar.
6. ohe_retail.pkl y lista_modelos_retail.pkl: salida del reentrenamiento, entrada de la ejecución.
7. DatosParaProduccion.csv: lo genera sistemas cada cierto tiempo.
8. predicciones.csv: resultado de ejecuciones.py.

## Cómo lanzar

Ejecución diaria (la normal):

```
cd "C:\Users\Admin\Desktop\Desktop\CarpetaFisica\Data Detective\Mis Casos(Importante)\PROYECTO 5 - FORECASTING RETAIL\02_FORECASTING\07_despliegue"
..\.venv\Scripts\python.exe ejecuciones.py
```

Reentrenamiento (cuando haya datos nuevos o el modelo se degrade):

```
cd "C:\Users\Admin\Desktop\Desktop\CarpetaFisica\Data Detective\Mis Casos(Importante)\PROYECTO 5 - FORECASTING RETAIL\02_FORECASTING\07_despliegue"
..\.venv\Scripts\python.exe reentrenamiento.py
```

Importante: reentrenar primero, ejecutar después. Si reentrenas, ejecuciones.py usará los modelos nuevos solo desde ese momento.

## Contrato del CSV de entrada

1. Separador punto y coma.
2. Fecha en formato dd/mm/yyyy.
3. Columnas que espera crear_variables: store_id, item_id, fecha, event_name_1, event_type_1, sell_price, ventas (los eventos pueden ir vacíos).
4. Debe traer suficientes días de historia para calcular los lags y ventanas.

Si sistemas cambia una columna o el formato de fecha, falla aquí primero.

## Errores típicos

1. FileNotFoundError 'train.pkl' o '.pkl': estás en otra carpeta. Haz cd a 07_despliegue.
2. NameError con una constante: la constante debe estar en funciones.py, no en el script.
3. ModuleNotFoundError: estás usando otro Python. Usa el de .venv.
4. predicciones.csv vacío o raro: revisa fechas del CSV de entrada.

## Llevarlo a otra máquina o a Render

1. Se copia SOLO 07_despliegue (con los pkl dentro).
2. Instalar las mismas versiones de librerías (pandas, scikit-learn, joblib) que en tu .venv. Los pkl no cargan bien con versiones muy distintas.
3. Fijar la carpeta de trabajo en 07_despliegue (Root Directory en Render, "Iniciar en" en el Programador de tareas).

## Cuidado

train.pkl, *.pkl y *.csv están en .gitignore: no suben a GitHub. Si cambias de máquina hay que moverlos a mano.
