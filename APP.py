import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import io

# --- 1. CONFIGURACIÓN DE LA CONEXIÓN A DRIVE ---
# El ID que me pasaste de tu archivo
ID_DRIVE = "1IlCy67vBvvcj1LrdCtUTJk9EjZADOOqN" 

st.set_page_config(page_title="Sistema de Gestión DVP-NYX", layout="wide")

@st.cache_data(ttl=300) # Se actualiza cada 5 minutos
def cargar_toda_la_cartera(id_file):
    url = f"https://docs.google.com/spreadsheets/d/{id_file}/export?format=xlsx"
    try:
        response = requests.get(url)
        # Cargamos todas las hojas del Excel en un diccionario de DataFrames
        return pd.read_excel(io.BytesIO(response.content), sheet_name=None, engine='openpyxl')
    except Exception as e:
        st.error(f"Error al conectar con Drive: {e}")
        return None

# --- 2. CARGA DE DATOS ---
st.title("📊 Control de Cartera y Facturación Global")
st.markdown("---")

datos_excel = cargar_toda_la_cartera(ID_DRIVE)

if datos_excel:
    # Filtramos las hojas para mostrar solo los países (ignoramos hojas técnicas)
    hojas_ignorar = ['Dashboard', 'Hoja 2', 'Hoja 4', 'Instrucciones']
    hojas_validas = [h for h in datos_excel.keys() if h not in hojas_ignorar]
    
    # --- FILTRO 1: PAÍS (BARRA LATERAL) ---
    st.sidebar.header("Configuración de Filtros")
    pais_sel = st.sidebar.selectbox("🚩 1. Seleccionar País / Operación:", hojas_validas)
    
    # Obtenemos la tabla del país seleccionado
    df = datos_excel[pais_sel].copy()

    # --- 3. LIMPIEZA DINÁMICA DE ENCABEZADOS ---
    # Si la primera fila es basura (títulos vacíos), intentamos detectar la cabecera real
    if 'Total' not in df.columns and 'TOTAL' not in df.columns:
        df.columns = df.iloc[0] # Usamos la primera fila como cabecera
        df = df[1:].reset_index(drop=True) # Quitamos la fila de títulos de los datos
    
    # Limpiar nombres de columnas
    df.columns = [str(c).strip() for c in df.columns]

    # --- 4. MAPEADO DE COLUMNAS (Colombia, Ecuador, Mx, etc.) ---
    col_año = next((c for c in df.columns if c.upper() == 'AÑO'), 'Año')
    col_cliente = next((c for c in df.columns if c in ['Cliente', 'NOMBRE', 'Nombre Receptor']), 'Cliente')
    col_total = next((c for c in df.columns if c.upper() == 'TOTAL'), 'Total')
    col_servicio = next((c for c in df.columns if c.upper() in ['SERVICIO', 'CONCEPTO']), 'Servicio')
    col_vence = next((c for c in df.columns if 'vencimiento' in c.lower() or 'Vencimiento' in c), None)
    col_pago = next((c for c in df.columns if 'pago' in c.lower()), 'Fecha de Pago')
    col_estado_manual = next((c for c in df.columns if c in ['Cartera', 'Estado', 'Estado de pago']), 'Cartera')

    # Convertir formatos
    df[col_total] = pd.to_numeric(df[col_total], errors='coerce').fillna(0)
    if col_vence:
        df[col_vence] = pd.to_datetime(df[col_vence], errors='coerce')
    
    # --- FILTRO 2: AÑO ---
    año_sel = "Todos"
    if col_año in df.columns:
        df[col_año] = pd.to_numeric(df[col_año], errors='coerce').fillna(0).astype(int)
        años = sorted(df[df[col_año] > 0][col_año].unique(), reverse=True)
        año_sel = st.sidebar.selectbox("📅 2. Seleccionar Año:", ["Todos"] + list(años))
        if año_sel != "Todos":
            df = df[df[col_año] == año_sel]

    # --- FILTRO 3: CLIENTE ---
    clientes_lista = sorted(df[col_cliente].dropna().unique())
    cli_sel = st.sidebar.selectbox("👤 3. Seleccionar Cliente:", ["Todos"] + list(clientes_lista))
    if cli_sel != "Todos":
        df = df[df[col_cliente] == cli_sel]

    # --- 5. LÓGICA DE CLASIFICACIÓN (Mora, Al día, Pagada, Cruce) ---
    hoy = datetime.now()

    def clasificar_registro(row):
        txt_estado = str(row.get(col_estado_manual, "")).upper()
        if "CRUCE" in txt_estado: return "🟠 CRUCE DE CUENTAS"
        if "NC" in txt_estado: return "🟣 NOTA CRÉDITO"
        
        txt_pago = str(row.get(col_pago, "")).lower()
        if "PAGADA" in txt_estado or (txt_pago != "" and txt_pago != "nan" and txt_pago != "none"):
            return "🔵 PAGADA"
        
        f_v = row.get(col_vence)
        if pd.isnull(f_v): return "⚪ SIN FECHA"
        return "🔴 EN MORA" if f_v < hoy else "🟢 AL DÍA"

    df['Dashboard_Estado'] = df.apply(clasificar_registro, axis=1)

    # --- 6. KPIs PRINCIPALES ---
    st.header(f"Resumen Financiero: {pais_sel} ({año_sel})")
    m1, m2, m3, m4 = st.columns(4)
    
    m1.metric("Cartera Total", f"$ {df[col_total].sum():,.0f}")
    m2.metric("Monto en Mora", f"$ {df[df['Dashboard_Estado']=='🔴 EN MORA'][col_total].sum():,.0f}", delta="Riesgo", delta_color="inverse")
    m3.metric("Monto Recaudado", f"$ {df[df['Dashboard_Estado'].isin(['🔵 PAGADA', '🟠 CRUCE DE CUENTAS'])][col_total].sum():,.0f}")
    m4.metric("Facturas Emitidas", f"{len(df)} Und")

    st.markdown("---")

    # --- 7. GRÁFICOS ---
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Estado de Cartera (Valor)")
        fig_pie = px.pie(df, values=col_total, names='Dashboard_Estado', hole=0.4,
                         color='Dashboard_Estado', color_discrete_map={
                             "🔵 PAGADA": "#2980B9", "🔴 EN MORA": "#C0392B", 
                             "🟠 CRUCE DE CUENTAS": "#E67E22", "🟢 AL DÍA": "#27AE60", "⚪ SIN FECHA": "#BDC3C7"
                         })
        st.plotly_chart(fig_pie, use_container_width=True)

    with c2:
        st.subheader("Total Facturas por Servicio (Cantidad)")
        serv_count = df[col_servicio].value_counts().reset_index()
        serv_count.columns = ['Servicio', 'Cantidad']
        fig_serv = px.bar(serv_count, x='Cantidad', y='Servicio', orientation='h', 
                          color='Cantidad', text_auto=True, color_continuous_scale='Blues')
        st.plotly_chart(fig_serv, use_container_width=True)

    st.subheader("Volumen de Facturación por Cliente (Top 10)")
    vol_cli = df.groupby(col_cliente).size().reset_index(name='Facturas')
    vol_cli = vol_cli.sort_values(by='Facturas', ascending=False).head(10)
    fig_vol = px.bar(vol_cli, x=col_cliente, y='Facturas', color='Facturas', text_auto=True, color_continuous_scale='Viridis')
    st.plotly_chart(fig_vol, use_container_width=True)

    # --- 8. TABLA DE DETALLE ---
    with st.expander("🔍 Ver listado completo de facturas analizadas"):
        st.dataframe(df[[col_cliente, col_servicio, col_vence, col_total, 'Dashboard_Estado']])

else:
    st.error("No se pudo establecer conexión con los datos de Google Drive.")