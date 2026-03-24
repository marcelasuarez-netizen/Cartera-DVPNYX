import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import io

# --- 1. CONFIGURACIÓN Y CONEXIÓN ---
ID_DRIVE = "1IlCy67vBvvcj1LrdCtUTJk9EjZADOOqN" 

st.set_page_config(page_title="Cartera DVPNYX", layout="wide")

# --- ESTILO CSS COMPLETO (UX/UI PROFESIONAL) ---
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
    
    /* Estilo Podio Salud */
    .podio-wrapper { display: flex; justify-content: center; align-items: flex-end; gap: 8px; height: 70px; }
    .podio-block { border-radius: 4px 4px 0 0; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 0.8rem; width: 50px; }
    .oro { background: linear-gradient(180deg, #FFD700 0%, #B8860B 100%); height: 55px; }
    .plata { background: linear-gradient(180deg, #C0C0C0 0%, #708090 100%); height: 40px; }
    .bronce { background: linear-gradient(180deg, #CD7F32 0%, #8B4513 100%); height: 30px; }
    .podio-name { font-size: 0.65rem; color: #0d47a1; font-weight: bold; text-align: center; width: 50px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

    /* Contenedor para métricas personalizadas */
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

MESES_NOMBRES = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}

# --- 2. CARGA DE DATOS ---
datos_excel = cargar_datos_completos(ID_DRIVE)

if datos_excel:
    hojas_excluir = ['Dashboard', 'Hoja 2', 'Hoja 4', 'altabix', 'ALTABIX', 'Instrucciones']
    hojas_paises = [h for h in datos_excel.keys() if h not in hojas_excluir]
    TASAS_REF = {"COP": 4000, "MXN": 18.5, "GTQ": 7.8, "USD": 1}
    hoy = datetime.now()

    # --- 3. PROCESAMIENTO GLOBAL (PARA EL PODIO) ---
    salud_paises = []
    resumen_global = []
    for p in hojas_paises:
        df_p = datos_excel[p].copy()
        
        # CORRECCIÓN DEFINITIVA LÍNEA 91
        if 'Total' not in df_p.columns:
            df_p.columns = df_p.iloc # <--- EL ES CLAVE
            df_p = df_p[1:].reset_index(drop=True)
            
        df_p.columns = [str(c).strip() for c in df_p.columns]
        
        c_tot = next((c for c in df_p.columns if c.upper() == 'TOTAL'), 'Total')
        c_sal = next((c for c in df_p.columns if c.upper() == 'SALDO'), 'Saldo')
        c_mon = next((c for c in df_p.columns if 'Moneda' in c), None)
        c_cli = next((c for c in df_p.columns if str(c).strip().upper() in ['CLIENTE', 'NOMBRE', 'RECEPTOR']), 'Cliente')

        if c_cli in df_p.columns and c_tot in df_p.columns:
            df_p['CLI_CLEAN'] = df_p[c_cli].astype(str).str.strip().str.upper()
            df_p_ext = df_p[~df_p['CLI_CLEAN'].isin(INTERNOS_CLEAN)].copy()
            tasa = TASAS_REF.get(str(df_p[c_mon].iloc).upper() if c_mon and not df_p.empty else "USD", 1)
            v_usd = pd.to_numeric(df_p_ext[c_tot], errors='coerce').fillna(0).sum() / tasa
            s_usd = pd.to_numeric(df_p_ext[c_sal], errors='coerce').fillna(0).sum() / tasa
            resumen_global.append({"País": p, "Venta_Total_USD": v_usd, "Saldo_USD": s_usd})
            score = (1 - (s_usd / v_usd)) if v_usd > 0 else 0
            salud_paises.append({"País": p, "Score": score})

    # PODIO
    df_salud = pd.DataFrame(salud_paises).sort_values(by="Score", ascending=False).reset_index(drop=True)
    h1, h2, h3 = (df_salud.iloc['País'] if len(df_salud)>0 else "-", df_salud.iloc['País'] if len(df_salud)>1 else "-", df_salud.iloc['País'] if len(df_salud)>2 else "-")

    col_t, col_p = st.columns()
    with col_t: st.title("📊 Cartera DVPNYX")
    with col_p:
        st.markdown(f"""<div style="text-align:right"><div class='podio-wrapper'>
            <div style="display:flex; flex-direction:column; align-items:center"><div class="podio-name">{h2}</div><div class='podio-block plata'>2º</div></div>
            <div style="display:flex; flex-direction:column; align-items:center"><div class="podio-name">{h1}</div><div class='podio-block oro'>1º</div></div>
            <div style="display:flex; flex-direction:column; align-items:center"><div class="podio-name">{h3}</div><div class='podio-block bronce'>3º</div></div>
        </div><p style="font-size:0.55rem; color:#546e7a; margin-top:2px; font-weight:bold; text-align:center">RANKING SALUD CARTERA</p></div>""", unsafe_allow_html=True)

    st.markdown("---")
    
    # --- 4. FILTROS SIDEBAR (LOS 4 DESPLEGABLES) ---
    st.sidebar.header("Menú de Filtros")
    
    # Filtro 1: País
    pais_sel = st.sidebar.selectbox("🚩 País:", hojas_paises)
    df_sel = datos_excel[pais_sel].copy()
    
    if 'Total' not in df_sel.columns:
        df_sel.columns = df_sel.iloc
        df_sel = df_sel[1:].reset_index(drop=True)
        
    df_sel.columns = [str(c).strip() for c in df_sel.columns]

    # Identificación de columnas
    col_sal = next((c for c in df_sel.columns if c.upper() == 'SALDO'), 'Saldo')
    col_sub = next((c for c in df_sel.columns if c.upper() in ['SUBTOTAL', 'SERVICIOS']), 'Subtotal')
    col_iva = next((c for c in df_sel.columns if c.upper() in ['IVA', 'TOTAL IVA']), 'IVA')
    col_cli = next((c for c in df_sel.columns if str(c).strip().upper() in ['CLIENTE', 'NOMBRE', 'RECEPTOR']), 'Cliente')
    col_tot = next((c for c in df_sel.columns if c.upper() == 'TOTAL'), 'Total')
    col_car = next((c for c in df_sel.columns if c in ['Cartera', 'Estado']), 'Cartera')
    col_ven = next((c for c in df_sel.columns if 'vencimiento' in str(c).lower()), None)
    col_mon = next((c for c in df_sel.columns if 'Moneda' in c), None)
    col_año = next((c for c in df_sel.columns if 'AÑO' in c.upper()), None)
    col_mes = next((c for c in df_sel.columns if 'MES' in c.upper()), None)

    # Exclusión Clientes Internos
    if col_cli in df_sel.columns:
        df_sel['CLI_CLEAN'] = df_sel[col_cli].astype(str).str.strip().str.upper()
        df_sel = df_sel[~df_sel['CLI_CLEAN'].isin(INTERNOS_CLEAN)].copy()

    # Filtro 2: Año
    if col_año:
        años = ["Todos"] + sorted(list(df_sel[col_año].dropna().unique()), reverse=True)
        año_f = st.sidebar.selectbox("📅 Año:", años)
        if año_f != "Todos": df_sel = df_sel[df_sel[col_año] == año_f]
        
    # Filtro 3: Mes
    if col_mes:
        meses = ["Todos"] + [f"{int(m)} - {MESES_NOMBRES.get(int(m))}" for m in sorted(df_sel[col_mes].dropna().unique())]
        mes_f = st.sidebar.selectbox("📆 Mes:", meses)
        if mes_f != "Todos": df_sel = df_sel[df_sel[col_mes] == int(mes_f.split(" - "))]
    
    # Filtro 4: Cliente
    cli_lista = ["Todos"] + sorted(list(df_sel[col_cli].dropna().unique())) if col_cli in df_sel.columns else ["Todos"]
    cli_f = st.sidebar.selectbox("👤 Cliente:", cli_lista)
    if cli_f != "Todos" and col_cli in df_sel.columns: 
        df_sel = df_sel[df_sel[col_cli] == cli_f]

    # --- 5. GESTIÓN DETALLADA ---
    def cls_fin(row):
        t = str(row.get(col_car, "")).upper()
        if "NC" in t: return "NC"
        if pd.to_numeric(row.get(col_sal), errors='coerce') == 0: return "🔵 Pagada"
        f_v = pd.to_datetime(row.get(col_ven), errors='coerce')
        return "🔴 En mora" if pd.notnull(f_v) and f_v < hoy else "🟢 Al día"
    
    df_sel['Estado_Final'] = df_sel.apply(cls_fin, axis=1)

    for c in [col_sub, col_iva, col_tot, col_sal]:
        if c in df_sel.columns: df_sel[c] = pd.to_numeric(df_sel[c], errors='coerce').fillna(0)

    st.header(f"Gestión Detallada: {pais_sel}")
    
    # Fila 1: KPIs Principales (Mora en Rojo)
    r1c0, r1c1, r1c2, r1c3, r1c4 = st.columns(5)
    sub_total = df_sel[col_sub].sum()
    val_nc = abs(df_sel[df_sel['Estado_Final'] == "NC"][col_sub].sum())
    tasa_act = TASAS_REF.get(str(df_sel[col_mon].iloc).upper() if col_mon and not df_sel.empty else "USD", 1)
    
    with r1c0: st.markdown(f'<div class="metric-custom"><p class="metric-custom-label">Conv. Dólares</p><p class="metric-custom-value">$ {(sub_total-val_nc)/tasa_act/1000:,.2f} K</p></div>', unsafe_allow_html=True)
    r1c1.metric("Subtotal", f"$ {sub_total:,.2f}")
    with r1c2: st.markdown(f'<div style="background-color:white; padding:10px; border-radius:10px; border:1px solid #bbdefb; height:100%;"><p style="color:#546e7a; font-size:0.75rem; margin:0;">Notas crédito</p><p style="color:#d32f2f; font-size:1.1rem; font-weight:700; margin:0;">- $ {val_nc:,.2f}</p></div>', unsafe_allow_html=True)
    r1c3.metric("Saldo pendiente", f"$ {df_sel[col_sal].sum():,.2f}")
    with r1c4: st.markdown(f'<div class="metric-custom"><p class="metric-custom-label" style="color:#d32f2f; font-weight:bold;">Monto en mora</p><p class="metric-custom-value">$ {df_sel[df_sel['Estado_Final']=='🔴 En mora'][col_sal].sum():,.2f}</p></div>', unsafe_allow_html=True)

    # Fila 2: Gestión
    st.write("")
    r2c1, r2c2, r2c3, r2c4 = st.columns(4)
    r2c1.metric("IVA", f"$ {df_sel[~df_sel['Estado_Final'].isin(['Anulada', 'NC'])][col_iva].sum():,.2f}")
    r2c2.metric("DSO (Días)", f"{(df_sel[col_sal].sum() / (df_sel[col_tot].sum() if df_sel[col_tot].sum()>0 else 1) * 360):.0f}")
    r2c3.metric("Docs Emitidos", f"{len(df_sel):,d}")
    r2c4.metric("Venta Neta Local", f"$ {sub_total-val_nc:,.2f}")

    st.markdown("---")
    
    # GRÁFICAS
    c1, c2 = st.columns(2)
    with c1: st.plotly_chart(px.pie(df_sel, values=col_tot, names='Estado_Final', hole=0.5, title="Cartera por Estado", color='Estado_Final', color_discrete_map={"🔵 Pagada": "#1e88e5", "🔴 En mora": "#e53935", "🟢 Al día": "#43a047"}), use_container_width=True)
    with c2:
        df_aud = df_sel['Estado_Final'].apply(lambda x: x if x in ["NC", "Anulada"] else "Vigente").value_counts().reset_index()
        df_aud.columns = ['Tipo', 'Cantidad']
        st.plotly_chart(px.bar(df_aud, x='Cantidad', y='Tipo', orientation='h', title="Auditoría de Documentos", color='Tipo', color_discrete_map={"Vigente": "#43a047", "NC": "#8e24aa"}), use_container_width=True)

    st.subheader("Listado Maestro")
    st.dataframe(df_sel[[col_cli, col_sal, 'Estado_Final']].sort_values(by=col_sal, ascending=False), use_container_width=True)

else: