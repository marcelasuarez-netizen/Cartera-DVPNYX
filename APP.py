import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import io

# --- 1. CONFIGURACIÓN INICIAL (DEBE SER LO PRIMERO) ---
st.set_page_config(page_title="Cartera DVPNYX", layout="wide")

ID_DRIVE = "1IlCy67vBvvcj1LrdCtUTJk9EjZADOOqN" 

# --- ESTILO CSS PROFESIONAL ---
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
    
    .podio-wrapper { display: flex; justify-content: center; align-items: flex-end; gap: 8px; height: 65px; margin-bottom: 5px; }
    .podio-block { border-radius: 4px 4px 0 0; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 0.75rem; width: 45px; }
    .oro { background: linear-gradient(180deg, #FFD700 0%, #B8860B 100%); height: 50px; }
    .plata { background: linear-gradient(180deg, #C0C0C0 0%, #708090 100%); height: 35px; }
    .bronce { background: linear-gradient(180deg, #CD7F32 0%, #8B4513 100%); height: 25px; }
    .podio-name { font-size: 0.6rem; color: #0d47a1; font-weight: bold; text-align: center; width: 45px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    </style>
    """, unsafe_allow_html=True)

# CLIENTES EXCLUIDOS (LOS 6 INTERCOMPANY)
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

# --- 2. CARGA Y PROCESAMIENTO ---
datos_excel = cargar_datos_completos(ID_DRIVE)

if datos_excel:
    hojas_excluir = ['Dashboard', 'Hoja 2', 'Hoja 4', 'altabix', 'ALTABIX', 'Instrucciones']
    hojas_paises = [h for h in datos_excel.keys() if h not in hojas_excluir]
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
        c_sub = next((c for c in df_p.columns if c.upper() in ['SUBTOTAL', 'SERVICIOS']), 'Subtotal')
        c_cli = next((c for c in df_p.columns if c in ['Cliente', 'NOMBRE', 'Nombre Receptor']), 'Cliente')
        c_car = next((c for c in df_p.columns if c in ['Cartera', 'Estado', 'Estado de pago', 'Estatus']), 'Cartera')
        c_mon = next((c for c in df_p.columns if 'Moneda' in c), None)

        if c_tot in df_p.columns:
            df_p['CLI_CLEAN'] = df_p[c_cli].astype(str).str.strip().str.upper()
            df_p_ext = df_p[~df_p['CLI_CLEAN'].isin(INTERNOS_CLEAN)].copy()
            
            # Tasa
            moneda_val = "USD"
            if c_mon and not df_p.empty:
                val = df_p[c_mon].iloc[0]
                moneda_val = str(val).upper().strip() if pd.notnull(val) else "USD"
            tasa = TASAS_REF.get(moneda_val, 1)

            # Cálculos de Salud para el Podio
            v_usd = pd.to_numeric(df_p_ext[c_tot], errors='coerce').fillna(0).sum() / tasa
            s_usd = pd.to_numeric(df_p_ext[c_sal], errors='coerce').fillna(0).sum() / tasa
            score_salud = ((v_usd - s_usd) / v_usd * 100) if v_usd > 0 else 0
            
            resumen_global.append({"País": p, "Venta_Total_USD": v_usd, "Saldo_USD": s_usd, "Salud": score_salud})

    # --- PODIO ---
    df_salud = pd.DataFrame(resumen_global).sort_values(by="Salud", ascending=False).reset_index(drop=True)
    h1, h2, h3 = (df_salud.iloc[0]['País'] if len(df_salud)>0 else "-", df_salud.iloc[1]['País'] if len(df_salud)>1 else "-", df_salud.iloc[2]['País'] if len(df_salud)>2 else "-")

    col_t, col_p = st.columns([3, 1])
    with col_t: st.title("📊 Cartera DVPNYX")
    with col_p:
        st.markdown(f"""<div style="text-align:right"><div class='podio-wrapper'>
                <div style="display:flex; flex-direction:column; align-items:center"><div class="podio-name">{h2}</div><div class='podio-block plata'>2º</div></div>
                <div style="display:flex; flex-direction:column; align-items:center"><div class="podio-name">{h1}</div><div class='podio-block oro'>1º</div></div>
                <div style="display:flex; flex-direction:column; align-items:center"><div class="podio-name">{h3}</div><div class='podio-block bronce'>3º</div></div>
            </div><p style="font-size:0.55rem; color:#546e7a; margin-top:2px; font-weight:bold; text-align:center">PODIO SALUD CARTERA</p></div>""", unsafe_allow_html=True)

    # --- 4. DETALLE POR PAÍS ---
    st.sidebar.header("Menú de Filtros")
    pais_sel = st.sidebar.selectbox("🚩 Selección País:", hojas_paises)
    df_sel = datos_excel[pais_sel].copy()
    if 'Total' not in df_sel.columns: df_sel.columns = df_sel.iloc[0]; df_sel = df_sel[1:]
    df_sel.columns = [str(c).strip() for c in df_sel.columns]
    
    # Exclusión Internos
    c_cli_sel = next((c for c in df_sel.columns if any(x in str(c) for x in ['Cliente', 'NOMBRE'])), 'Cliente')
    df_sel['CLI_CLEAN'] = df_sel[c_cli_sel].astype(str).str.strip().str.upper()
    df_sel = df_sel[~df_sel['CLI_CLEAN'].isin(INTERNOS_CLEAN)].copy()

    # Lógica de Estados
    def cls_fin(row):
        try:
            val_s = pd.to_numeric(row.get('Saldo'), errors='coerce')
            if val_s == 0: return "🔵 Pagada"
            f_v = pd.to_datetime(row.get('Vencimiento'), errors='coerce')
            return "🔴 En mora" if pd.notnull(f_v) and f_v < hoy else "🟢 Al día"
        except: return "🟢 Al día"

    df_sel['Estado_Final'] = df_sel.apply(cls_fin, axis=1)

    st.header(f"Gestión Detallada: {pais_sel}")
    
    # FILA DE MÉTRICAS (R1)
    # ... (Cálculos de Subtotal, NC, Saldo, Mora) ...
    st.markdown("---")

    # --- FILA INFERIOR: GRÁFICA ESTADO (IZQ) vs COMPARATIVA (DER) ---
    col_izq, col_der = st.columns(2)
    
    with col_izq:
        # Gráfica de Pie (Salud Interna)
        fig_est = px.pie(df_sel, names='Estado_Final', title=f"Estado Cartera - {pais_sel}", hole=0.4,
                         color='Estado_Final', color_discrete_map={"🔵 Pagada": "#1e88e5", "🔴 En mora": "#e53935", "🟢 Al día": "#43a047"})
        st.plotly_chart(fig_est, use_container_width=True)

    with col_der:
        # GRÁFICA COMPARATIVA EN LA DERECHA (Facturado vs Recaudado)
        sub_total = pd.to_numeric(df_sel['Subtotal'], errors='coerce').fillna(0).sum()
        pagado = sub_total - pd.to_numeric(df_sel['Saldo'], errors='coerce').fillna(0).sum()
        
        df_comp = pd.DataFrame({
            "Categoría": ["Valor Neteado", "Recaudado (Pagado)"],
            "Monto": [sub_total, pagado]
        })
        
        fig_comp = px.bar(df_comp, x="Categoría", y="Monto", title=f"Recaudo vs Facturación - {pais_sel}",
                          color="Categoría", color_discrete_map={"Valor Neteado": "#1565C0", "Recaudado (Pagado)": "#43A047"})
        st.plotly_chart(fig_comp, use_container_width=True)

    st.subheader("Listado Maestro")
    st.dataframe(df_sel, use_container_width=True)

else:
    st.error("Error al cargar datos.")