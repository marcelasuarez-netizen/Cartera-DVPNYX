import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import io

# --- CONFIGURACIÓN CON TU ID REAL ---
ID_DRIVE = "1IlCy67vBvvcj1LrdCtUTJk9EjZADOOqN" 

st.set_page_config(page_title="Dashboard Cartera DVP-NYX", layout="wide")

@st.cache_data(ttl=300)
def cargar_excel_dvp(id_file):
    # Enlace de exportación forzada para archivos de Google Drive
    url = f"https://docs.google.com/spreadsheets/d/{id_file}/export?format=xlsx"
    try:
        response = requests.get(url)
        # Usamos openpyxl para leer el contenido binario
        return pd.ExcelFile(io.BytesIO(response.content), engine='openpyxl')
    except Exception as e:
        st.error(f"Error al conectar con Drive: {e}")
        return None

st.title("📊 Control de Cartera Global DVP-NYX")

excel_obj = cargar_excel_dvp(ID_DRIVE)

if excel_obj:
    # Filtramos las hojas para mostrar solo los países
    hojas_ignorar = ['Dashboard', 'Hoja 2', 'Hoja 4', 'Instrucciones']
    paises = [h for h in excel_obj.sheet_names if h not in hojas_ignorar]
    
    st.sidebar.header("Filtros")
    pais_sel = st.sidebar.selectbox("Selecciona un País:", paises)

    # Cargamos la hoja del país seleccionado
    # Saltamos la primera fila si es necesario (tus archivos suelen tener el título en la fila 1)
    df = pd.read_excel(excel_obj, sheet_name=pais_sel, skiprows=1, engine='openpyxl')
    
    # Limpiar nombres de columnas
    df.columns = df.columns.str.strip()

    # Identificar columnas clave (ajustado a tus pestañas como 'DVP Colombia' o 'DVP Ecuador')
    col_cliente = next((c for c in df.columns if c in ['Cliente', 'NOMBRE', 'Nombre Receptor']), 'Cliente')
    col_total = next((c for c in df.columns if c.upper() == 'TOTAL'), 'Total')
    col_vence = next((c for c in df.columns if 'vencimiento' in c.lower() or 'Vencimiento' in c), None)
    col_estado = next((c for c in df.columns if 'Cartera' in c or 'Estado' in c), 'Cartera')

    # Convertir total a número
    df[col_total] = pd.to_numeric(df[col_total], errors='coerce').fillna(0)

    # Mostrar KPIs rápidos
    st.subheader(f"Resumen de Cartera: {pais_sel}")
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Monto Total Facturado", f"$ {df[col_total].sum():,.2f}")
    with c2:
        recaudado = df[df[col_estado].str.contains("PAGADA|Cruce", case=False, na=False)][col_total].sum()
        st.metric("Monto Recaudado", f"$ {recaudado:,.2f}")

    # Gráfico de pastel
    fig = px.pie(df, values=col_total, names=col_estado, title="Distribución de Estados de Pago", hole=0.4)
    st.plotly_chart(fig, use_container_width=True)

    # Tabla Detallada
    st.write("### Detalle de Facturación")
    st.dataframe(df[[col_cliente, col_total, col_estado]].sort_values(by=col_total, ascending=False))

else:
    st.error("No se pudo cargar el archivo. Verifica que en Google Drive esté como 'Cualquier persona con el enlace puede ver'.")