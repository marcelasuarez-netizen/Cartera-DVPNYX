
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
    text-transform: capitalize;
}

h1, h2, h3 {
    color: #0d47a1;
}

/* --- PODIO --- */
.podio-wrapper {
    display: flex;
    justify-content: center;
    align-items: flex-end;
    gap: 8px;
    height: 70px;
}

.podio-block {
    border-radius: 4px 4px 0 0;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: bold;
    font-size: 0.8rem;
    width: 50px;
}

.oro {
    background: linear-gradient(180deg, #FFD700 0%, #B8860B 100%);
    height: 55px;
}

.plata {
    background: linear-gradient(180deg, #C0C0C0 0%, #708090 100%);
    height: 40px;
}

.bronce {
    background: linear-gradient(180deg, #CD7F32 0%, #8B4513 100%);
    height: 30px;
}

.podio-name {
    font-size: 0.65rem;
    color: #0d47a1;
    font-weight: bold;
    text-align: center;
    width: 50px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
</style>
""", unsafe_allow_html=True)

# --- CLIENTES INTERNOS ---
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


# --- CARGA ---
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

        c_tot = next((c for c in df_p.columns if c.upper() == 'TOTAL'), None)
        c_sal = next((c for c in df_p.columns if c.upper() == 'SALDO'), None)
        c_mon = next((c for c in df_p.columns if 'Moneda' in c), None)
        c_cli = next((c for c in df_p.columns if c in ['Cliente','NOMBRE','Nombre Receptor']), None)

        if c_tot and c_sal and c_cli:

            df_p['CLI_CLEAN'] = df_p[c_cli].astype(str).str.strip().str.upper()
            df_p_ext = df_p[~df_p['CLI_CLEAN'].isin(INTERNOS_CLEAN)].copy()

            tasa = TASAS_REF.get(
                str(df_p[c_mon].iloc[0]).upper() if c_mon and not df_p.empty else "USD",
                1
            )

            v_usd = pd.to_numeric(df_p_ext[c_tot], errors='coerce').fillna(0).sum() / tasa
            s_usd = pd.to_numeric(df_p_ext[c_sal], errors='coerce').fillna(0).sum() / tasa

            resumen_global.append({"País": p, "Venta_Total_USD": v_usd, "Saldo_USD": s_usd})

            score = (1 - (s_usd / v_usd)) if v_usd > 0 else 0
            salud_paises.append({"País": p, "Score": score})

    # --- PODIO ---
    df_salud = pd.DataFrame(salud_paises).sort_values(by="Score", ascending=False).reset_index(drop=True)

    h1 = df_salud.iloc[0]['País'] if len(df_salud) > 0 else "-"
    h2 = df_salud.iloc[1]['País'] if len(df_salud) > 1 else "-"
    h3 = df_salud.iloc[2]['País'] if len(df_salud) > 2 else "-"

    col_t, col_p = st.columns([3, 1])

    with col_t:
        st.title("📊 Cartera DVPNYX")

    with col_p:
        st.markdown(f"""
        <div class='podio-wrapper'>
            <div style="display:flex; flex-direction:column; align-items:center">
                <div class="podio-name">{h2}</div>
                <div class='podio-block plata'>2º</div>
            </div>
            <div style="display:flex; flex-direction:column; align-items:center">
                <div class="podio-name">{h1}</div>
                <div class='podio-block oro'>1º</div>
            </div>
            <div style="display:flex; flex-direction:column; align-items:center">
                <div class="podio-name">{h3}</div>
                <div class='podio-block bronce'>3º</div>
            </div>
        </div>
        <p style="font-size:0.55rem; color:#546e7a; margin-top:2px; font-weight:bold; text-align:center">
        RANKING SALUD CARTERA
        </p>
        """, unsafe_allow_html=True)

    st.markdown("---")

else:
    st.error("Error al cargar datos.")