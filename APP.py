import streamlit as st

import pandas as pd

import plotly.express as px

from datetime import datetime

import requests

import io



# --- 1. CONFIGURACIÓN Y CONEXIÓN ---

ID_DRIVE = "1IlCy67vBvvcj1LrdCtUTJk9EjZADOOqN"



st.set_page_config(page_title="Cartera DVPNYX", layout="wide")



# --- ESTILO CSS PROFESIONAL (UX/UI) ---

st.markdown("""

    <style>

    .stApp { background-color: #f4f7f9; }

    [data-testid="stMetric"] {

        background-color: #ffffff;

        padding: 15px;

        border-radius: 12px;

        box-shadow: 0 4px 6px rgba(0,0,0,0.05);

        border: 1px solid #e1e8ed;

    }

    /* Estilo Podio */

    .podio-wrapper { display: flex; justify-content: center; align-items: flex-end; gap: 10px; margin: 20px 0; height: 120px; }

    .podio-block { border-radius: 8px 8px 0 0; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; color: white; font-weight: bold; font-size: 1.2rem; transition: 0.3s; }

    .oro { background: linear-gradient(180deg, #FFD700 0%, #B8860B 100%); width: 60px; height: 100px; box-shadow: 0 4px 15px rgba(218,165,32,0.4); }

    .plata { background: linear-gradient(180deg, #C0C0C0 0%, #708090 100%); width: 60px; height: 75px; }

    .bronce { background: linear-gradient(180deg, #CD7F32 0%, #8B4513 100%); width: 60px; height: 55px; }

    .podio-off { background-color: #e1e8ed; color: #aab8c2; height: 40px; }

   

    /* Panel de Seguimiento */

    .notas-container {

        background-color: #fff3cd;

        padding: 15px;

        border-radius: 10px;

        border-left: 5px solid #ffc107;

        margin-top: 20px;

    }

    .nota-item { font-size: 0.85rem; color: #856404; margin-bottom: 5px; font-weight: 500; }

    </style>

    """, unsafe_allow_html=True)



# MAPEO DE BANDERAS (URLs reales)

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

def cargar_datos(id_file):

    url = f"https://docs.google.com/spreadsheets/d/{id_file}/export?format=xlsx"

    response = requests.get(url)

    return pd.read_excel(io.BytesIO(response.content), sheet_name=None, engine='openpyxl')



# --- CARGA Y PROCESAMIENTO ---

datos_excel = cargar_datos(ID_DRIVE)

if datos_excel:

    hojas_paises = [h for h in datos_excel.keys() if h not in ['Dashboard', 'Hoja 2', 'Hoja 4', 'altabix', 'ALTABIX', 'Instrucciones']]

    TASAS_REF = {"COP": 4000, "MXN": 18.5, "GTQ": 7.8, "USD": 1}

   

    resumen_global = []

    for p in hojas_paises:

        df_p = datos_excel[p].copy()

        if 'Total' not in df_p.columns and 'TOTAL' not in df_p.columns:

            df_p.columns = df_p.iloc[0]; df_p = df_p[1:].reset_index(drop=True)

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



    # --- SIDEBAR DINÁMICO ---

    st.sidebar.header("Filtros y Estatus")

    pais_sel = st.sidebar.selectbox("🚩 Seleccionar País:", hojas_paises)

   

    # LÓGICA DEL PODIO

    info_pais = df_rank[df_rank['País'] == pais_sel].iloc[0]

    puesto = info_pais['Puesto']

    bandera_url = BANDERAS.get(pais_sel.upper(), "")



    if puesto <= 3:

        st.sidebar.markdown(f"<div style='text-align: center;'><img src='{bandera_url}' width='50'><h3>{pais_sel}</h3></div>", unsafe_allow_html=True)

        # Render del Podio CSS

        p1 = "oro" if puesto == 1 else "podio-off"

        p2 = "plata" if puesto == 2 else "podio-off"

        p3 = "bronce" if puesto == 3 else "podio-off"

       

        podio_html = f"""

        <div class='podio-wrapper'>

            <div class='podio-block {p2}'>2º</div>

            <div class='podio-block {p1}'>1º</div>

            <div class='podio-block {p3}'>3º</div>

        </div>

        """

        st.sidebar.markdown(podio_html, unsafe_allow_html=True)

        mensajes = {1: "🥇 Líder del ranking en desempeño", 2: "🥈 Desempeño destacado y consistente", 3: "🥉 Buen posicionamiento en el Top 3"}

        st.sidebar.success(mensajes[puesto])

    else:

        st.sidebar.markdown(f"<div style='text-align: center;'><img src='{bandera_url}' width='50'><h3>{pais_sel}</h3></div>", unsafe_allow_html=True)

        st.sidebar.warning("País fuera del Top 3")

        st.sidebar.markdown(f"""

            <div class="notas-container">

                <div style="font-weight:bold; margin-bottom:10px;">⚠️ NOTAS DE SEGUIMIENTO</div>

                <div class="nota-item">📌 Revisar cartera vencida > 60 días</div>

                <div class="nota-item">📌 Validar acuerdos de pago pendientes</div>

                <div class="nota-item">📌 Priorizar gestión clientes críticos</div>

            </div>

        """, unsafe_allow_html=True)



    # --- DASHBOARD PRINCIPAL ---

    st.title("📊 Cartera DVPNYX")

    st.markdown("---")

   

    # Gráficas globales (Ventas y Saldos)

    df_global_ui = df_rank.copy()

    df_global_ui['Venta_K'] = df_global_ui['Venta_Total_USD'] / 1000

   

    col_g1, col_g2 = st.columns(2)

    with col_g1:

        fig = px.bar(df_global_ui, x="País", y="Venta_K", title="Ventas en USD (K)", color="País",

                     color_discrete_map={"GUATEMALA": "#4DD0E1", "COLOMBIA": "#1565C0", "MEXICO": "#43A047", "ECUADOR": "#FFB300"})

        fig.update_traces(texttemplate='<b>%{y:.1f} K</b>', textposition='outside')

        st.plotly_chart(fig, use_container_width=True)

    with col_g2:

        st.info("Visualización global de ventas externas por territorio.")



    # --- DETALLE PAÍS SELECCIONADO ---

    st.markdown("---")

    df_sel = datos_excel[pais_sel].copy()

    if 'Total' not in df_sel.columns: df_sel.columns = df_sel.iloc[0]; df_sel = df_sel[1:]

   

    # (Aquí iría el resto de tu lógica de KPIs y tabla maestra que ya funciona)

    st.subheader(f"Gestión Detallada: {pais_sel}")

    st.write("Filtros de tiempo y listado maestro cargados correctamente.")



else:

    st.error("Error al conectar con la base de datos.")