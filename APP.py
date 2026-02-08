import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import io

# --- 1. CONFIGURACIÓN Y CONEXIÓN ---
ID_DRIVE = "1IlCy67vBvvcj1LrdCtUTJk9EjZADOOqN" 

st.set_page_config(page_title="Dashboard Cartera DVP-NYX 360", layout="wide")

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
    [data-testid="stMetricLabel"] { font-size: 0.75rem !important; color: #546e7a; }
    h1, h2, h3 { color: #0d47a1; }
    </style>
    """, unsafe_allow_html=True)

# Lista de Clientes a Excluir (Intercompany)
CLIENTES_EXCLUIR = [
    "TRADIOH LLC", 
    "N&X TECNOLOGIA Y NEGOCIOS", 
    "NYX DESARROLLADORA DE SOFTWARE Y SOLUCIONES TECNOLOGICAS", 
    "DOUBLE V PARTNERS GUATEMALA SOCIEDAD ANONIMA", 
    "DVP SOFTWARE AND CONSULTING SA DE CV", 
    "DOUBLE V PARTNERS ECUADOR DVP"
]

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

# --- 2. CARGA DE DATOS ---
st.title("📊 Control Financiero 360: Cartera Externa (Sin Intercompany)")
st.markdown("---")

datos_excel = cargar_datos_completos(ID_DRIVE)

if datos_excel:
    hojas_excluir = ['Dashboard', 'Hoja 2', 'Hoja 4', 'altabix', 'ALTABIX', 'Instrucciones']
    hojas_paises = [h for h in datos_excel.keys() if h not in hojas_excluir]
    TASAS_REF = {"COP": 4000, "MXN": 18.5, "GTQ": 7.8, "USD": 1}
    hoy = datetime.now()

    # --- 3. PROCESAMIENTO GLOBAL USD (Excluyendo Clientes Internos) ---
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

        if c_tot in df_p.columns:
            # Filtrar exclusiones para el consolidado global
            df_p_filtrado = df_p[~df_p[c_cli].astype(str).str.upper().isin([c.upper() for c in CLIENTES_EXCLUIR])]
            
            tasa = TASAS_REF.get(str(df_p[c_mon].iloc[0]).upper() if c_mon and not df_p.empty else "USD", 1)
            v_usd = pd.to_numeric(df_p_filtrado[c_tot], errors='coerce').fillna(0).sum() / tasa
            s_usd = pd.to_numeric(df_p_filtrado[c_sal], errors='coerce').fillna(0).sum() / tasa if c_sal in df_p_filtrado.columns else 0
            resumen_global.append({"País": p, "Venta_Total_USD": v_usd, "Saldo_USD": s_usd})

    df_global = pd.DataFrame(resumen_global)
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.plotly_chart(px.bar(df_global, x="País", y="Venta_Total_USD", text_auto=',.0f', title="Venta Externa Total (USD)", color="País").update_layout(template="plotly_white", paper_bgcolor='rgba(0,0,0,0)'), use_container_width=True)
    with col_g2:
        st.plotly_chart(px.bar(df_global, x="País", y="Saldo_USD", text_auto=',.0f', title="Saldo Pendiente Externo (USD)", color_discrete_sequence=['#e53935']).update_layout(template="plotly_white", paper_bgcolor='rgba(0,0,0,0)'), use_container_width=True)

    st.markdown("---")

    # --- 4. DETALLE POR PAÍS ---
    st.sidebar.header("Filtros de Cartera")
    pais_sel = st.sidebar.selectbox("🚩 Seleccionar País:", hojas_paises)
    
    # Menú para mostrar u ocultar intercompany en el detalle
    ver_internos = st.sidebar.checkbox("Ver solo Clientes Internos", value=False)

    df_sel = datos_excel[pais_sel].copy()
    if 'Total' not in df_sel.columns and 'TOTAL' not in df_sel.columns:
        df_sel.columns = df_sel.iloc[0]; df_sel = df_sel[1:].reset_index(drop=True)
    df_sel.columns = [str(c).strip() for c in df_sel.columns]

    # Mapeo de columnas
    col_sal = next((c for c in df_sel.columns if c.upper() == 'SALDO'), 'Saldo')
    col_sub = next((c for c in df_sel.columns if c.upper() in ['SUBTOTAL', 'SERVICIOS']), 'Subtotal')
    col_iva = next((c for c in df_sel.columns if c.upper() in ['IVA', 'TOTAL IVA']), 'IVA')
    col_rets = [c for c in df_sel.columns if any(x in c.upper() for x in ['RETE', 'RET.'])]
    col_cli = next((c for c in df_sel.columns if c in ['Cliente', 'NOMBRE', 'Nombre Receptor']), 'Cliente')
    col_tot = next((c for c in df_sel.columns if c.upper() == 'TOTAL'), 'Total')
    col_car = next((c for c in df_sel.columns if c in ['Cartera', 'Estado', 'Estado de pago', 'Estatus']), 'Cartera')
    col_ven = next((c for c in df_sel.columns if 'vencimiento' in str(c).lower() or 'Vencimiento' in str(c)), None)

    # Lógica de Filtrado de Clientes Internos
    if ver_internos:
        df_sel = df_sel[df_sel[col_cli].astype(str).str.upper().isin([c.upper() for c in CLIENTES_EXCLUIR])]
        st.warning(f"⚠️ Mostrando únicamente facturación intercompany para {pais_sel}")
    else:
        df_sel = df_sel[~df_sel[col_cli].astype(str).str.upper().isin([c.upper() for c in CLIENTES_EXCLUIR])]

    # Conversión Financiera
    fin_cols = [col_sub, col_iva, col_tot, col_sal] + col_rets
    for c in fin_cols:
        if c in df_sel.columns: df_sel[c] = pd.to_numeric(df_sel[c], errors='coerce').fillna(0)
    df_sel['Total_Retenciones'] = df_sel[col_rets].sum(axis=1).abs() if col_rets else 0

    # Estados
    def cls_fin(row):
        t = str(row.get(col_car, "")).upper()
        if "NC" in t: return "NC"
        if any(x in t for x in ["ANULADA", "CANCELADO"]): return "ANULADA"
        if row.get(col_sal, 0) == 0: return "🔵 PAGADA"
        f_v = pd.to_datetime(row.get(col_ven), errors='coerce')
        return "🔴 EN MORA" if pd.notnull(f_v) and f_v < hoy else ("🟢 AL DÍA" if pd.notnull(f_v) else "⚪ SIN FECHA")
    
    df_sel['Estado_Final'] = df_sel.apply(cls_fin, axis=1)

    # --- KPIs ---
    st.header(f"Gestión Detallada {'Interna' if ver_internos else 'Externa'}: {pais_sel}")
    
    r1c1, r1c2, r1c3, r1c4, r1c5 = st.columns(5)
    v_bruta = df_sel[~df_sel['Estado_Final'].isin(["NC", "ANULADA"])][col_tot].sum()
    saldo_p = df_sel[col_sal].sum()
    
    r1c1.metric("Venta Bruta", f"$ {v_bruta:,.2f}")
    r1c2.metric("SALDO PENDIENTE", f"$ {saldo_p:,.2f}")
    r1c3.metric("En Mora", f"$ {df_sel[df_sel['Estado_Final']=='🔴 EN MORA'][col_sal].sum():,.2f}")
    r1c4.metric("DSO", f"{(saldo_p / v_bruta * 360) if v_bruta > 0 else 0:.0f} d")
    r1c5.metric("Docs", f"{len(df_sel):,d}")

    # --- TABLA Y EXPORTACIÓN ---
    st.subheader("Listado de Facturación")
    cols_f = [col_cli, col_sub, col_iva, 'Total_Retenciones', col_tot, col_sal, 'Estado_Final']
    st.dataframe(df_sel[cols_f].sort_values(by=col_sal, ascending=False).style.format({c: "{:,.2f}" for c in fin_cols if c in cols_f}))

    # --- OPCIÓN SEPARADA PARA AUDITAR INTERNOS (Solo si no están ya filtrados) ---
    if not ver_internos:
        with st.expander("🔍 Ver Datos de Clientes Internos (Intercompany)"):
            df_internos = datos_excel[pais_sel].copy()
            if 'Total' not in df_internos.columns: 
                df_internos.columns = df_internos.iloc[0]; df_internos = df_internos[1:].reset_index(drop=True)
            df_internos.columns = [str(c).strip() for c in df_internos.columns]
            df_internos = df_internos[df_internos[col_cli].astype(str).str.upper().isin([c.upper() for c in CLIENTES_EXCLUIR])]
            
            if not df_internos.empty:
                st.write("Estos datos NO están incluidos en los gráficos superiores:")
                st.dataframe(df_internos[[col_cli, col_tot, col_sal]])
            else:
                st.info("No se encontró facturación interna en este país.")

else:
    st.error("Error al cargar Drive.")