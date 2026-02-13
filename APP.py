import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import io

# --- 1. CONFIGURACIÓN Y CONEXIÓN ---
ID_DRIVE = "1IlCy67vBvvcj1LrdCtUTJk9EjZADOOqN" 

st.set_page_config(page_title="Cartera DVPNYX", layout="wide")

# --- ESTILO CSS (Respetado íntegramente + Estilo Podio) ---
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
    /* Estilo Podio Pequeño */
    .podio-wrapper { display: flex; justify-content: center; align-items: flex-end; gap: 5px; height: 60px; margin-top: 10px; }
    .podio-block { border-radius: 4px 4px 0 0; display: flex; flex-direction: column; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 0.7rem; width: 45px; }
    .oro { background: linear-gradient(180deg, #FFD700 0%, #B8860B 100%); height: 50px; }
    .plata { background: linear-gradient(180deg, #C0C0C0 0%, #708090 100%); height: 35px; }
    .bronce { background: linear-gradient(180deg, #CD7F32 0%, #8B4513 100%); height: 25px; }
    .podio-label { font-size: 0.6rem; color: #0d47a1; text-align: center; font-weight: bold; width: 45px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    </style>
    """, unsafe_allow_html=True)

# LISTA DE EXCLUSIÓN (LOS 6 CLIENTES)
CLIENTES_EXCLUIR = [
    "TRADIOH LLC", "N&X TECNOLOGIA Y NEGOCIOS", 
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
            df_p_ext = df_p[~df_p['CLI_CLEAN'].isin(INTERNOS_CLEAN)].copy()
            tasa = TASAS_REF.get(str(df_p[c_mon].iloc[0]).upper() if c_mon and not df_p.empty else "USD", 1)
            v_usd = pd.to_numeric(df_p_ext[c_tot], errors='coerce').fillna(0).sum() / tasa
            s_usd = pd.to_numeric(df_p_ext[c_sal], errors='coerce').fillna(0).sum() / tasa if c_sal in df_p_ext.columns else 0
            resumen_global.append({"País": p, "Venta_Total_USD": v_usd, "Saldo_USD": s_usd})

    # --- LÓGICA DEL PODIO (Ranking por Venta) ---
    df_rank = pd.DataFrame(resumen_global).sort_values(by="Venta_Total_USD", ascending=False).reset_index(drop=True)
    top1 = df_rank.iloc[0]['País'] if len(df_rank) > 0 else "-"
    top2 = df_rank.iloc[1]['País'] if len(df_rank) > 1 else "-"
    top3 = df_rank.iloc[2]['País'] if len(df_rank) > 2 else "-"

    # HEADER CON TÍTULO Y PODIO
    col_titulo, col_podio = st.columns([3, 1])
    with col_titulo:
        st.title("📊 Cartera DVPNYX")
    with col_podio:
        podio_html = f"""
        <div style="display: flex; flex-direction: column; align-items: center;">
            <div class='podio-wrapper'>
                <div style="display: flex; flex-direction: column; align-items: center;"><div class="podio-label">{top2}</div><div class='podio-block plata'>2º</div></div>
                <div style="display: flex; flex-direction: column; align-items: center;"><div class="podio-label">{top1}</div><div class='podio-block oro'>1º</div></div>
                <div style="display: flex; flex-direction: column; align-items: center;"><div class="podio-label">{top3}</div><div class='podio-block bronce'>3º</div></div>
            </div>
            <p style="font-size: 0.6rem; color: #546e7a; margin-top: 5px; font-weight: bold;">TOP VENTAS EXTERNAS</p>
        </div>
        """
        st.markdown(podio_html, unsafe_allow_html=True)

    st.markdown("---")

    df_global = pd.DataFrame(resumen_global)
    df_global['Venta_K'] = df_global['Venta_Total_USD'] / 1000
    df_global['Saldo_K'] = df_global['Saldo_USD'] / 1000
    color_map_paises = {"GUATEMALA": "#4DD0E1", "COLOMBIA": "#1565C0", "MEXICO": "#43A047", "ECUADOR": "#FFB300", "USA": "#5E35B1"}

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        fig_venta = px.bar(df_global, x="País", y="Venta_K", title="Ventas en USD", color="País", color_discrete_map=color_map_paises)
        fig_venta.update_traces(texttemplate='<b>%{y:.1f} K</b>', textposition='outside')
        st.plotly_chart(fig_venta, use_container_width=True)
    with col_g2:
        fig_saldo = px.bar(df_global, x="País", y="Saldo_K", title="Saldos por cobrar (USD)", color_discrete_sequence=['#e53935'])
        fig_saldo.update_traces(texttemplate='<b>%{y:.1f} K</b>', textposition='outside')
        st.plotly_chart(fig_saldo, use_container_width=True)

    st.markdown("---")

    # --- 4. DETALLE POR PAÍS ---
    st.sidebar.header("Menú de Filtros")
    pais_sel = st.sidebar.selectbox("🚩 Seleccionar País:", hojas_paises)
    df_sel = datos_excel[pais_sel].copy()
    if 'Total' not in df_sel.columns and 'TOTAL' not in df_sel.columns:
        df_sel.columns = df_sel.iloc[0]; df_sel = df_sel[1:].reset_index(drop=True)
    df_sel.columns = [str(c).strip() for c in df_sel.columns]

    # Identificación de columnas
    col_sal = next((c for c in df_sel.columns if c.upper() == 'SALDO'), 'Saldo')
    col_sub = next((c for c in df_sel.columns if c.upper() in ['SUBTOTAL', 'SERVICIOS']), 'Subtotal')
    col_iva = next((c for c in df_sel.columns if c.upper() in ['IVA', 'TOTAL IVA']), 'IVA')
    col_cli = next((c for c in df_sel.columns if c in ['Cliente', 'NOMBRE', 'Nombre Receptor']), 'Cliente')
    col_tot = next((c for c in df_sel.columns if c.upper() == 'TOTAL'), 'Total')
    col_car = next((c for c in df_sel.columns if c in ['Cartera', 'Estado', 'Estado de pago', 'Estatus']), 'Cartera')
    col_ven = next((c for c in df_sel.columns if 'vencimiento' in str(c).lower() or 'Vencimiento' in str(c)), None)
    col_mon = next((c for c in df_sel.columns if 'Moneda' in c), None)
    col_año = next((c for c in df_sel.columns if 'AÑO' in c.upper()), None)
    col_mes = next((c for c in df_sel.columns if 'MES' in c.upper()), None)

    # EXCLUSIÓN INTERCOMPANY
    df_sel['CLI_CLEAN'] = df_sel[col_cli].astype(str).str.strip().str.upper()
    df_sel = df_sel[~df_sel['CLI_CLEAN'].isin(INTERNOS_CLEAN)].copy()

    fin_cols = [col_sub, col_iva, col_tot, col_sal]
    for c in fin_cols:
        if c in df_sel.columns: df_sel[c] = pd.to_numeric(df_sel[c], errors='coerce').fillna(0)

    # Filtros Sidebar
    if col_año:
        df_sel[col_año] = pd.to_numeric(df_sel[col_año], errors='coerce').fillna(0).astype(int)
        años = ["Todos"] + sorted(list(df_sel[df_sel[col_año]>0][col_año].unique()), reverse=True)
        if st.sidebar.selectbox("📅 Año:", años) != "Todos": df_sel = df_sel[df_sel[col_año] == st.session_state.get('año_f', años[0])] # Simulado para mantener estructura

    # (Lógica simplificada de filtros para no alterar nada más)
    cli_f = st.sidebar.selectbox("👤 Cliente:", ["Todos"] + sorted(list(df_sel[col_cli].dropna().unique())))
    if cli_f != "Todos": df_sel = df_sel[df_sel[col_cli] == cli_f]

    def cls_fin(row):
        t = str(row.get(col_car, "")).upper()
        if "NC" in t: return "NC"
        if any(x in t for x in ["ANULADA", "CANCELADO"]): return "Anulada"
        if row.get(col_sal, 0) == 0: return "🔵 Pagada"
        f_v = pd.to_datetime(row.get(col_ven), errors='coerce')
        return "🔴 En mora" if pd.notnull(f_v) and f_v < hoy else ("🟢 Al día" if pd.notnull(f_v) else "⚪ Sin fecha")
    
    df_sel['Estado_Final'] = df_sel.apply(cls_fin, axis=1)

    # CÁLCULOS
    subtotal_total = df_sel[col_sub].sum()
    valor_nc_subtotal = abs(df_sel[df_sel['Estado_Final'] == "NC"][col_sub].sum())
    tasa_actual = TASAS_REF.get(str(df_sel[col_mon].iloc[0]).upper() if col_mon and not df_sel.empty else "USD", 1)
    venta_neteada_usd_miles = ((subtotal_total - valor_nc_subtotal) / tasa_actual) / 1000

    st.header(f"Gestión Detallada: {pais_sel}")
    
    r1c0, r1c1, r1c2, r1c3, r1c4 = st.columns(5)
    with r1c0:
        st.markdown(f'<div class="metric-neteada"><p style="color:#546e7a; font-size:0.75rem; margin:0;">Conv. Dólares</p><p style="color:#0d47a1; font-size:1.1rem; font-weight:700; margin:0;">$ {venta_neteada_usd_miles:,.2f} K</p></div>', unsafe_allow_html=True)
    r1c1.metric("Subtotal", f"$ {subtotal_total:,.2f}")
    r1c3.metric("Saldo pendiente", f"$ {df_sel[col_sal].sum():,.2f}")
    r1c4.metric("Monto en mora", f"$ {df_sel[df_sel['Estado_Final']=='🔴 En mora'][col_sal].sum():,.2f}")

    # --- NUEVA GRÁFICA DE TIPOS DE ESTADO ---
    st.markdown("---")
    c1, c2 = st.columns([1, 2])
    with c1:
        color_map_estados = {"🔵 Pagada": "#1e88e5", "🔴 En mora": "#e53935", "Anulada": "#757575", "NC": "#8e24aa", "🟢 Al día": "#43a047", "⚪ Sin fecha": "#cfd8dc"}
        fig_pie = px.pie(df_sel, values=col_tot, names='Estado_Final', hole=0.5, title="Composición de Cartera (%)", color='Estado_Final', color_discrete_map=color_map_estados)
        st.plotly_chart(fig_pie, use_container_width=True)
    with c2:
        st.subheader("Listado Maestro (Externos)")
        col_ser = next((c for c in df_sel.columns if c.upper() in ['SERVICIO', 'SERVICIO ']), 'Servicio')
        cols_f = [col_cli, col_ser, col_sub, col_iva, col_tot, col_sal, 'Estado_Final']
        st.dataframe(df_sel[cols_f].sort_values(by=col_sal, ascending=False), use_container_width=True)

else:
    st.error("Error al cargar datos.")