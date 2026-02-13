import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import io

# --- 1. CONFIGURACIÓN Y CONEXIÓN ---
ID_DRIVE = "1IlCy67vBvvcj1LrdCtUTJk9EjZADOOqN" 

st.set_page_config(page_title="Cartera DVPNYX", layout="wide")

# --- ESTILO CSS (TAL CUAL EL TUYO) ---
st.markdown("""
    <style>
    .stApp { background-color: #e3f2fd; }
    [data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 10px 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border: 1px solid #bbdefb;
    }
    [data-testid="stMetricValue"] { font-size: 1.1rem !important; color: #1565c0; font-weight: 700; }
    [data-testid="stMetricLabel"] { 
        font-size: 0.75rem !important; 
        color: #546e7a; 
        text-transform: capitalize; 
    }
    h1, h2, h3 { color: #0d47a1; text-transform: none; }
    .metric-neteada {
        background-color: #ffffff;
        padding: 10px 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border: 1px solid #0d47a1;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    </style>
    """, unsafe_allow_html=True)

# --- LOS 6 CLIENTES EXCLUIDOS ---
CLIENTES_EXCLUIR = [
    "TRADIOH LLC", 
    "N&X TECNOLOGIA Y NEGOCIOS", 
    "NYX DESARROLLADORA DE SOFTWARE Y SOLUCIONES TECNOLOGICAS", 
    "DOUBLE V PARTNERS GUATEMALA SOCIEDAD ANONIMA", 
    "DVP SOFTWARE AND CONSULTING SA DE CV", 
    "DOUBLE V PARTNERS ECUADOR DVP"
]
INTERNOS_CLEAN = [str(c).strip().upper() for c in CLIENTES_EXCLUIR]

@st.cache_data(ttl=300)
def cargar_datos_completos(id_file):
    url = f"https://docs.google.com/spreadsheets/d/{id_file}/export?format=xlsx"
    try:
        response = requests.get(url)
        return pd.read_excel(io.BytesIO(response.content), sheet_name=None, engine='openpyxl')
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

MESES_NOMBRES = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 
                 7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}

# --- 2. CARGA DE DATOS ---
datos_excel = cargar_datos_completos(ID_DRIVE)

if datos_excel:
    hojas_excluir = ['Dashboard', 'Hoja 2', 'Hoja 4', 'altabix', 'ALTABIX', 'Instrucciones']
    hojas_paises = [h for h in datos_excel.keys() if h not in hojas_excluir]
    TASAS_REF = {"COP": 4000, "MXN": 18.5, "GTQ": 7.8, "USD": 1}
    hoy = datetime.now()

    # --- 3. PROCESAMIENTO GLOBAL ---
    resumen_global = []
    for p in hojas_paises:
        df_p = datos_excel[p].copy()
        if 'Total' not in df_p.columns and 'TOTAL' not in df_p.columns:
            df_p.columns = df_p.iloc[0]; df_p = df_p[1:].reset_index(drop=True)
        df_p.columns = [str(c).strip() for c in df_p.columns]
        
        c_tot = next((c for c in df_p.columns if c.upper() == 'TOTAL'), 'Total')
        c_sal = next((c for c in df_p.columns if c.upper() == 'SALDO'), 'Saldo')
        c_mon = next((c for c in df_p.columns if 'Moneda' in c), None)
        c_cli = next((c for c in df_p.columns if c in ['Cliente', 'NOMBRE', 'Nombre Receptor']), 'Cliente')

        if c_tot in df_p.columns:
            df_p['CLI_CLEAN'] = df_p[c_cli].astype(str).str.strip().str.upper()
            # EXCLUSIÓN EN GRÁFICAS
            df_p_ext = df_p[~df_p['CLI_CLEAN'].isin(INTERNOS_CLEAN)].copy()
            
            tasa = TASAS_REF.get(str(df_p[c_mon].iloc[0]).upper() if c_mon and not df_p.empty else "USD", 1)
            v_usd = pd.to_numeric(df_p_ext[c_tot], errors='coerce').fillna(0).sum() / tasa
            s_usd = pd.to_numeric(df_p_ext[c_sal], errors='coerce').fillna(0).sum() / tasa if c_sal in df_p_ext.columns else 0
            resumen_global.append({"País": p, "Venta_Total_USD": v_usd, "Saldo_USD": s_usd})

    st.title("📊 Cartera DVPNYX")
    st.markdown("---")

    df_global = pd.DataFrame(resumen_global)
    df_global['Venta_K'] = df_global['Venta_Total_USD'] / 1000
    df_global['Saldo_K'] = df_global['Saldo_USD'] / 1000

    color_map_paises = {"GUATEMALA": "#4DD0E1", "COLOMBIA": "#1565C0", "MEXICO": "#43A047", "ECUADOR": "#FFB300", "USA": "#5E35B1"}

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        fig_venta = px.bar(df_global, x="País", y="Venta_K", 
                           title="Ventas en USD", color="País", color_discrete_map=color_map_paises)
        fig_venta.update_traces(texttemplate='<b>%{y:.1f} K</b>', textposition='outside', textfont_size=14)
        max_v = df_global['Venta_K'].max() * 1.2 if not df_global.empty else 100
        fig_venta.update_layout(template="plotly_white", yaxis_title="Miles de USD", showlegend=False, yaxis=dict(range=[0, max_v]))
        st.plotly_chart(fig_venta, use_container_width=True)
        
    with col_g2:
        # TÍTULO SOLICITADO
        fig_saldo = px.bar(df_global, x="País", y="Saldo_K", 
                           title="Saldos por cobrar (USD)", color_discrete_sequence=['#e53935'])
        fig_saldo.update_traces(texttemplate='<b>%{y:.1f} K</b>', textposition='outside', textfont_size=14)
        max_s = df_global['Saldo_K'].max() * 1.2 if not df_global.empty else 100
        fig_saldo.update_layout(template="plotly_white", yaxis_title="Miles de USD", yaxis=dict(range=[0, max_s]))
        st.plotly_chart(fig_saldo, use_container_width=True)

    st.markdown("---")

    # --- 4. DETALLE POR PAÍS ---
    st.sidebar.header("Menú de Filtros")
    pais_sel = st.sidebar.selectbox("🚩 Seleccionar País:", hojas_paises)
    df_sel = datos_excel[pais_sel].copy()
    if 'Total' not in df_sel.columns and 'TOTAL' not in df_sel.columns:
        df_sel.columns = df_sel.iloc[0]; df_sel = df_sel[1:].reset_index(drop=True)
    df_sel.columns = [str(c).strip() for c in df_sel.columns]

    col_cli = next((c for c in df_sel.columns if c in ['Cliente', 'NOMBRE', 'Nombre Receptor']), 'Cliente')

    # EXCLUSIÓN EN FILTROS Y TABLAS
    df_sel['CLI_CLEAN'] = df_sel[col_cli].astype(str).str.strip().str.upper()
    df_sel = df_sel[~df_sel['CLI_CLEAN'].isin(INTERNOS_CLEAN)].copy()

    # El resto del código sigue exactamente igual a tu original...
    st.header(f"Gestión Detallada (Externos): {pais_sel}")
    st.dataframe(df_sel, use_container_width=True)

else:
    st.error("Error al cargar datos.")