import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import io

# --- 1. CONFIGURACIÓN Y CONEXIÓN ---
ID_DRIVE = "1IlCy67vBvvcj1LrdCtUTJk9EjZADOOqN"
st.set_page_config(page_title="Cartera DVPNYX", layout="wide")

# --- ESTILO GENERAL ---
st.markdown("""
<style>
.stApp { background-color: #e3f2fd; }

.podio-card {
    background-color: white;
    border-radius: 16px;
    padding: 15px;
    box-shadow: 0 6px 18px rgba(0,0,0,0.08);
    border: 1px solid #bbdefb;
    text-align:center;
}

.podio-title {
    font-size: 0.7rem;
    font-weight: 700;
    color: #546e7a;
    margin-top: 8px;
}
</style>
""", unsafe_allow_html=True)

# LISTA DE EXCLUSIÓN
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

datos_excel = cargar_datos_completos(ID_DRIVE)

if datos_excel:

    hojas_excluir = ['Dashboard', 'Hoja 2', 'Hoja 4', 'altabix', 'ALTABIX', 'Instrucciones']
    hojas_paises = [h for h in datos_excel.keys() if h not in hojas_excluir]
    TASAS_REF = {"COP": 4000, "MXN": 18.5, "GTQ": 7.8, "USD": 1}
    hoy = datetime.now()

    resumen_global = []
    salud_paises = []

    for p in hojas_paises:
        df_p = datos_excel[p].copy()

        if 'Total' not in df_p.columns and 'TOTAL' not in df_p.columns:
            df_p.columns = df_p.iloc[0]
            df_p = df_p[1:].reset_index(drop=True)

        df_p.columns = [str(c).strip() for c in df_p.columns]

        c_tot = next((c for c in df_p.columns if c.upper() == 'TOTAL'), 'Total')
        c_sal = next((c for c in df_p.columns if c.upper() == 'SALDO'), 'Saldo')
        c_mon = next((c for c in df_p.columns if 'Moneda' in c), None)
        c_cli = next((c for c in df_p.columns if c in ['Cliente','NOMBRE','Nombre Receptor']), 'Cliente')

        if c_tot in df_p.columns:

            df_p['CLI_CLEAN'] = df_p[c_cli].astype(str).str.strip().str.upper()
            df_p_ext = df_p[~df_p['CLI_CLEAN'].isin(INTERNOS_CLEAN)].copy()

            tasa = TASAS_REF.get(str(df_p[c_mon].iloc[0]).upper() if c_mon and not df_p.empty else "USD", 1)

            v_usd = pd.to_numeric(df_p_ext[c_tot], errors='coerce').fillna(0).sum() / tasa
            s_usd = pd.to_numeric(df_p_ext[c_sal], errors='coerce').fillna(0).sum() / tasa if c_sal in df_p_ext.columns else 0

            resumen_global.append({"País": p, "Venta_Total_USD": v_usd, "Saldo_USD": s_usd})

            score_salud = (1 - (s_usd / v_usd)) if v_usd > 0 else 0
            salud_paises.append({"País": p, "Score": score_salud})

    # ---------------- PODIO ----------------
    df_salud = pd.DataFrame(salud_paises).sort_values(by="Score", ascending=False).reset_index(drop=True)

    h1 = df_salud.iloc[0]['País'] if len(df_salud)>0 else "-"
    h2 = df_salud.iloc[1]['País'] if len(df_salud)>1 else "-"
    h3 = df_salud.iloc[2]['País'] if len(df_salud)>2 else "-"

    col_t, col_p = st.columns([3,1])

    with col_t:
        st.title("📊 Cartera DVPNYX")

    with col_p:
        st.markdown('<div class="podio-card">', unsafe_allow_html=True)
        c1,c2,c3 = st.columns(3)

        with c1:
            st.markdown("#### 🥈")
            st.markdown(f"**{h2}**")

        with c2:
            st.markdown("### 🥇")
            st.markdown(f"**{h1}**")

        with c3:
            st.markdown("#### 🥉")
            st.markdown(f"**{h3}**")

        st.markdown('<div class="podio-title">RANKING SALUD CARTERA</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    # ---------------- GRÁFICAS GLOBALES ----------------
    df_global = pd.DataFrame(resumen_global)
    df_global['Venta_K'] = df_global['Venta_Total_USD']/1000
    df_global['Saldo_K'] = df_global['Saldo_USD']/1000

    col_g1, col_g2 = st.columns(2)

    with col_g1:
        fig_v = px.bar(df_global, x="País", y="Venta_K", title="Ventas en USD")
        st.plotly_chart(fig_v, use_container_width=True)

    with col_g2:
        fig_s = px.bar(df_global, x="País", y="Saldo_K", title="Saldos por cobrar (USD)", color_discrete_sequence=['#e53935'])
        st.plotly_chart(fig_s, use_container_width=True)

    st.markdown("---")

    # ---------------- DETALLE POR PAÍS ----------------
    st.sidebar.header("Menú de Filtros")
    pais_sel = st.sidebar.selectbox("Seleccionar País:", hojas_paises)

    df_sel = datos_excel[pais_sel].copy()

    if 'Total' not in df_sel.columns:
        df_sel.columns = df_sel.iloc[0]
        df_sel = df_sel[1:].reset_index(drop=True)

    df_sel.columns = [str(c).strip() for c in df_sel.columns]

    col_sal = next((c for c in df_sel.columns if c.upper() == 'SALDO'), 'Saldo')
    col_tot = next((c for c in df_sel.columns if c.upper() == 'TOTAL'), 'Total')
    col_cli = next((c for c in df_sel.columns if c in ['Cliente','NOMBRE']), 'Cliente')
    col_car = next((c for c in df_sel.columns if c in ['Cartera','Estado']), 'Cartera')
    col_ven = next((c for c in df_sel.columns if 'vencimiento' in str(c).lower()), None)

    df_sel['CLI_CLEAN'] = df_sel[col_cli].astype(str).str.strip().str.upper()
    df_sel = df_sel[~df_sel['CLI_CLEAN'].isin(INTERNOS_CLEAN)].copy()

    def cls_fin(row):
        t = str(row.get(col_car,"")).upper()
        if "NC" in t: return "NC"
        if pd.to_numeric(row.get(col_sal),errors='coerce') == 0: return "Pagada"
        f_v = pd.to_datetime(row.get(col_ven),errors='coerce')
        return "En mora" if pd.notnull(f_v) and f_v < hoy else "Al día"

    df_sel['Estado_Final'] = df_sel.apply(cls_fin,axis=1)

    st.header(f"Gestión Detallada: {pais_sel}")

    m1,m2,m3,m4 = st.columns(4)

    m1.metric("Subtotal", f"$ {pd.to_numeric(df_sel[col_tot],errors='coerce').sum():,.2f}")
    m2.metric("Saldo pendiente", f"$ {pd.to_numeric(df_sel[col_sal],errors='coerce').sum():,.2f}")
    m3.metric("En mora", f"$ {df_sel[df_sel['Estado_Final']=='En mora'][col_sal].sum():,.2f}")
    m4.metric("Facturas", len(df_sel))

    st.markdown("---")

    c1,c2 = st.columns(2)

    with c1:
        fig_pie = px.pie(df_sel, values=col_tot, names="Estado_Final", hole=0.5, title="Cartera por Estado")
        st.plotly_chart(fig_pie, use_container_width=True)

    with c2:
        st.subheader("Listado Maestro")
        st.dataframe(df_sel[[col_cli,col_sal,"Estado_Final"]].sort_values(by=col_sal,ascending=False),
                     use_container_width=True)

else:
    st.error("Error al cargar datos.")
