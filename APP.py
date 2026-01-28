import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io
import requests

# --- CONFIGURACIÓN DE GOOGLE DRIVE ---
# PEGA AQUÍ TU ID DE ARCHIVO REAL
ID_DRIVE = "1A2B3C4D5E6F7G8H9I0J_EJEMPLO" 
URL_DESCARGA = f"https://docs.google.com/spreadsheets/d/1IlCy67vBvvcj1LrdCtUTJk9EjZADOOqN/edit?usp=sharing&ouid=105747081974090957408&rtpof=true&sd=true"

st.set_page_config(page_title="Dashboard DVP Global", layout="wide")

@st.cache_data(ttl=300)
def cargar_datos_desde_drive(url):
    try:
        # Descargamos el contenido del archivo primero
        respuesta = requests.get(url)
        # Si la respuesta no es 200, hay un problema con el link de Drive
        if respuesta.status_code != 200:
            st.error("Google Drive rechazó la conexión. Revisa que el archivo sea PÚBLICO.")
            return None
        
        # Leemos el contenido binario usando el motor openpyxl
        fichero_excel = pd.ExcelFile(io.BytesIO(respuesta.content), engine='openpyxl')
        return fichero_excel
    except Exception as e:
        st.error(f"Error crítico al leer Excel: {e}")
        return None

# --- EJECUCIÓN PRINCIPAL ---
st.title("📊 Control de Cartera DVP & NYX")

excel_obj = cargar_datos_desde_drive(URL_DESCARGA)

if excel_obj:
    # Obtener nombres de pestañas (países)
    hojas_validas = [h for h in excel_obj.sheet_names if h not in ['Dashboard', 'Hoja 2', 'Hoja 4']]
    
    st.sidebar.header("Filtros Principales")
    pais_sel = st.sidebar.selectbox("🚩 1. Seleccionar País:", hojas_validas)

    # Cargar la hoja seleccionada
    df = pd.read_excel(excel_obj, sheet_name=pais_sel, engine='openpyxl')
    
    # Limpieza de encabezados automática (DVP Colombia y otros)
    if 'Total' not in df.columns and 'TOTAL' not in df.columns:
        df = pd.read_excel(excel_obj, sheet_name=pais_sel, skiprows=1, engine='openpyxl')

    df.columns = df.columns.str.strip()

    # --- MAPEADO DE COLUMNAS SEGÚN TUS ARCHIVOS ---
    col_cliente = next((c for c in df.columns if c in ['Cliente', 'NOMBRE', 'Nombre Receptor']), 'Cliente')
    col_total = next((c for c in df.columns if c.upper() == 'TOTAL'), 'Total')
    col_año = next((c for c in df.columns if c.upper() == 'AÑO'), 'Año')
    col_vence = next((c for c in df.columns if 'vencimiento' in c.lower() or 'Vencimiento' in c), None)
    col_cartera = next((c for c in df.columns if c in ['Cartera', 'Estado', 'Estado de pago']), 'Cartera')

    # Convertir datos
    df[col_total] = pd.to_numeric(df[col_total], errors='coerce').fillna(0)
    
    # Filtro de Año
    if col_año in df.columns:
        df[col_año] = pd.to_numeric(df[col_año], errors='coerce').fillna(0).astype(int)
        lista_años = sorted(df[df[col_año] > 0][col_año].unique(), reverse=True)
        año_sel = st.sidebar.selectbox("📅 2. Seleccionar Año:", ["Todos"] + list(lista_años))
        if año_sel != "Todos":
            df = df[df[col_año] == año_sel]

    # Clasificación de Estados
    hoy = datetime.now()
    def definir_estado(row):
        txt = str(row.get(col_cartera, "")).upper()
        if "CRUCE" in txt: return "🟠 CRUCE DE CUENTAS"
        if "PAGADA" in txt or pd.notnull(row.get('Fecha de Pago')): return "🔵 PAGADA"
        
        f_v = pd.to_datetime(row.get(col_vence), errors='coerce')
        if pd.isnull(f_v): return "⚪ SIN FECHA"
        return "🔴 EN MORA" if f_v < hoy else "🟢 AL DÍA"

    df['Estado_DVP'] = df.apply(definir_estado, axis=1)

    # --- DASHBOARD ---
    st.subheader(f"Análisis: {pais_sel} - Periodo: {año_sel if 'año_sel' in locals() else 'Global'}")
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Cartera Total", f"$ {df[col_total].sum():,.0f}")
    m2.metric("En Mora", f"$ {df[df['Estado_DVP']=='🔴 EN MORA'][col_total].sum():,.0f}")
    m3.metric("Recaudado/Cruzado", f"$ {df[df['Estado_DVP'].isin(['🔵 PAGADA', '🟠 CRUCE DE CUENTAS'])][col_total].sum():,.0f}")

    st.plotly_chart(px.pie(df, values=col_total, names='Estado_DVP', hole=0.4, 
                           color='Estado_DVP', color_discrete_map={
                               "🔵 PAGADA": "#2980B9", "🔴 EN MORA": "#C0392B", 
                               "🟠 CRUCE DE CUENTAS": "#E67E22", "🟢 AL DÍA": "#27AE60"
                           }), use_container_width=True)

    st.dataframe(df[[col_cliente, col_total, 'Estado_DVP']])

else:
    st.warning("No se pudo cargar el archivo. Por favor, revisa el ID del Drive y que el archivo esté compartido públicamente.")