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
    [data-testid="stMetricLabel"] { 
        font-size: 0.75rem !important; 
        color: #546e7a; 
        text-transform: capitalize; 
    }
    h1, h2, h3 { color: #0d47a1; text-transform: none; }
    </style>
    """, unsafe_allow_html=True)

# LISTA DE EXCLUSIÓN ESTRICTA (INTERCOMPANY)
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

# --- 2. CARGA DE DATOS ---
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

    st.title("📊 Control Financiero 360: Cartera Externa")
    st.markdown("---")

    df_global = pd.DataFrame(resumen_global)
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.plotly_chart(px.bar(df_global, x="País", y="Venta_Total_USD", text_auto=',.0f', title="Venta Externa (USD)", color="País").update_layout(template="plotly_white", paper_bgcolor='rgba(0,0,0,0)'), use_container_width=True)
    with col_g2:
        st.plotly_chart(px.bar(df_global, x="País", y="Saldo_USD", text_auto=',.0f', title="Saldo Pendiente Externo (USD)", color_discrete_sequence=['#e53935']).update_layout(template="plotly_white", paper_bgcolor='rgba(0,0,0,0)'), use_container_width=True)

    st.markdown("---")

    # --- 4. DETALLE POR PAÍS ---
    st.sidebar.header("Menú de Filtros")
    pais_sel = st.sidebar.selectbox("🚩 Seleccionar País:", hojas_paises)
    df_sel = datos_excel[pais_sel].copy()
    if 'Total' not in df_sel.columns and 'TOTAL' not in df_sel.columns:
        df_sel.columns = df_sel.iloc[0]; df_sel = df_sel[1:].reset_index(drop=True)
    df_sel.columns = [str(c).strip() for c in df_sel.columns]

    col_sal = next((c for c in df_sel.columns if c.upper() == 'SALDO'), 'Saldo')
    col_sub = next((c for c in df_sel.columns if c.upper() in ['SUBTOTAL', 'SERVICIOS']), 'Subtotal')
    col_iva = next((c for c in df_sel.columns if c.upper() in ['IVA', 'TOTAL IVA']), 'IVA')
    col_cli = next((c for c in df_sel.columns if c in ['Cliente', 'NOMBRE', 'Nombre Receptor']), 'Cliente')
    col_tot = next((c for c in df_sel.columns if c.upper() == 'TOTAL'), 'Total')
    col_car = next((c for c in df_sel.columns if c in ['Cartera', 'Estado', 'Estado de pago', 'Estatus']), 'Cartera')
    col_ven = next((c for c in df_sel.columns if 'vencimiento' in str(c).lower() or 'Vencimiento' in str(c)), None)

    df_sel['CLI_CLEAN'] = df_sel[col_cli].astype(str).str.strip().str.upper()
    df_sel = df_sel[~df_sel['CLI_CLEAN'].isin(INTERNOS_CLEAN)].copy()

    fin_cols = [col_sub, col_iva, col_tot, col_sal]
    for c in fin_cols:
        if c in df_sel.columns: df_sel[c] = pd.to_numeric(df_sel[c], errors='coerce').fillna(0)

    # Filtros Desplegables
    if 'Año' in df_sel.columns:
        años = ["Todos"] + sorted(list(df_sel['Año'].dropna().unique()), reverse=True)
        año_f = st.sidebar.selectbox("📅 Año:", años)
        if año_f != "Todos": df_sel = df_sel[df_sel['Año'] == año_f]
    
    if 'Mes' in df_sel.columns:
        meses = ["Todos"] + [f"{m} - {MESES_NOMBRES.get(m, 'Mes')}" for m in sorted(list(df_sel['Mes'].dropna().unique()))]
        mes_f = st.sidebar.selectbox("📆 Mes:", meses)
        if mes_f != "Todos": df_sel = df_sel[df_sel['Mes'] == int(mes_f.split(" - ")[0])]

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

    # --- CÁLCULOS GESTIÓN DETALLADA ---
    venta_bruta_total = df_sel[~df_sel['Estado_Final'].isin(["Anulada"])][col_tot].sum()
    valor_nc = df_sel[df_sel['Estado_Final'] == "NC"][col_tot].sum()
    saldo_p = df_sel[col_sal].sum()

    # AJUSTE PEDIDO: El subtotal ahora toma solo la suma de su columna de facturas vigentes
    df_vigentes_solo = df_sel[~df_sel['Estado_Final'].isin(["Anulada", "NC"])]
    subtotal_vigente = df_vigentes_solo[col_sub].sum()
    
    # IVA sigue basándose en facturas vigentes
    iva_vigente = df_vigentes_solo[col_iva].sum()

    st.header(f"Gestión Detallada (Externos): {pais_sel}")
    
    r1c1, r1c2, r1c3, r1c4, r1c5 = st.columns(5)
    r1c1.metric("Venta bruta", f"$ {venta_bruta_total:,.2f}")
    
    with r1c2:
        st.markdown(f"""
            <div style="background-color: white; padding: 10px; border-radius: 10px; border: 1px solid #bbdefb; height: 100%;">
                <p style="color: #546e7a; font-size: 0.75rem; margin: 0; text-transform: capitalize;">Notas crédito</p>
                <p style="color: #d32f2f; font-size: 1.1rem; font-weight: 700; margin: 0;">- $ {valor_nc:,.2f}</p>
            </div>
        """, unsafe_allow_html=True)
    
    r1c3.metric("Saldo pendiente", f"$ {saldo_p:,.2f}")
    r1c4.metric("Monto en mora", f"$ {df_sel[df_sel['Estado_Final']=='🔴 En mora'][col_sal].sum():,.2f}")
    r1c5.metric("Dso (días)", f"{(saldo_p / venta_bruta_total * 360) if venta_bruta_total > 0 else 0:.0f}")

    r2c1, r2c2, r2c3 = st.columns(3)
    r2c1.metric("Subtotal", f"$ {subtotal_vigente:,.2f}")
    r2c2.metric("IVA", f"$ {iva_vigente:,.2f}")
    r2c3.metric("Emitidas", f"{len(df_sel):,d} Und")

    st.markdown("---")
    
    # --- GRÁFICAS Y TABLA MAESTRA ---
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(px.pie(df_sel, values=col_tot, names='Estado_Final', hole=0.5, title="Cartera Externa por Estado ($)", color='Estado_Final', color_discrete_map={"🔵 Pagada": "#1e88e5", "🔴 En mora": "#e53935", "Anulada": "#757575", "NC": "#8e24aa"}).update_layout(paper_bgcolor='rgba(0,0,0,0)'), use_container_width=True)
    with c2:
        df_audit = df_sel['Estado_Final'].apply(lambda x: x if x in ["NC", "Anulada"] else "Vigente").value_counts().reset_index()
        df_audit.columns = ['Tipo', 'Cantidad']
        st.plotly_chart(px.bar(df_audit, x='Cantidad', y='Tipo', orientation='h', title="Auditoría: Tipo de Documento", color='Tipo', color_discrete_map={"NC": "#8e24aa", "Anulada": "#757575", "Vigente": "#43a047"}).update_layout(paper_bgcolor='rgba(0,0,0,0)', showlegend=False), use_container_width=True)

    st.subheader("Listado Maestro (Externos)")
    col_ser = next((c for c in df_sel.columns if c.upper() in ['SERVICIO', 'SERVICIO ']), 'Servicio')
    cols_f = [col_cli, col_ser, col_sub, col_iva, col_tot, col_sal, 'Estado_Final']
    st.dataframe(df_sel[cols_f].sort_values(by=col_sal, ascending=False).style.format({c: "{:,.2f}" for c in fin_cols if c in cols_f}))

else:
    st.error("Error al cargar datos.")