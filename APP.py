import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import io

# --- 1. CONFIGURACIÓN Y CONEXIÓN ---
ID_DRIVE = "1IlCy67vBvvcj1LrdCtUTJk9EjZADOOqN" 

st.set_page_config(page_title="Dashboard Cartera DVP-NYX 360", layout="wide")

@st.cache_data(ttl=300)
def cargar_datos_completos(id_file):
    url = f"https://docs.google.com/spreadsheets/d/{id_file}/export?format=xlsx"
    try:
        response = requests.get(url)
        return pd.read_excel(io.BytesIO(response.content), sheet_name=None, engine='openpyxl')
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

# Mapeo de meses para el desplegable
MESES_NOMBRES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto", 
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

# --- 2. CARGA DE DATOS ---
st.title("📊 Dashboard Financiero Global: Mora, Rotación y Meses")
st.markdown("---")

datos_excel = cargar_datos_completos(ID_DRIVE)

if datos_excel:
    # Excluir Altabix y hojas técnicas
    hojas_excluir = ['Dashboard', 'Hoja 2', 'Hoja 4', 'altabix', 'ALTABIX', 'Instrucciones']
    hojas_paises = [h for h in datos_excel.keys() if h not in hojas_excluir]
    
    TASAS_REF = {"COP": 4000, "MXN": 18.5, "GTQ": 7.8, "USD": 1}
    hoy = datetime.now()

    # --- 3. ANÁLISIS GLOBAL EN USD (MORA Y DSO) ---
    resumen_global = []
    for p in hojas_paises:
        df_p = datos_excel[p].copy()
        if 'Total' not in df_p.columns and 'TOTAL' not in df_p.columns:
            df_p.columns = df_p.iloc[0]
            df_p = df_p[1:].reset_index(drop=True)
        df_p.columns = [str(c).strip() for c in df_p.columns]
        
        c_tot = next((c for c in df_p.columns if c.upper() == 'TOTAL'), 'Total')
        c_mon = next((c for c in df_p.columns if 'Moneda' in c), None)
        c_est = next((c for c in df_p.columns if c in ['Cartera', 'Estado', 'Estado de pago']), 'Estado')

        if c_tot in df_p.columns:
            df_p[c_tot] = pd.to_numeric(df_p[c_tot], errors='coerce').fillna(0)
            def es_cobrado(row):
                txt = str(row.get(c_est, "")).upper()
                return "CRUCE" in txt or "PAGADA" in txt or pd.notnull(row.get('Fecha de Pago'))
            
            df_p['Es_Cobrado'] = df_p.apply(es_cobrado, axis=1)
            moneda = str(df_p[c_mon].iloc[0]).upper() if c_mon and not df_p.empty else "USD"
            tasa = TASAS_REF.get(moneda, 1)
            
            total_fact_usd = df_p[c_tot].sum() / tasa
            total_pend_usd = df_p[~df_p['Es_Cobrado']][c_tot].sum() / tasa
            dso = (total_pend_usd / total_fact_usd * 360) if total_fact_usd > 0 else 0
            
            resumen_global.append({"País": p, "Mora_USD": total_pend_usd, "DSO_Dias": dso})

    df_global = pd.DataFrame(resumen_global)

    # --- 4. SECCIÓN GLOBAL ---
    st.subheader("🌎 Vista Consolidada Regional (USD)")
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.plotly_chart(px.bar(df_global.sort_values("Mora_USD", ascending=False), x="País", y="Mora_USD", text_auto='.2s', color="Mora_USD", color_continuous_scale="Reds", title="Mora en USD por País"), use_container_width=True)
    with col_g2:
        st.plotly_chart(px.bar(df_global.sort_values("DSO_Dias"), x="País", y="DSO_Dias", text_auto='.0f', color="DSO_Dias", color_continuous_scale="Blues_r", title="Días de Rotación (DSO)"), use_container_width=True)

    st.markdown("---")

    # --- 5. DETALLE POR PAÍS CON FILTROS DE AÑO, MES Y CLIENTE ---
    st.sidebar.header("Filtros de Detalle")
    pais_sel = st.sidebar.selectbox("🚩 1. Seleccionar País:", hojas_paises)
    
    df_sel = datos_excel[pais_sel].copy()
    if 'Total' not in df_sel.columns and 'TOTAL' not in df_sel.columns:
        df_sel.columns = df_sel.iloc[0]
        df_sel = df_sel[1:].reset_index(drop=True)
    df_sel.columns = [str(c).strip() for c in df_sel.columns]

    # Mapeo de columnas
    col_año = next((c for c in df_sel.columns if c.upper() == 'AÑO'), 'Año')
    col_mes = next((c for c in df_sel.columns if c.upper() == 'MES'), 'Mes')
    col_cli = next((c for c in df_sel.columns if c in ['Cliente', 'NOMBRE', 'Nombre Receptor']), 'Cliente')
    col_tot = next((c for c in df_sel.columns if c.upper() == 'TOTAL'), 'Total')
    col_ser = next((c for c in df_sel.columns if c.upper() in ['SERVICIO', 'SERVICIO ']), 'Servicio')
    col_ven = next((c for c in df_sel.columns if 'vencimiento' in c.lower()), None)
    col_car = next((c for c in df_sel.columns if c in ['Cartera', 'Estado', 'Estado de pago']), 'Cartera')

    # Filtro de Año
    if col_año in df_sel.columns:
        df_sel[col_año] = pd.to_numeric(df_sel[col_año], errors='coerce').fillna(0).astype(int)
        años = ["Todos"] + sorted(list(df_sel[df_sel[col_año]>0][col_año].unique()), reverse=True)
        año_f = st.sidebar.selectbox("📅 2. Seleccionar Año:", años)
        if año_f != "Todos": df_sel = df_sel[df_sel[col_año] == año_f]

    # --- FILTRO DE MES (NUEVO) ---
    if col_mes in df_sel.columns:
        df_sel[col_mes] = pd.to_numeric(df_sel[col_mes], errors='coerce').fillna(0).astype(int)
        meses_ids = sorted(list(df_sel[df_sel[col_mes]>0][col_mes].unique()))
        # Creamos opciones como "1 - Enero", "2 - Febrero"
        opciones_mes = ["Todos"] + [f"{m} - {MESES_NOMBRES.get(m, 'Desconocido')}" for m in meses_ids]
        mes_f_raw = st.sidebar.selectbox("📆 3. Seleccionar Mes:", opciones_mes)
        
        if mes_f_raw != "Todos":
            mes_id_sel = int(mes_f_raw.split(" - ")[0])
            df_sel = df_sel[df_sel[col_mes] == mes_id_sel]

    # Filtro de Cliente
    clientes = ["Todos"] + sorted(list(df_sel[col_cli].dropna().unique()))
    cli_f = st.sidebar.selectbox("👤 4. Seleccionar Cliente:", clientes)
    if cli_f != "Todos": df_sel = df_sel[df_sel[col_cli] == cli_f]

    # Clasificación y KPIs
    def clasificar_final(row):
        txt = str(row.get(col_car, "")).upper()
        if "CRUCE" in txt: return "🟠 CRUCE DE CUENTAS"
        if "NC" in txt: return "🟣 NOTA CRÉDITO"
        if "PAGADA" in txt or pd.notnull(row.get('Fecha de Pago')): return "🔵 PAGADA"
        f_v = pd.to_datetime(row.get(col_ven), errors='coerce')
        if pd.isnull(f_v): return "⚪ SIN FECHA"
        return "🔴 EN MORA" if f_v < hoy else "🟢 AL DÍA"

    df_sel['Estado_Final'] = df_sel.apply(clasificar_final, axis=1)
    df_sel[col_tot] = pd.to_numeric(df_sel[col_tot], errors='coerce').fillna(0)

    # Dashboard Detalle
    st.header(f"Gestión Detallada: {pais_sel}")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Cartera Local", f"$ {df_sel[col_tot].sum():,.0f}")
    k2.metric("En Mora", f"$ {df_sel[df_sel['Estado_Final']=='🔴 EN MORA'][col_tot].sum():,.0f}", delta="Riesgo")
    k3.metric("Recaudado/Cruce", f"$ {df_sel[df_sel['Estado_Final'].isin(['🔵 PAGADA', '🟠 CRUCE DE CUENTAS'])][col_tot].sum():,.0f}")
    
    # Rotación local
    v_loc = df_sel[col_tot].sum()
    p_loc = df_sel[df_sel['Estado_Final'].isin(["🔴 EN MORA", "🟢 AL DÍA"])][col_tot].sum()
    dso_l = (p_loc / v_loc * 360) if v_loc > 0 else 0
    k4.metric("DSO (Días)", f"{dso_l:.0f} Días")

    st.markdown("---")
    c_d1, c_d2 = st.columns(2)
    with c_d1:
        st.plotly_chart(px.pie(df_sel, values=col_tot, names='Estado_Final', hole=0.4, title="Estado Financiero",
                               color='Estado_Final', color_discrete_map={"🔵 PAGADA": "#2980B9", "🔴 EN MORA": "#C0392B", "🟠 CRUCE DE CUENTAS": "#E67E22", "🟢 AL DÍA": "#27AE60", "🟣 NOTA CRÉDITO": "#8E44AD"}), use_container_width=True)
    with c_d2:
        if col_ser in df_sel.columns:
            st.plotly_chart(px.bar(df_sel[col_ser].value_counts().reset_index(), x='count', y=col_ser, orientation='h', color='count', color_continuous_scale='Greens', title="Mix de Servicios"), use_container_width=True)

    st.subheader("Listado de Facturas Filtradas")
    st.dataframe(df_sel[[col_cli, col_ser, col_tot, 'Estado_Final']].sort_values(by=col_tot, ascending=False))

else:
    st.error("Error al conectar con el Drive. Revisa permisos.")