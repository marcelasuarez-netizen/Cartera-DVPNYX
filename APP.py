import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import io

# --- CONFIGURACIÓN ---
ID_DRIVE = "1IlCy67vBvvcj1LrdCtUTJk9EjZADOOqN" 

st.set_page_config(page_title="Dashboard Cartera DVP-NYX", layout="wide")

# CAMBIO CLAVE: Ahora cacheamos los datos procesados, no el objeto ExcelFile
@st.cache_data(ttl=300)
def descargar_y_procesar_hojas(id_file):
    url = f"https://docs.google.com/spreadsheets/d/{id_file}/export?format=xlsx"
    try:
        response = requests.get(url)
        # Leer todas las hojas de una vez y guardarlas en un diccionario
        # Esto sí es serializable por Streamlit
        dict_hojas = pd.read_excel(io.BytesIO(response.content), sheet_name=None, engine='openpyxl')
        return dict_hojas
    except Exception as e:
        st.error(f"Error al conectar con Drive: {e}")
        return None

st.title("📊 Control de Cartera Global DVP-NYX")

# Llamamos a la nueva función
datos_dvp = descargar_y_procesar_hojas(ID_DRIVE)

if datos_dvp:
    # Obtener nombres de las hojas desde el diccionario
    hojas_ignorar = ['Dashboard', 'Hoja 2', 'Hoja 4', 'Instrucciones']
    paises = [h for h in datos_dvp.keys() if h not in hojas_ignorar]
    
    st.sidebar.header("Filtros")
    pais_sel = st.sidebar.selectbox("Selecciona un País:", paises)

    # Obtener el DataFrame directamente del diccionario
    df_crudo = datos_dvp[pais_sel]
    
    # Lógica de limpieza: saltar filas si 'Total' no está en las columnas
    if 'Total' not in df_crudo.columns and 'TOTAL' not in df_crudo.columns:
        # Si la primera fila era basura, tomamos la segunda como cabecera
        df = df_crudo.copy()
        df.columns = df.iloc[0] # La fila 0 pasa a ser el nombre de columna
        df = df[1:] # Quitamos esa fila de los datos
    else:
        df = df_crudo.copy()

    df.columns = df.columns.str.strip()

    # --- El resto de tu lógica de gráficos sigue igual ---
    # (Asegúrate de usar 'df' para tus cálculos)
    
    st.success(f"Dashboard de {pais_sel} cargado con éxito")
    st.dataframe(df.head())

else:
    st.error("No se pudieron cargar los datos desde Google Drive.")