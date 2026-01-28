import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIGURACIÓN DE GOOGLE DRIVE ---
# REEMPLAZA ESTO CON TU ID DE ARCHIVO REAL
ID_DRIVE = "TU_ID_AQUÍ" 
URL_DESCARGA = f"https://docs.google.com/spreadsheets/d/1IlCy67vBvvcj1LrdCtUTJk9EjZADOOqN/edit?usp=sharing&ouid=105747081974090957408&rtpof=true&sd=true"

st.set_page_config(page_title="Dashboard Cartera DVP-NYX", layout="wide")

@st.cache_data(ttl=300) # Se actualiza cada 5 minutos
def obtener_datos():
    # Leemos todas las pestañas del Excel
    return pd.read_excel(URL_DESCARGA, sheet_name=None)

try:
    dict_hojas = obtener_datos()
    hojas_validas = [h for h in dict_hojas.keys() if h not in ['Dashboard', 'Hoja 2', 'Hoja 4']]

    st.sidebar.title("Filtros de Cartera")
    pais_sel = st.sidebar.selectbox("🚩 1. Seleccionar País:", hojas_validas)
    
    # Procesar hoja seleccionada
    df = dict_hojas[pais_sel]
    
    # Limpieza: Si no encuentra 'Total', saltamos filas (común en tus Excels)
    if 'Total' not in df.columns and 'TOTAL' not in df.columns:
        df = pd.read_excel(URL_DESCARGA, sheet_name=pais_sel, skiprows=1)
    
    df.columns = df.columns.str.strip()

    # Mapeo de columnas dinámico
    col_año = next((c for c in df.columns if c.upper() == 'AÑO'), 'Año')
    col_cliente = next((c for c in df.columns if c in ['Cliente', 'NOMBRE', 'Nombre Receptor']), 'Cliente')
    col_total = next((c for c in df.columns if c.upper() == 'TOTAL'), 'Total')
    col_vence = next((c for c in df.columns if 'vencimiento' in c.lower() or 'Vencimiento' in c), None)

    # Filtro de Año (usando la columna de tu Excel)
    if col_año in df.columns:
        df[col_año] = pd.to_numeric(df[col_año], errors='coerce').fillna(0).astype(int)
        años = sorted(df[df[col_año] > 0][col_año].unique(), reverse=True)
        año_sel = st.sidebar.selectbox("📅 2. Seleccionar Año:", ["Todos"] + list(años))
        if año_sel != "Todos":
            df = df[df[col_año] == año_sel]

    # Clasificación de Estados
    hoy = datetime.now()
    def clasificar(row):
        txt_cartera = str(row.get('Cartera', "")).upper()
        if "CRUCE" in txt_cartera: return "🟠 CRUCE DE CUENTAS"
        if "PAGADA" in txt_cartera or "PAGADA" in str(row.get('Estado', "")).upper(): return "🔵 PAGADA"
        
        f_v = pd.to_datetime(row.get(col_vence), errors='coerce')
        if pd.isnull(f_v): return "⚪ SIN DATOS"
        return "🔴 EN MORA" if f_v < hoy else "🟢 AL DÍA"

    df['Estado_Final'] = df.apply(clasificar, axis=1)

    # Visualización de KPIs
    st.header(f"Cartera: {pais_sel}")
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Facturado", f"$ {df[col_total].sum():,.0f}")
    m2.metric("En Mora", f"$ {df[df['Estado_Final']=='🔴 EN MORA'][col_total].sum():,.0f}")
    m3.metric("Recaudado/Cruce", f"$ {df[df['Estado_Final'].isin(['🔵 PAGADA', '🟠 CRUCE DE CUENTAS'])][col_total].sum():,.0f}")

    st.plotly_chart(px.pie(df, values=col_total, names='Estado_Final', hole=0.4), use_container_width=True)
    st.dataframe(df[[col_cliente, col_total, 'Estado_Final']])

except Exception as e:
    st.error(f"Error: {e}. Verifica el ID del Drive y que el archivo sea público.")