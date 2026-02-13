import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import io

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Cartera DVPNYX", layout="wide")

ID_DRIVE = "1IlCy67vBvvcj1LrdCtUTJk9EjZADOOqN" 

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
    [data-testid="stMetricLabel"] { font-size: 0.75rem !important; color: #546e7a; text-transform: capitalize; }
    h1, h2, h3 { color: #0d47a1; text-transform: none; }
    
    /* Estilo Podio Salud */
    .podio-wrapper { display: flex; justify-content: center; align-items: flex-end; gap: 8px; height: 65px; margin-bottom: 5px; }
    .podio-block { border-radius: 4px 4px 0 0; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 0.75rem; width: 45px; }
    .oro { background: linear-gradient(180deg, #FFD700 0%, #B8860B 100%); height: 50px; }
    .plata { background: linear-gradient(180deg, #C0C0C0 0%, #708090 100%); height: 35px; }
    .bronce { background: linear-gradient(180deg, #CD7F32 0%, #8B4513 100%); height: 25px; }
    .podio-name { font-size: 0.6rem; color: #0d47a1; font-weight: bold; text-align: center; width: 45px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    
    .metric-neteada {
        background-color: #ffffff;
        padding: 10px 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border: 1px solid #0d47a1;
        height: 100%;
        display: flex; flex-direction: column; justify-content: center;
    }
    </style>
    """, unsafe_allow_html=True)

# CLIENTES EXCLUIDOS (INTERCOMPANY)
CLIENTES_EXCLUIR = ["TRADIOH LLC", "N&X TECNOLOGIA Y NEGOCIOS", "NYX DESARROLLADORA DE SOFTWARE Y SOLUCIONES TECNOLOGICAS", 
                    "DOUBLE V PARTNERS GUATEMALA SOCIEDAD ANONIMA", "DVP SOFTWARE AND CONSULTING SA DE CV", "DOUBLE V PARTNERS ECUADOR DVP"]
INTERNOS_CLEAN = [str(c).strip().upper() for c in CLIENTES_EXCLUIR]

@st.cache_data(ttl=300)
def cargar_datos_completos(id_file):
    url = f"https://docs.google.com/spreadsheets/d/{id_file}/export?format=xlsx"
    try:
        response = requests.get(url)
        return pd.read_excel(io.BytesIO(response.content), sheet_name=None, engine='openpyxl')
    except Exception as e:
        st.error(f"Error de conexión: {e}"); return None

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
        c_cli = next((c for c in df_p.columns if c in ['Cliente', 'NOMBRE', 'Nombre Receptor']), 'Cliente')
        c_mon = next((c for c in df_p.columns if 'Moneda' in c), None)

        if c_tot in df_p.columns:
            df_p['CLI_CLEAN'] = df_p[c_cli].astype(str).str.strip().str.upper()
            df_p_ext = df_p[~df_p['CLI_CLEAN'].isin(INTERNOS_CLEAN)].copy()
            
            tasa = TASAS_REF.get(str(df_p[c_mon].iloc[0]).upper() if c_mon and not df_p.empty else "USD", 1)
            v_usd = pd.to_numeric(df_p_ext[c_tot], errors='coerce').fillna(0).sum() / tasa
            s_usd = pd.to_numeric(df_p_ext[c_sal], errors='coerce').fillna(0).sum() / tasa if c_sal in df_p_ext.columns else 0
            
            p_sano = ((v_usd - s_usd) / v_usd * 100) if v_usd > 0 else 0
            resumen_global.append({"País": p, "Venta_Total_USD": v_usd, "Saldo_USD": s_usd, "Salud": p_sano})

    # PODIO SALUD
    df_salud = pd.DataFrame(resumen_global).sort_values(by="Salud", ascending=False).reset_index(drop=True)
    h1 = df_salud.iloc[0]['País'] if len(df_salud)>0 else "-"
    h2 = df_salud.iloc[1]['País'] if len(df_salud)>1 else "-"
    h3 = df_salud.iloc[2]['País'] if len(df_salud)>2 else "-"

    head1, head2 = st.columns([3, 1])
    with head1: st.title("📊 Cartera DVPNYX")
    with head2:
        st.markdown(f"""<div style="text-align:right"><div class='podio-wrapper'>
            <div style="display:flex; flex-direction:column; align-items:center"><div class="podio-name">{h2}</div><div class='podio-block plata'>2º</div></div>
            <div style="display:flex; flex-direction:column; align-items:center"><div class="podio-name">{h1}</div><div class='podio-block oro'>1º</div></div>
            <div style="display:flex; flex-direction:column; align-items:center"><div class="podio-name">{h3}</div><div class='podio-block bronce'>3º</div></div>
        </div><p style="font-size:0.55rem; color:#546e7a; margin-top:2px; font-weight:bold; text-align:center">SALUD DE CARTERA</p></div>""", unsafe_allow_html=True)

    st.markdown("---")

    # --- 4. SIDEBAR CON FILTROS Y GRÁFICA COMPARATIVA ---
    st.sidebar.header("Menú de Filtros")
    pais_sel = st.sidebar.selectbox("🚩 Selección País:", hojas_paises)
    df_sel = datos_excel[pais_sel].copy()
    if 'Total' not in df_sel.columns: df_sel.columns = df_sel.iloc[0]; df_sel = df_sel[1:]
    df_sel.columns = [str(c).strip() for c in df_sel.columns]

    # Identificación de columnas
    col_sal = next((c for c in df_sel.columns if c.upper() == 'SALDO'), 'Saldo')
    col_sub = next((c for c in df_sel.columns if c.upper() in ['SUBTOTAL', 'SERVICIOS']), 'Subtotal')
    col_cli = next((c for c in df_sel.columns if c in ['Cliente', 'NOMBRE']), 'Cliente')
    col_tot = next((c for c in df_sel.columns if c.upper() == 'TOTAL'), 'Total')
    col_car = next((c for c in df_sel.columns if c in ['Cartera', 'Estado']), 'Cartera')

    # Exclusión
    df_sel['CLI_CLEAN'] = df_sel[col_cli].astype(str).str.strip().str.upper()
    df_sel = df_sel[~df_sel['CLI_CLEAN'].isin(INTERNOS_CLEAN)].copy()

    # Otros filtros sidebar
    cli_f = st.sidebar.selectbox("👤 Cliente:", ["Todos"] + sorted(list(df_sel[col_cli].dropna().unique())))
    if cli_f != "Todos": df_sel = df_sel[df_sel[col_cli] == cli_f]

    # --- GRÁFICA COMPARATIVA EN SIDEBAR ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Salud del Recaudo")
    
    sub_total = pd.to_numeric(df_sel[col_sub], errors='coerce').fillna(0).sum()
    nc_total = abs(pd.to_numeric(df_sel[df_sel[col_car].astype(str).str.contains('NC', case=False, na=False)][col_sub], errors='coerce').fillna(0).sum())
    val_neteado = sub_total - nc_total
    val_pagado = pd.to_numeric(df_sel[col_tot], errors='coerce').fillna(0).sum() - pd.to_numeric(df_sel[col_sal], errors='coerce').fillna(0).sum()

    df_comp_sidebar = pd.DataFrame({
        "Concepto": ["Neteado", "Pagado"],
        "Valor": [val_neteado, val_pagado]
    })
    
    fig_side = px.bar(df_comp_sidebar, x="Concepto", y="Valor", color="Concepto", 
                      color_discrete_map={"Neteado": "#1565C0", "Pagado": "#43A047"},
                      text_auto='.2s')
    fig_side.update_layout(showlegend=False, height=250, margin=dict(l=10, r=10, t=30, b=10))
    st.sidebar.plotly_chart(fig_side, use_container_width=True)

    # --- 5. CUERPO PRINCIPAL (DETALLE) ---
    st.header(f"Gestión Detallada: {pais_sel}")
    # (Tus métricas blancas y tabla maestra siguen aquí abajo...)
    st.dataframe(df_sel, use_container_width=True)

else:
    st.error("Error al cargar datos.")