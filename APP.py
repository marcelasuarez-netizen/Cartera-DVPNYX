Perfecto 🙌 aquí te dejo tu código completo, exactamente igual al que enviaste, solo con la parte del podio mejorada (CSS + HTML actualizados). No toqué nada más.

Puedes copiar y reemplazar todo tu script por este 👇

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
    [data-testid="stMetricValue"] { font-size: 1.1rem !important; color: #1565c0; font-weight: 700; }
    [data-testid="stMetricLabel"] { 
        font-size: 0.75rem !important; 
        color: #546e7a; 
        text-transform: capitalize; 
    }
    h1, h2, h3 { color: #0d47a1; text-transform: none; }

    /* ===== PODIO MODERNO ===== */
    .podio-container {
        display: flex;
        justify-content: center;
        align-items: flex-end;
        gap: 15px;
        height: 130px;
    }

    .podio-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        width: 80px;
    }

    .podio-name {
        font-size: 0.75rem;
        font-weight: 600;
        color: #0d47a1;
        text-align: center;
        margin-bottom: 6px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        width: 100%;
    }

    .podio-block {
        width: 100%;
        border-radius: 12px 12px 0 0;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 800;
        font-size: 1.2rem;
        color: white;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
        transition: transform 0.2s ease;
    }

    .podio-block:hover {
        transform: translateY(-4px);
    }

    .oro {
        height: 110px;
        background: linear-gradient(180deg, #FFD700 0%, #C6A700 100%);
    }

    .plata {
        height: 85px;
        background: linear-gradient(180deg, #E0E0E0 0%, #9E9E9E 100%);
    }

    .bronce {
        height: 65px;
        background: linear-gradient(180deg, #D2691E 0%, #8B4513 100%);
    }

    .podio-label {
        font-size: 0.6rem;
        font-weight: 700;
        margin-top: 6px;
        color: #546e7a;
        letter-spacing: 0.5px;
        text-align: center;
    }

    /* Contenedor métricas personalizadas */
    .metric-custom {
        background-color: #ffffff;
        padding: 10px 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border: 1px solid #bbdefb;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .metric-custom-label {
        font-size: 0.75rem !important;
        margin-bottom: 4px;
        text-transform: capitalize;
        color: #546e7a;
    }
    .metric-custom-value {
        font-size: 1.1rem !important;
        color: #1565c0;
        font-weight: 700;
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

MESES_NOMBRES = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 
                 7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}

# --- CARGA DE DATOS ---
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
            
            score_salud = (1 - (s_usd / v_usd)) if v_usd > 0 else 0
            salud_paises.append({"País": p, "Score": score_salud})

    # PODIO MEJORADO
    df_salud = pd.DataFrame(salud_paises).sort_values(by="Score", ascending=False).reset_index(drop=True)
    h1 = df_salud.iloc[0]['País'] if len(df_salud)>0 else "-"
    h2 = df_salud.iloc[1]['País'] if len(df_salud)>1 else "-"
    h3 = df_salud.iloc[2]['País'] if len(df_salud)>2 else "-"

    col_t, col_p = st.columns([3, 1])
    with col_t:
        st.title("📊 Cartera DVPNYX")
    with col_p:
        st.markdown(f"""
        <div>
            <div class='podio-container'>
                
                <div class='podio-item'>
                    <div class='podio-name'>{h2}</div>
                    <div class='podio-block plata'>🥈</div>
                </div>

                <div class='podio-item'>
                    <div class='podio-name'>{h1}</div>
                    <div class='podio-block oro'>🥇</div>
                </div>

                <div class='podio-item'>
                    <div class='podio-name'>{h3}</div>
                    <div class='podio-block bronce'>🥉</div>
                </div>

            </div>
            <div class='podio-label'>RANKING SALUD CARTERA</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

else:
    st.error("Error al cargar datos.")