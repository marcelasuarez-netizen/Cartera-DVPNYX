Entendido perfectamente. He revisado el código para asegurar que el Podio Dinámico, las Banderas y los Tres Desplegables (País, Año y Mes) convivan perfectamente en la barra lateral sin que uno borre al otro.

Aquí tienes el código completo y unificado. He organizado el Sidebar para que primero aparezca la identidad del país (Bandera + Nombre), luego el Podio o las Notas de Seguimiento, y finalmente los filtros de tiempo.

Python
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import io

# --- 1. CONFIGURACIÓN Y CONEXIÓN ---
ID_DRIVE = "1IlCy67vBvvcj1LrdCtUTJk9EjZADOOqN" 

st.set_page_config(page_title="Cartera DVPNYX", layout="wide")

# --- ESTILO CSS INTEGRAL (DISEÑO UX/UI + PODIO + MÉTRICAS) ---
st.markdown("""
    <style>
    .stApp { background-color: #f4f7f9; }
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
    
    .metric-neteada {
        background-color: #ffffff; padding: 10px 15px; border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); border: 1px solid #0d47a1;
        height: 100%; display: flex; flex-direction: column; justify-content: center;
    }

    /* ESTILOS DEL PODIO DINÁMICO UX */
    .podio-wrapper { display: flex; justify-content: center; align-items: flex-end; gap: 10px; margin: 15px 0; height: 110px; }
    .podio-block { border-radius: 6px 6px 0 0; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; color: white; font-weight: bold; font-size: 1rem; transition: 0.3s; width: 55px; }
    .oro { background: linear-gradient(180deg, #FFD700 0%, #B8860B 100%); height: 90px; box-shadow: 0 4px 12px rgba(218,165,32,0.5); }
    .plata { background: linear-gradient(180deg, #C0C0C0 0%, #708090 100%); height: 70px; }
    .bronce { background: linear-gradient(180deg, #CD7F32 0%, #8B4513 100%); height: 50px; }
    .podio-off { background-color: #cfd8dc; color: #90a4ae; height: 35px; }

    /* PANEL DE SEGUIMIENTO AMARILLO */
    .notas-container {
        background-color: #fff3cd; padding: 15px; border-radius: 10px;
        border-left: 6px solid #ffc107; margin: 15px 0;
    }
    .nota-item { font-size: 0.85rem; color: #856404; margin-bottom: 5px; font-weight: 600; }
    </style>
    """, unsafe_allow_html=True)

# DICCIONARIO DE BANDERAS
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

# --- 2. PROCESAMIENTO Y RANKING ---
datos_excel = cargar_datos_completos(ID_DRIVE)
if datos_excel:
    hojas_paises = [h for h in datos_excel.keys() if h not in ['Dashboard', 'Hoja 2', 'Hoja 4', 'altabix', 'ALTABIX', 'Instrucciones']]
    TASAS_REF = {"COP": 4000, "MXN": 18.5, "GTQ": 7.8, "USD": 1}
    hoy = datetime.now()

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

        df_p['CLI_CLEAN'] = df_p[c_cli].astype(str).str.strip().str.upper()
        df_p_ext = df_p[~df_p['CLI_CLEAN'].isin(INTERNOS_CLEAN)].copy()
        tasa = TASAS_REF.get(str(df_p[c_mon].iloc[0]).upper() if c_mon and not df_p.empty else "USD", 1)
        v_usd = pd.to_numeric(df_p_ext[c_tot], errors='coerce').fillna(0).sum() / tasa
        s_usd = pd.to_numeric(df_p_ext[c_sal], errors='coerce').fillna(0).sum() / tasa
        resumen_global.append({"País": p, "Venta_Total_USD": v_usd, "Saldo_USD": s_usd})

    df_rank = pd.DataFrame(resumen_global).sort_values(by="Venta_Total_USD", ascending=False).reset_index(drop=True)
    df_rank['Puesto'] = df_rank.index + 1
    df_rank['Venta_K'] = df_rank['Venta_Total_USD'] / 1000
    df_rank['Saldo_K'] = df_rank['Saldo_USD'] / 1000

    # --- 3. SIDEBAR INTEGRAL (BANDERAS + PODIO + 3 DESPLEGABLES) ---
    st.sidebar.header("Menú de Filtros")
    
    # DESPLEGABLE 1: PAÍS
    pais_sel = st.sidebar.selectbox("🚩 Seleccionar País:", hojas_paises)
    
    # Identidad Visual
    info_pais = df_rank[df_rank['País'] == pais_sel].iloc[0]
    puesto = info_pais['Puesto']
    bandera = BANDERAS.get(pais_sel.upper(), "")
    st.sidebar.markdown(f"<div style='text-align: center;'><img src='{bandera}' width='65'><br><b style='font-size:1.3rem; color:#0d47a1;'>{pais_sel}</b></div>", unsafe_allow_html=True)

    # COMPONENTE PODIO / NOTAS
    if puesto <= 3:
        p1_cls = "oro" if puesto == 1 else "podio-off"
        p2_cls = "plata" if puesto == 2 else "podio-off"
        p3_cls = "bronce" if puesto == 3 else "podio-off"
        podio_html = f"<div class='podio-wrapper'><div class='podio-block {p2_cls}'>2º</div><div class='podio-block {p1_cls}'>1º</div><div class='podio-block {p3_cls}'>3º</div></div>"
        st.sidebar.markdown(podio_html, unsafe_allow_html=True)
        st.sidebar.success({1: "🥇 Líder de Cartera", 2: "🥈 Desempeño Destacado", 3: "🥉 Top 3 del período"}[puesto])
    else:
        st.sidebar.markdown("""<div class="notas-container"><div style="font-weight:bold; margin-bottom:8px;">⚠️ SEGUIMIENTO OPERATIVO</div><div class="nota-item">📌 Revisar cartera > 60 días</div><div class="nota-item">📌 Validar acuerdos de pago</div><div class="nota-item">📌 Priorizar clientes críticos</div></div>""", unsafe_allow_html=True)

    st.sidebar.markdown("---")

    # CARGA DE HOJA SELECCIONADA PARA FILTROS DE TIEMPO
    df_sel = datos_excel[pais_sel].copy()
    if 'Total' not in df_sel.columns and 'TOTAL' not in df_sel.columns:
        df_sel.columns = df_sel.iloc[0]; df_sel = df_sel[1:].reset_index(drop=True)
    df_sel.columns = [str(c).strip() for c in df_sel.columns]
    
    col_año = next((c for c in df_sel.columns if 'AÑO' in c.upper()), None)
    col_mes = next((c for c in df_sel.columns if 'MES' in c.upper()), None)

    # DESPLEGABLE 2: AÑO
    if col_año:
        lista_años = ["Todos"] + sorted(list(pd.to_numeric(df_sel[col_año], errors='coerce').dropna().unique().astype(int)), reverse=True)
        año_f = st.sidebar.selectbox("📅 Seleccionar Año:", lista_años)
        if año_f != "Todos": df_sel = df_sel[pd.to_numeric(df_sel[col_año]) == año_f]

    # DESPLEGABLE 3: MES
    if col_mes:
        lista_meses = sorted(list(pd.to_numeric(df_sel[col_mes], errors='coerce').dropna().unique().astype(int)))
        meses_opc = ["Todos"] + [f"{m} - {MESES_NOMBRES.get(m)}" for m in lista_meses]
        mes_f = st.sidebar.selectbox("📆 Seleccionar Mes:", meses_opc)
        if mes_f != "Todos": df_sel = df_sel[pd.to_numeric(df_sel[col_mes]) == int(mes_f.split(" - ")[0])]

    # --- 4. DASHBOARD GLOBAL ---
    st.title("📊 Cartera DVPNYX")
    st.markdown("---")

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        fig_v = px.bar(df_rank, x="País", y="Venta_K", title="Ventas en USD (K)", color="País", 
                     color_discrete_map={"COLOMBIA":"#1565C0","GUATEMALA":"#4DD0E1","MEXICO":"#43A047","ECUADOR":"#FFB300","USA":"#5E35B1"})
        fig_v.update_traces(texttemplate='<b>%{y:.1f} K</b>', textposition='outside', textfont_size=14)
        fig_v.update_layout(yaxis=dict(range=[0, df_rank['Venta_K'].max()*1.2]), showlegend=False, template="plotly_white")
        st.plotly_chart(fig_v, use_container_width=True)
    with col_g2:
        fig_s = px.bar(df_rank, x="País", y="Saldo_K", title="Saldo Pendiente (USD K)", color_discrete_sequence=['#e53935'])
        fig_s.update_traces(texttemplate='<b>%{y:.1f} K</b>', textposition='outside', textfont_size=14)
        fig_s.update_layout(yaxis=dict(range=[0, df_rank['Saldo_K'].max()*1.2]), template="plotly_white")
        st.plotly_chart(fig_s, use_container_width=True)

    st.markdown("---")

    # --- 5. GESTIÓN DETALLADA ---
    col_car = next((c for c in df_sel.columns if c in ['Cartera', 'Estado', 'Estatus']), 'Cartera')
    col_sal_d = next((c for c in df_sel.columns if c.upper() == 'SALDO'), 'Saldo')
    col_sub_d = next((c for c in df_sel.columns if c.upper() in ['SUBTOTAL', 'SERVICIOS']), 'Subtotal')
    col_iva_d = next((c for c in df_sel.columns if c.upper() in ['IVA', 'TOTAL IVA']), 'IVA')
    col_tot_d = next((c for c in df_sel.columns if c.upper() == 'TOTAL'), 'Total')
    col_ven_d = next((c for c in df_sel.columns if 'vencimiento' in str(c).lower()), None)
    
    df_sel['Estado_Final'] = df_sel.apply(lambda r: "NC" if "NC" in str(r.get(col_car, "")).upper() else 
                                         ("Anulada" if any(x in str(r.get(col_car, "")).upper() for x in ["ANULADA", "CANCELADO"]) else 
                                         ("🔵 Pagada" if pd.to_numeric(r.get(col_sal_d), errors='coerce') == 0 else 
                                         ("🔴 En mora" if pd.notnull(pd.to_datetime(r.get(col_ven_d), errors='coerce')) and pd.to_datetime(r.get(col_ven_d), errors='coerce') < hoy else "🟢 Al día"))), axis=1)
    
    sub_t = pd.to_numeric(df_sel[col_sub_d], errors='coerce').fillna(0).sum()
    nc_v = abs(pd.to_numeric(df_sel[df_sel['Estado_Final']=="NC"][col_sub_d], errors='coerce').fillna(0).sum())
    moneda_ref = str(df_sel.iloc[0].get('Moneda', 'USD')).upper() if not df_sel.empty else "USD"
    v_net_k = ((sub_t - nc_v) / TASAS_REF.get(moneda_ref, 1)) / 1000

    st.header(f"Gestión Detallada: {pais_sel}")
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1: st.markdown(f"<div class='metric-neteada'><p style='color:#546e7a; font-size:0.75rem; margin:0;'>Venta Neta USD</p><p style='color:#0d47a1; font-size:1.1rem; font-weight:700; margin:0;'>$ {v_net_k:,.2f} K</p></div>", unsafe_allow_html=True)
    k2.metric("Subtotal", f"$ {sub_t:,.2f}")
    with k3: st.markdown(f"""<div style="background-color:white; padding:10px; border-radius:10px; border:1px solid #bbdefb; height:100%;"><p style="color:#546e7a; font-size:0.75rem; margin:0;">Notas crédito</p><p style="color:#d32f2f; font-size:1.1rem; font-weight:700; margin:0;">- $ {nc_v:,.2f}</p></div>""", unsafe_allow_html=True)
    k4.metric("Saldo Pend.", f"$ {pd.to_numeric(df_sel[col_sal_d], errors='coerce').sum():,.2f}")
    k5.metric("En Mora", f"$ {pd.to_numeric(df_sel[df_sel['Estado_Final']=='🔴 En mora'][col_sal_d], errors='coerce').sum():,.2f}")

    c1, c2 = st.columns(2)
    est_colors = {"🔵 Pagada":"#1e88e5","🔴 En mora":"#e53935","Anulada":"#757575","NC":"#8e24aa","🟢 Al día":"#43a047"}
    with c1: st.plotly_chart(px.pie(df_sel, values=col_tot_d, names='Estado_Final', hole=0.5, title="Cartera por Estado", color='Estado_Final', color_discrete_map=est_colors), use_container_width=True)
    with c2:
        df_a = df_sel['Estado_Final'].apply(lambda x: x if x in ["NC", "Anulada"] else "Vigente").value_counts().reset_index()
        st.plotly_chart(px.bar(df_a, x='count', y='Estado_Final', orientation='h', title="Auditoría Documentos", color='Estado_Final', color_discrete_map={**est_colors, "Vigente":"#43a047"}), use_container_width=True)

    st.subheader("Listado Maestro")
    st.dataframe(df_sel.sort_values(by=col_sal_d, ascending=False))
else:
    st.error("No se pudo cargar la información.")