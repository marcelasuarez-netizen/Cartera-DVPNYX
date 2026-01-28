import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import io

# --- CONFIGURACIÓN DE CONEXIÓN ---
# 1. PEGA AQUÍ TU ID (el código largo de tu enlace de Drive)
ID_DRIVE = "https://docs.google.com/spreadsheets/d/1IlCy67vBvvcj1LrdCtUTJk9EjZADOOqN/edit?usp=sharing&ouid=105747081974090957408&rtpof=true&sd=true" 

st.set_page_config(page_title="Dashboard DVP Global", layout="wide")

@st.cache_data(ttl=300)
def descargar_excel_drive(id_archivo):
    # Intentamos primero como archivo de Excel subido (.xlsx)
    url_directa = f"https://drive.google.com/uc?export=download&id={id_archivo}"
    # Si eso falla (porque es un Google Sheet nativo), usamos el link de exportación
    url_export = f"https://docs.google.com/spreadsheets/d/{id_archivo}/export?format=xlsx"
    
    sesion = requests.Session()
    
    try:
        # Intento 1: Descarga directa
        respuesta = sesion.get(url_directa, stream=True)
        # Si Google pide confirmación de virus, buscamos el token
        if "confirm=" in respuesta.text:
            token = [v for k, v in respuesta.cookies.items() if k.startswith("download_warning")][0]
            respuesta = sesion.get(url_directa + f"&confirm={token}", stream=True)
        
        # Si el contenido parece HTML (error), intentamos el método de exportación
        if "html" in respuesta.headers.get('Content-Type', '').lower():
            respuesta = sesion.get(url_export)
            
        return pd.ExcelFile(io.BytesIO(respuesta.content), engine='openpyxl')
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

# --- INICIO DE LA APP ---
st.title("📊 Control de Cartera DVP & NYX")

if ID_DRIVE == "TU_ID_AQUÍ":
    st.warning("⚠️ Por favor, pon el ID de tu archivo de Drive en el código (línea 11).")
else:
    excel_obj = descargar_excel_drive(ID_DRIVE)

    if excel_obj:
        # Filtrar pestañas reales
        hojas = [h for h in excel_obj.sheet_names if h not in ['Dashboard', 'Hoja 2', 'Hoja 4']]
        pais_sel = st.sidebar.selectbox("🚩 Seleccionar País:", hojas)

        # Leer datos de la hoja
        df = pd.read_excel(excel_obj, sheet_name=pais_sel, engine='openpyxl')
        
        # Si la tabla tiene filas vacías arriba, las saltamos
        if 'Total' not in df.columns and 'TOTAL' not in df.columns:
            df = pd.read_excel(excel_obj, sheet_name=pais_sel, skiprows=1, engine='openpyxl')

        df.columns = df.columns.str.strip()
        
        # --- (Aquí sigue el resto de tu lógica de gráficos que ya tenemos) ---
        st.success(f"Datos de {pais_sel} cargados correctamente.")
        st.dataframe(df.head())
    else:
        st.error("❌ No se pudo leer el archivo. Revisa que el ID sea correcto y el archivo sea PÚBLICO.")