import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import io

# --- 1. CONFIGURACIÓN Y CONEXIÓN ---
ID_DRIVE = "1IlCy67vBvvcj1LrdCtUTJk9EjZADOOqN" 

st.set_page_config(page_title="Dashboard Cartera DVP-NYX 360", layout="wide")

# --- ESTILO CSS ---
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
    /* Estilo para las etiquetas en minúsculas */
    [data-testid="stMetricLabel"] { font-size: 0.75rem !important; color: #546e7a; text-transform: lowercase; }
    h1, h2, h3 { color: #0d47a1; }
    </style>
    """, unsafe_allow_html=True)

# LISTA DE EXCLUSIÓN ESTRICTA (INTERCOMPANY)
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
st.title("📊 Control Financiero 360: Cartera Externa")
st.markdown("---")

datos_excel = cargar_datos_completos(ID_DRIVE)

if datos_excel:
    hojas_excluir = ['Dashboard', 'Hoja 2', 'Hoja 4', 'altabix', 'ALTABIX', 'Instrucciones']
    hojas_paises = [h for h in datos_excel.keys() if h not in hojas_excluir]
    TASAS_REF = {"COP": 4000, "MXN": 18.5, "GTQ": 7.8, "USD": 1}
    hoy = datetime.now()

    # --- 3. PROCESAMIENTO GLOBAL USD ---
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

    df_global = pd.DataFrame(resumen_global)
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.plotly_chart(px.bar(df_global, x="País", y="Venta_Total_USD", text_auto=',.0f', title="venta externa (usd)", color="País").update_layout(template="plotly_white", paper_bgcolor='rgba(0,0,0,0)'), use_container_width=True)
    with col_g2:
        st.plotly_chart(px.bar(df_global, x="País", y="Saldo_USD", text_auto=',.0f', title="saldo pendiente externo (usd)", color_discrete_sequence=['#e53935']).update_layout(template="plotly_white", paper_bgcolor='rgba(0,0,0,0)'), use_container_width=True)

    st.markdown("---")

    # --- 4. DETALLE POR PAÍS ---
    pais_sel = st.sidebar.selectbox("🚩 país:", hojas_paises)
    df_sel = datos_excel[pais_sel].copy()
    if 'Total' not in df_sel.columns and 'TOTAL' not in df_sel.columns:
        df_sel.columns = df_sel.iloc[0]; df_sel = df_sel[1:].reset_index(drop=True)
    df_sel.columns = [str(c).strip() for c in df_sel.columns]

    col_sal = next((c for c in df_sel.columns if c.upper() == 'SALDO'), 'Saldo')
    col_sub = next((c for c in df_sel.columns if c.upper() in ['SUBTOTAL', 'SERVICIOS']), 'Subtotal')
    col_iva = next((c for c in df_sel.columns if c.upper() in ['IVA', 'TOTAL IVA']), 'IVA')
    col_año = next((c for c in df_sel.columns if c.upper() in ['AÑO', 'Año']), 'Año')
    col_mes = next((c for c in df_sel.columns if c.upper() == 'MES'), 'Mes')
    col_cli = next((c for c in df_sel.columns if c in ['Cliente', 'NOMBRE', 'Nombre Receptor']), 'Cliente')
    col_tot = next((c for c in df_sel.columns if c.upper() == 'TOTAL'), 'Total')
    col_ser = next((c for c in df_sel.columns if c.upper() in ['SERVICIO', 'SERVICIO ']), 'Servicio')
    col_car = next((c for c in df_sel.columns if c in ['Cartera', 'Estado', 'Estado de pago', 'Estatus']), 'Cartera')
    col_ven = next((c for c in df_sel.columns if 'vencimiento' in str(c).lower() or 'Vencimiento' in str(c)), None)

    # Exclusión Intercompany
    df_sel['CLI_CLEAN'] = df_sel[col_cli].astype(str).str.strip().str.upper()
    df_sel = df_sel[~df_sel['CLI_CLEAN'].isin(INTERNOS_CLEAN)].copy()

    # Unificación de minúsculas en Clientes y Servicios
    df_sel[col_cli] = df_sel[col_cli].astype(str).str.strip().str.title()
    if col_ser in df_sel.columns:
        df_sel[col_ser] = df_sel[col_ser].astype(str).str.strip().str.lower()

    fin_cols = [col_sub, col_iva, col_tot, col_sal]
    for c in fin_cols:
        if c in df_sel.columns: df_sel[c] = pd.to_numeric(df_sel[c], errors='coerce').fillna(0)

    if col_año in df_sel.columns:
        df_sel[col_año] = pd.to_numeric(df_sel[col_año], errors='coerce').fillna(0).astype(int)
        año_f = st.sidebar.selectbox("📅 año:", ["Todos"] + sorted(list(df_sel[df_sel[col_año]>0][col_año].unique()), reverse=True))
        if año_f != "Todos": df_sel = df_sel[df_sel[col_año] == año_f]
    
    cli_f = st.sidebar.selectbox("👤 cliente:", ["Todos"] + sorted(list(df_sel[col_cli].dropna().unique())))
    if cli_f != "Todos": df_sel = df_sel[df_sel[col_cli] == cli_f]

    def cls_fin(row):
        t = str(row.get(col_car, "")).upper()
        if "NC" in t: return "nc"
        if any(x in t for x in ["ANULADA", "CANCELADO"]): return "anulada"
        if row.get(col_sal, 0) == 0: return "🔵 pagada"
        f_v = pd.to_datetime(row.get(col_ven), errors='coerce')
        return "🔴 en mora" if pd.notnull(f_v) and f_v < hoy else ("🟢 al día" if pd.notnull(f_v) else "⚪ sin fecha")
    
    df_sel['Estado_Final'] = df_sel.apply(cls_fin, axis=1)

    st.header(f"gestión detallada (externos): {pais_sel.lower()}")
    
    # KPIs en minúsculas excepto IVA
    r1c1, r1c2, r1c3, r1c4, r1c5 = st.columns(5)
    v_bruta = df_sel[~df_sel['Estado_Final'].isin(["nc", "anulada"])][col_tot].sum()
    saldo_p = df_sel[col_sal].sum()
    
    r1c1.metric("venta bruta (vig)", f"$ {v_bruta:,.2f}")
    r1c2.metric("saldo pendiente", f"$ {saldo_p:,.2f}")
    r1c3.metric("monto en mora", f"$ {df_sel[df_sel['Estado_Final']=='🔴 en mora'][col_sal].sum():,.2f}")
    r1c4.metric("dso (días)", f"{(saldo_p / v_bruta * 360) if v_bruta > 0 else 0:.0f}")
    r1c5.metric("emitidas", f"{len(df_sel):,d} und")

    r2c1, r2c2 = st.columns(2)
    r2c1.metric("subtotal", f"$ {df_sel[col_sub].sum():,.2f}")
    # Única etiqueta en MAYÚSCULAS según petición
    r2c2.metric("IVA", f"$ {df_sel[col_iva].sum():,.2f}")

    st.markdown("---")
    
    # Gráficas con etiquetas unificadas
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(px.pie(df_sel, values=col_tot, names='Estado_Final', hole=0.5, title="cartera externa por estado ($)", color='Estado_Final').update_layout(paper_bgcolor='rgba(0,0,0,0)'), use_container_width=True)
    with c2:
        df_audit = df_sel['Estado_Final'].apply(lambda x: x if x in ["nc", "anulada"] else "vigente").value_counts().reset_index()
        df_audit.columns = ['tipo', 'cantidad']
        st.plotly_chart(px.bar(df_audit, x='cantidad', y='tipo', orientation='h', title="auditoría: tipo de documento").update_layout(paper_bgcolor='rgba(0,0,0,0)', showlegend=False), use_container_width=True)

    st.subheader("listado maestro (externos)")
    # Columnas de tabla
    cols_f = [col_cli, col_ser, col_sub, col_iva, col_tot, col_sal, 'Estado_Final']
    
    # Renombrar columnas solo para visualización
    df_display = df_sel[cols_f].copy()
    df_display.columns = ['cliente', 'servicio', 'subtotal', 'IVA', 'total', 'saldo', 'estado']
    
    st.dataframe(df_display.sort_values(by='saldo', ascending=False).style.format({
        'subtotal': "{:,.2f}", 'IVA': "{:,.2f}", 'total': "{:,.2f}", 'saldo': "{:,.2f}"
    }))

else:
    st.error("error al cargar datos.")