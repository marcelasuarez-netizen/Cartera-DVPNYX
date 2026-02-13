import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import io

# --- 1. CONFIGURACIÓN Y CONEXIÓN ---
ID_DRIVE = "1IlCy67vBvvcj1LrdCtUTJk9EjZADOOqN"

st.set_page_config(page_title="Cartera DVPNYX", layout="wide")

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

[data-testid="stMetricValue"] {
    font-size: 1.1rem !important;
    color: #1565c0;
    font-weight: 700;
}

[data-testid="stMetricLabel"] {
    font-size: 0.75rem !important;
    color: #546e7a;
}

h1, h2, h3 {
    color: #0d47a1;
}

/* PODIO */
.podio-card {
    background: white;
    padding: 12px;
    border-radius: 14px;
    border: 1px solid #bbdefb;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    text-align: center;
}

.podio-title {
    font-size: 0.65rem;
    font-weight: 700;
    margin-top: 6px;
    color: #546e7a;
}
</style>
""", unsafe_allow_html=True)

# --- LISTA DE EXCLUSIÓN ---
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


# --- 2. CARGA DE DATOS ---
datos_excel = cargar_datos_completos(ID_DRIVE)

if datos_excel:

    hojas_excluir = ['Dashboard','Hoja 2','Hoja 4','altabix','ALTABIX','Instrucciones']
    hojas_paises = [h for h in datos_excel.keys() if h not in hojas_excluir]

    TASAS_REF = {"COP":4000,"MXN":18.5,"GTQ":7.8,"USD":1}
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

            tasa = TASAS_REF.get(
                str(df_p[c_mon].iloc[0]).upper() if c_mon and not df_p.empty else "USD",
                1
            )

            v_usd = pd.to_numeric(df_p_ext[c_tot], errors='coerce').fillna(0).sum() / tasa
            s_usd = pd.to_numeric(df_p_ext[c_sal], errors='coerce').fillna(0).sum() / tasa

            resumen_global.append({"País":p,"Venta_Total_USD":v_usd,"Saldo_USD":s_usd})

            score = (1 - (s_usd / v_usd)) if v_usd > 0 else 0
            salud_paises.append({"País":p,"Score":score})

    # --- PODIO ---
    df_salud = pd.DataFrame(salud_paises).sort_values(by="Score", ascending=False).reset_index(drop=True)

    h1 = df_salud.iloc[0]['País'] if len(df_salud)>0 else "-"
    h2 = df_salud.iloc[1]['País'] if len(df_salud)>1 else "-"
    h3 = df_salud.iloc[2]['País'] if len(df_salud)>2 else "-"

    col_t, col_p = st.columns([3,1])

    with col_t:
        st.title("📊 Cartera DVPNYX")

    with col_p:
        st.markdown('<div class="podio-card">', unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)

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

    # --- GRÁFICAS GLOBALES ---
    df_global = pd.DataFrame(resumen_global)
    df_global['Venta_K'] = df_global['Venta_Total_USD']/1000
    df_global['Saldo_K'] = df_global['Saldo_USD']/1000

    col_g1, col_g2 = st.columns(2)

    with col_g1:
        fig_v = px.bar(df_global, x="País", y="Venta_K", title="Ventas en USD")
        st.plotly_chart(fig_v, use_container_width=True)

    with col_g2:
        fig_s = px.bar(df_global, x="País", y="Saldo_K", title="Saldos por cobrar (USD)")
        st.plotly_chart(fig_s, use_container_width=True)

else:
    st.error("Error al cargar datos.")