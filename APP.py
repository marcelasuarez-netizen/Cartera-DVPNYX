import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import io

# --- 1. CONFIGURACIÓN Y CONEXIÓN ---
ID_DRIVE = "1IlCy67vBvvcj1LrdCtUTJk9EjZADOOqN" 

st.set_page_config(page_title="Dashboard Cartera Global DVP-NYX", layout="wide")

@st.cache_data(ttl=300)
def cargar_toda_la_cartera(id_file):
    url = f"https://docs.google.com/spreadsheets/d/{id_file}/export?format=xlsx"
    try:
        response = requests.get(url)
        return pd.read_excel(io.BytesIO(response.content), sheet_name=None, engine='openpyxl')
    except Exception as e:
        st.error(f"Error de conexión con Drive: {e}")
        return None

# --- 2. CARGA Y FILTROS INICIALES ---
datos_excel = cargar_toda_la_cartera(ID_DRIVE)

if datos_excel:
    # Excluir Altabix y hojas basura
    hojas_excluir = ['Dashboard', 'Hoja 2', 'Hoja 4', 'altabix', 'ALTABIX', 'Instrucciones']
    hojas_paises = [h for h in datos_excel.keys() if h not in hojas_excluir]
    
    TASAS_REF = {"COP": 4000, "MXN": 18.5, "GTQ": 7.8, "USD": 1}
    hoy = datetime.now()

    st.title("🌎 Dashboard de Cartera 360: Global, Mora y Rotación")
    st.markdown("---")

    # --- 3. PROCESAMIENTO GLOBAL (USD Y ROTACIÓN) ---
    resumen_global = []
    
    for p in hojas_paises:
        df_p = datos_excel[p].copy()
        
        # Limpieza de cabecera dinámica
        if 'Total' not in df_p.columns and 'TOTAL' not in df_p.columns:
            df_p.columns = df_p.iloc[0]
            df_p = df_p[1:].reset_index(drop=True)
        
        df_p.columns = [str(c).strip() for c in df_p.columns]
        
        # Mapeo
        c_tot = next((c for c in df_p.columns if c.upper() == 'TOTAL'), 'Total')
        c_ven = next((c for c in df_p.columns if 'vencimiento' in c.lower()), None)
        c_mon = next((c for c in df_p.columns if 'Moneda' in c), None)
        c_est = next((c for c in df_p.columns if c in ['Cartera', 'Estado', 'Estado de pago']), 'Estado')

        if c_tot in df_p.columns:
            df_p[c_tot] = pd.to_numeric(df_p[c_tot], errors='coerce').fillna(0)
            
            # Clasificación de estados para cálculo
            def clasificar_global(row):
                txt = str(row.get(c_est, "")).upper()
                if "CRUCE" in txt or "PAGADA" in txt or pd.notnull(row.get('Fecha de Pago')):
                    return "COBRADO"
                return "PENDIENTE"

            df_p['Status_G'] = df_p.apply(clasificar_global, axis=1)
            
            # Conversión USD
            moneda = str(df_p[c_mon].iloc[0]).upper() if c_mon and not df_p.empty else "USD"
            tasa = TASAS_REF.get(moneda, 1)
            
            ventas_totales_usd = df_p[c_tot].sum() / tasa
            cartera_pendiente_usd = df_p[df_p['Status_G']=="PENDIENTE"][c_tot].sum() / tasa
            
            # Rotación (DSO) = (Cartera / Ventas) * 360
            rotacion = (cartera_pendiente_usd / ventas_totales_usd * 360) if ventas_totales_usd > 0 else 0
            
            resumen_global.append({
                "País": p, 
                "Mora_USD": cartera_pendiente_usd, 
                "Rotacion_Dias": rotacion,
                "Ventas_USD": ventas_totales_usd
            })

    df_g = pd.DataFrame(resumen_global)

    # --- 4. SECCIÓN GLOBAL (GRÁFICAS EN USD Y ROTACIÓN) ---
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("⚠️ Mora Consolidada (USD)")
        fig_mora = px.bar(df_g.sort_values("Mora_USD", ascending=False), 
                          x="País", y="Mora_USD", text_auto='.2s', color="Mora_USD",
                          color_continuous_scale="Reds")
        st.plotly_chart(fig_mora, use_container_width=True)

    with col2:
        st.subheader("🔄 Rotación de Cartera (Días DSO)")
        fig_rot = px.bar(df_g.sort_values("Rotacion_Dias"), 
                         x="País", y="Rotacion_Dias", text_auto='.0f',
                         title="Días que tardamos en cobrar por país",
                         color="Rotacion_Dias", color_continuous_scale="Blues_r")
        st.plotly_chart(fig_rot, use_container_width=True)

    st.markdown("---")

    # --- 5. DETALLE POR PAÍS (SOLICITUDES ANTERIORES) ---
    st.sidebar.header("Filtros de Detalle")
    pais_sel = st.sidebar.selectbox("🚩 Seleccionar País:", hojas_paises)
    
    df_sel = datos_excel[pais_sel].copy()
    if 'Total' not in df_sel.columns and 'TOTAL' not in df_sel.columns:
        df_sel.columns = df_sel.iloc[0]
        df_sel = df_sel[1:].reset_index(drop=True)
    df_sel.columns = [str(c).strip() for c in df_sel.columns]

    # Mapeo Dinámico
    col_año = next((c for c in df_sel.columns if c.upper() == 'AÑO'), 'Año')
    col_cli = next((c for c in df_sel.columns if c in ['Cliente', 'NOMBRE', 'Nombre Receptor']), 'Cliente')
    col_tot = next((c for c in df_sel.columns if c.upper() == 'TOTAL'), 'Total')
    col_ser = next((c for c in df_sel.columns if c.upper() in ['SERVICIO', 'CONCEPTO']), 'Servicio')
    col_ven = next((c for c in df_sel.columns if 'vencimiento' in c.lower()), None)
    col_car = next((c for c in df_sel.columns if c in ['Cartera', 'Estado', 'Estado de pago']), 'Cartera')

    # Filtros Año y Cliente
    if col_año in df_sel.columns:
        df_sel[col_año] = pd.to_numeric(df_sel[col_año], errors='coerce').fillna(0).astype(int)
        año_f = st.sidebar.selectbox("📅 Año:", ["Todos"] + sorted(list(df_sel[df_sel[col_año]>0][col_año].unique()), reverse=True))
        if año_f != "Todos": df_sel = df_sel[df_sel[col_año] == año_f]

    cli_f = st.sidebar.selectbox("👤 Cliente Global:", ["Todos"] + sorted(list(df_sel[col_cli].dropna().unique())))
    if cli_f != "Todos": df_sel = df_sel[df_sel[col_cli] == cli_f]

    # Lógica de Estados Completa
    def clasificar_completo(row):
        txt = str(row.get(col_car, "")).upper()
        if "CRUCE" in txt: return "🟠 CRUCE DE CUENTAS"
        if "NC" in txt: return "🟣 NOTA CRÉDITO"
        if "PAGADA" in txt or pd.notnull(row.get('Fecha de Pago')): return "🔵 PAGADA"
        f_v = pd.to_datetime(row.get(col_ven), errors='coerce')
        if pd.isnull(f_v): return "⚪ SIN FECHA"
        return "🔴 EN MORA" if f_v < hoy else "🟢 AL DÍA"

    df_sel['Estado_Final'] = df_sel.apply(clasificar_completo, axis=1)
    df_sel[col_tot] = pd.to_numeric(df_sel[col_tot], errors='coerce').fillna(0)

    # Dashboard de País
    st.header(f"Gestión: {pais_sel} | Cliente: {cli_f}")
    
    # Cálculo de Rotación por Cliente si se selecciona uno
    ventas_cli = df_sel[col_tot].sum()
    cartera_cli = df_sel[df_sel['Estado_Final'].isin(["🔴 EN MORA", "🟢 AL DÍA"])][col_tot].sum()
    rot_cli = (cartera_cli / ventas_cli * 360) if ventas_cli > 0 else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Cartera Total", f"$ {df_sel[col_tot].sum():,.0f}")
    k2.metric("Monto en Mora", f"$ {df_sel[df_sel['Estado_Final']=='🔴 EN MORA'][col_tot].sum():,.0f}", delta="Riesgo")
    k3.metric("Recaudado/Cruce", f"$ {df_sel[df_sel['Estado_Final'].isin(['🔵 PAGADA', '🟠 CRUCE DE CUENTAS'])][col_total].sum() if 'col_total' in locals() else 0:,.0f}")
    k4.metric("Rotación (Días DSO)", f"{rot_cli:.0f} Días")

    c_p1, c_p2 = st.columns(2)
    with c_p1:
        st.plotly_chart(px.pie(df_sel, values=col_tot, names='Estado_Final', hole=0.4, 
                               color='Estado_Final', color_discrete_map={
                                   "🔵 PAGADA": "#2980B9", "🔴 EN MORA": "#C0392B", 
                                   "🟠 CRUCE DE CUENTAS": "#E67E22", "🟢 AL DÍA": "#27AE60", "⚪ SIN FECHA": "#BDC3C7"
                               }), use_container_width=True)
    with c_p2:
        st.plotly_chart(px.bar(df_sel[col_ser].value_counts().reset_index(), x='count', y=col_ser, orientation='h', title="Mix de Servicios"), use_container_width=True)

    st.subheader("Maestro de Facturación")
    st.dataframe(df_sel[[col_cli, col_ser, col_tot, 'Estado_Final']])

else:
    st.error("Error al conectar con Google Drive. Revisa permisos.")