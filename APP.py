import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import io

# --- 1. CONFIGURACIÓN Y CONEXIÓN ---
ID_DRIVE = "1IlCy67vBvvcj1LrdCtUTJk9EjZADOOqN" 

st.set_page_config(page_title="Cartera DVPNYX", layout="wide")

# --- ESTILO CSS INTEGRAL (DISEÑO UX/UI + PODIO COMPACTO) ---
st.markdown("""
    <style>
    .stApp { background-color: #f4f7f9; }
    [data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 8px 12px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border: 1px solid #bbdefb;
    }
    [data-testid="stMetricValue"] { font-size: 1rem !important; color: #1565c0; font-weight: 700; }
    [data-testid="stMetricLabel"] { font-size: 0.7rem !important; color: #546e7a; }
    
    .metric-neteada {
        background-color: #ffffff; padding: 8px 12px; border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); border: 1px solid #0d47a1;
        height: 100%; display: flex; flex-direction: column; justify-content: center;
    }

    /* PODIO COMPACTO PARA SIDEBAR */
    .podio-wrapper { display: flex; justify-content: center; align-items: flex-end; gap: 5px; margin: 10px 0; height: 70px; }
    .podio-block { border-radius: 4px 4px 0 0; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; color: white; font-weight: bold; font-size: 0.75rem; transition: 0.3s; width: 40px; }
    .oro { background: linear-gradient(180deg, #FFD700 0%, #B8860B 100%); height: 60px; }
    .plata { background: linear-gradient(180deg, #C0C0C0 0%, #708090 100%); height: 45px; }
    .bronce { background: linear-gradient(180deg, #CD7F32 0%, #8B4513 100%); height: 35px; }
    .podio-off { background-color: #cfd8dc; color: #90a4ae; height: 20px; }

    /* NOTAS DE SEGUIMIENTO COMPACTAS */
    .notas-container {
        background-color: #fff3cd; padding: 10px; border-radius: 8px;
        border-left: 4px solid #ffc107; margin: 10px 0;
    }
    .nota-item { font-size: 0.75rem; color: #856404; margin-bottom: 2px; font-weight: 600; }
    </style>
    """, unsafe_allow_html=True)

BANDERAS = {
    "COLOMBIA": "https://flagcdn.com/w80/co.png",
    "GUATEMALA": "https://flagcdn.com/w80/gt.png",
    "MEXICO": "https://flagcdn.com/w80/mx.png",
    "ECUADOR": "https://flagcdn.com/w80/ec.png",
    "USA": "https://flagcdn.com/w80/us.png"
}

CLIENTES_EXCLUIR = ["TRADIOH LLC", "N&X TECNOLOGIA Y NEGOCIOS", "NYX DESARROLLADORA DE SOFTWARE Y SOLUCIONES TECNOLOGICAS", 
                    "DOUBLE V PARTNERS GUATEMALA SOCIEDAD ANONIMA", "DVP SOFTWARE AND CONSULTING SA DE CV", "DOUBLE V PARTNERS ECUADOR DVP"]
INTERNOS_CLEAN = [str(c).strip().upper() for c in CLIENTES_EXCLUIR]

@st.cache_data(ttl=300)
def cargar_datos_completos(id_file):
    url = f"https://docs.google.com/spreadsheets/d/{id_file}/export?format=xlsx"
    try:
        response = requests.get(url)
        return pd.read_excel(io.BytesIO(response.content), sheet_name=None, engine='openpyxl')
    except: return None

MESES_NOMBRES = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 
                 7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}

datos_excel = cargar_datos_completos(ID_DRIVE)
if datos_excel:
    hojas_paises = [h for h in datos_excel.keys() if h not in ['Dashboard', 'Hoja 2', 'Hoja 4', 'altabix', 'ALTABIX', 'Instrucciones']]
    TASAS_REF = {"COP": 4000, "MXN": 18.5, "GTQ": 7.8, "USD": 1}
    hoy = datetime.now()

    # --- RANKING GLOBAL ---
    resumen_global = []
    for p in hojas_paises:
        df_p = datos_excel[p].copy()
        if 'Total' not in df_p.columns: df_p.columns = df_p.iloc[0]; df_p = df_p[1:]
        df_p.columns = [str(c).strip() for c in df_p.columns]
        c_tot = next((c for c in df_p.columns if c.upper() == 'TOTAL'), 'Total')
        c_mon = next((c for c in df_p.columns if 'Moneda' in c), None)
        c_cli = next((c for c in df_p.columns if c in ['Cliente', 'NOMBRE', 'Nombre Receptor']), 'Cliente')
        df_p['CLI_CLEAN'] = df_p[c_cli].astype(str).str.strip().str.upper()
        df_p_ext = df_p[~df_p['CLI_CLEAN'].isin(INTERNOS_CLEAN)].copy()
        tasa = TASAS_REF.get(str(df_p[c_mon].iloc[0]).upper() if c_mon and not df_p.empty else "USD", 1)
        v_usd = pd.to_numeric(df_p_ext[c_tot], errors='coerce').fillna(0).sum() / tasa
        resumen_global.append({"País": p, "Venta_Total_USD": v_usd})

    df_rank = pd.DataFrame(resumen_global).sort_values(by="Venta_Total_USD", ascending=False).reset_index(drop=True)
    df_rank['Puesto'] = df_rank.index + 1

    # --- SIDEBAR (4 DESPLEGABLES + PODIO) ---
    st.sidebar.header("Menú de Filtros")
    pais_sel = st.sidebar.selectbox("🚩 País:", hojas_paises)
    
    info_pais = df_rank[df_rank['País'] == pais_sel].iloc[0]
    puesto = info_pais['Puesto']
    st.sidebar.markdown(f"<div style='text-align: center;'><img src='{BANDERAS.get(pais_sel.upper(), '')}' width='45'></div>", unsafe_allow_html=True)

    if puesto <= 3:
        p1, p2, p3 = ("oro" if puesto==1 else "podio-off"), ("plata" if puesto==2 else "podio-off"), ("bronce" if puesto==3 else "podio-off")
        st.sidebar.markdown(f"<div class='podio-wrapper'><div class='podio-block {p2}'>2º</div><div class='podio-block {p1}'>1º</div><div class='podio-block {p3}'>3º</div></div>", unsafe_allow_html=True)
    else:
        st.sidebar.markdown("""<div class="notas-container"><div style="font-weight:bold; font-size:0.75rem;">⚠️ SEGUIMIENTO</div><div class="nota-item">📌 Revisar cartera > 60d</div><div class="nota-item">📌 Priorizar críticos</div></div>""", unsafe_allow_html=True)

    # DATOS DE LA HOJA
    df_sel = datos_excel[pais_sel].copy()
    if 'Total' not in df_sel.columns: df_sel.columns = df_sel.iloc[0]; df_sel = df_sel[1:]
    df_sel.columns = [str(c).strip() for c in df_sel.columns]
    
    col_año = next((c for c in df_sel.columns if 'AÑO' in c.upper()), None)
    col_mes = next((c for c in df_sel.columns if 'MES' in c.upper()), None)
    col_cli = next((c for c in df_sel.columns if c in ['Cliente', 'NOMBRE', 'Nombre Receptor']), 'Cliente')

    # DESPLEGABLES RESTANTES
    if col_año:
        años = ["Todos"] + sorted(list(pd.to_numeric(df_sel[col_año], errors='coerce').dropna().unique().astype(int)), reverse=True)
        año_f = st.sidebar.selectbox("📅 Año:", años)
        if año_f != "Todos": df_sel = df_sel[pd.to_numeric(df_sel[col_año]) == año_f]

    if col_mes:
        meses = ["Todos"] + [f"{m} - {MESES_NOMBRES.get(m)}" for m in sorted(list(pd.to_numeric(df_sel[col_mes], errors='coerce').dropna().unique().astype(int)))]
        mes_f = st.sidebar.selectbox("📆 Mes:", meses)
        if mes_f != "Todos": df_sel = df_sel[pd.to_numeric(df_sel[col_mes]) == int(mes_f.split(" - ")[0])]

    # FILTRO DE CLIENTE (RECUPERADO)
    lista_clientes = ["Todos"] + sorted(list(df_sel[col_cli].dropna().unique()))
    cli_sel = st.sidebar.selectbox("👤 Cliente:", lista_clientes)
    if cli_sel != "Todos": df_sel = df_sel[df_sel[col_cli] == cli_sel]

    # --- DASHBOARD PRINCIPAL ---
    st.title("📊 Cartera DVPNYX")
    st.markdown("---")

    # (Lógica de KPIs y Gráficas exactamente igual a la anterior para no borrar nada)
    col_sal_d = next((c for c in df_sel.columns if c.upper() == 'SALDO'), 'Saldo')
    col_sub_d = next((c for c in df_sel.columns if c.upper() in ['SUBTOTAL', 'SERVICIOS']), 'Subtotal')
    col_tot_d = next((c for c in df_sel.columns if c.upper() == 'TOTAL'), 'Total')
    col_car = next((c for c in df_sel.columns if c in ['Cartera', 'Estado', 'Estatus']), 'Cartera')
    col_ven_d = next((c for c in df_sel.columns if 'vencimiento' in str(c).lower()), None)

    df_sel['Estado_Final'] = df_sel.apply(lambda r: "NC" if "NC" in str(r.get(col_car, "")).upper() else ("Anulada" if any(x in str(r.get(col_car, "")).upper() for x in ["ANULADA", "CANCELADO"]) else ("🔵 Pagada" if pd.to_numeric(r.get(col_sal_d), errors='coerce') == 0 else ("🔴 En mora" if pd.notnull(pd.to_datetime(r.get(col_ven_d), errors='coerce')) and pd.to_datetime(r.get(col_ven_d), errors='coerce') < hoy else "🟢 Al día"))), axis=1)

    st.header(f"Gestión Detallada: {pais_sel}")
    sub_t = pd.to_numeric(df_sel[col_sub_d], errors='coerce').fillna(0).sum()
    nc_v = abs(pd.to_numeric(df_sel[df_sel['Estado_Final']=="NC"][col_sub_d], errors='coerce').fillna(0).sum())
    
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Subtotal", f"$ {sub_t:,.2f}")
    with k2: st.markdown(f"<div style='background-color:white; padding:10px; border-radius:8px; border:1px solid #bbdefb;'><p style='color:#546e7a; font-size:0.75rem; margin:0;'>Notas crédito</p><p style='color:#d32f2f; font-size:1.1rem; font-weight:700; margin:0;'>- $ {nc_v:,.2f}</p></div>", unsafe_allow_html=True)
    k3.metric("Saldo Pend.", f"$ {pd.to_numeric(df_sel[col_sal_d], errors='coerce').sum():,.2f}")
    k4.metric("En Mora", f"$ {pd.to_numeric(df_sel[df_sel['Estado_Final']=='🔴 En mora'][col_sal_d], errors='coerce').sum():,.2f}")

    st.plotly_chart(px.pie(df_sel, values=col_tot_d, names='Estado_Final', hole=0.5, title="Cartera por Estado", color_discrete_sequence=px.colors.qualitative.Pastel), use_container_width=True)
    st.subheader("Listado Maestro")
    st.dataframe(df_sel[[col_cli, col_sub_d, col_tot_d, col_sal_d, 'Estado_Final']].sort_values(by=col_sal_d, ascending=False))
else:
    st.error("Error de carga.")