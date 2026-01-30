import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import io

# --- 1. CONFIGURACIÓN Y CONEXIÓN ---
# Se mantiene el ID de Drive proporcionado
ID_DRIVE = "1IlCy67vBvvcj1LrdCtUTJk9EjZADOOqN" 

st.set_page_config(page_title="Dashboard Cartera DVP-NYX 360", layout="wide")

# --- ESTILO CSS PERSONALIZADO (Fondo Azul Claro y Tarjetas Blancas) ---
st.markdown("""
    <style>
    .stApp {
        background-color: #e3f2fd; /* Azul claro suave */
    }
    .stMetric {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border: 1px solid #bbdefb;
    }
    div[data-testid="stMetricValue"] {
        color: #1565c0;
    }
    /* Estilo para los títulos */
    h1, h2, h3 {
        color: #0d47a1;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=300)
def cargar_datos_completos(id_file):
    url = f"https://docs.google.com/spreadsheets/d/{id_file}/export?format=xlsx"
    try:
        response = requests.get(url)
        # Cargamos todas las hojas del Excel
        return pd.read_excel(io.BytesIO(response.content), sheet_name=None, engine='openpyxl')
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

# Mapeo de meses
MESES_NOMBRES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto", 
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

# --- 2. CARGA DE DATOS ---
st.title("📊 Dashboard Financiero Global: Auditoría y Cartera Consolidada")
st.markdown("---")

datos_excel = cargar_datos_completos(ID_DRIVE)

if datos_excel:
    # Excluir Altabix y hojas técnicas
    hojas_excluir = ['Dashboard', 'Hoja 2', 'Hoja 4', 'altabix', 'ALTABIX', 'Instrucciones']
    hojas_paises = [h for h in datos_excel.keys() if h not in hojas_excluir]
    
    # Tasas de cambio de referencia para consolidación
    TASAS_REF = {"COP": 4000, "MXN": 18.5, "GTQ": 7.8, "USD": 1}
    hoy = datetime.now()

    # --- 3. PROCESAMIENTO GLOBAL EN USD ---
    resumen_global = []
    for p in hojas_paises:
        df_p = datos_excel[p].copy()
        
        # Limpieza de cabecera dinámica
        if 'Total' not in df_p.columns and 'TOTAL' not in df_p.columns:
            df_p.columns = df_p.iloc[0]
            df_p = df_p[1:].reset_index(drop=True)
        
        df_p.columns = [str(c).strip() for c in df_p.columns]
        
        # Identificar columnas clave
        c_tot = next((c for c in df_p.columns if c.upper() == 'TOTAL'), 'Total')
        c_mon = next((c for c in df_p.columns if 'Moneda' in c), None)
        c_est = next((c for c in df_p.columns if c in ['Cartera', 'Estado', 'Estado de pago', 'Estatus']), 'Estado')
        c_ven = next((c for c in df_p.columns if 'vencimiento' in str(c).lower() or 'Vencimiento' in str(c)), None)

        if c_tot in df_p.columns:
            df_p[c_tot] = pd.to_numeric(df_p[c_tot], errors='coerce').fillna(0)
            
            # Clasificación para Mora (Vigente, sin pago, y vencida)
            def es_mora_global(row):
                txt = str(row.get(c_est, "")).upper()
                # Si es NC o Anulada, no es mora
                if any(x in txt for x in ["NC", "ANULADA", "CANCELADO", "ANULADO"]):
                    return False
                # Si ya está pagada o cruzada, no es mora
                if any(x in txt for x in ["PAGADA", "CRUCE"]):
                    return False
                if pd.notnull(row.get('Fecha de Pago')):
                    return False
                # Si la fecha de vencimiento ya pasó, es mora
                f_v = pd.to_datetime(row.get(c_ven), errors='coerce')
                return f_v < hoy if pd.notnull(f_v) else False

            df_p['Es_Mora'] = df_p.apply(es_mora_global, axis=1)
            
            # Conversión a USD
            moneda = str(df_p[c_mon].iloc[0]).upper() if c_mon and not df_p.empty else "USD"
            tasa = TASAS_REF.get(moneda, 1)
            
            # Cartera Total (Excluyendo Anuladas para el análisis de riesgo)
            df_valido = df_p[~df_p[c_est].str.contains("ANULADA|CANCELADO", case=False, na=False)]
            total_fact_usd = df_valido[c_tot].sum() / tasa
            total_mora_usd = df_p[df_p['Es_Mora']][c_tot].sum() / tasa
            
            resumen_global.append({
                "País": p, 
                "Cartera_Global_USD": total_fact_usd,
                "Mora_USD": total_mora_usd
            })

    df_global = pd.DataFrame(resumen_global)

    # --- 4. VISTA CONSOLIDADA (NUEVAS GRÁFICAS) ---
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        # Gráfica de Cartera Global (Solicitada)
        fig_cg = px.bar(df_global.sort_values("Cartera_Global_USD", ascending=False), 
                        x="País", y="Cartera_Global_USD", text_auto=',.2f', 
                        color="País", color_discrete_sequence=px.colors.qualitative.Safe,
                        title="Cartera Global por País (USD)")
        fig_cg.update_layout(template="plotly_white", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_cg, use_container_width=True)
        
    with col_g2:
        # Gráfica de Mora en USD
        fig_m = px.bar(df_global.sort_values("Mora_USD", ascending=False), 
                       x="País", y="Mora_USD", text_auto=',.2f', 
                       color="Mora_USD", color_continuous_scale="Reds", 
                       title="Monto en Mora por País (USD)")
        fig_m.update_layout(template="plotly_white", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_m, use_container_width=True)

    st.markdown("---")

    # --- 5. DETALLE POR PAÍS Y FILTROS ---
    st.sidebar.header("Opciones de Filtrado")
    pais_sel = st.sidebar.selectbox("🚩 Seleccionar País:", hojas_paises)
    
    df_sel = datos_excel[pais_sel].copy()
    if 'Total' not in df_sel.columns and 'TOTAL' not in df_sel.columns:
        df_sel.columns = df_sel.iloc[0]
        df_sel = df_sel[1:].reset_index(drop=True)
    df_sel.columns = [str(c).strip() for c in df_sel.columns]

    # Mapeo de columnas locales
    col_año = next((c for c in df_sel.columns if c.upper() == 'AÑO'), 'Año')
    col_mes = next((c for c in df_sel.columns if c.upper() == 'MES'), 'Mes')
    col_cli = next((c for c in df_sel.columns if c in ['Cliente', 'NOMBRE', 'Nombre Receptor']), 'Cliente')
    col_tot = next((c for c in df_sel.columns if c.upper() == 'TOTAL'), 'Total')
    col_ser = next((c for c in df_sel.columns if c.upper() in ['SERVICIO', 'SERVICIO ']), 'Servicio')
    col_ven = next((c for c in df_sel.columns if 'vencimiento' in str(c).lower() or 'Vencimiento' in str(c)), None)
    col_car = next((c for c in df_sel.columns if c in ['Cartera', 'Estado', 'Estado de pago', 'Estatus']), 'Cartera')

    # Filtros sidebar
    if col_año in df_sel.columns:
        df_sel[col_año] = pd.to_numeric(df_sel[col_año], errors='coerce').fillna(0).astype(int)
        años = ["Todos"] + sorted(list(df_sel[df_sel[col_año]>0][col_año].unique()), reverse=True)
        año_f = st.sidebar.selectbox("📅 Año:", años)
        if año_f != "Todos": df_sel = df_sel[df_sel[col_año] == año_f]

    if col_mes in df_sel.columns:
        df_sel[col_mes] = pd.to_numeric(df_sel[col_mes], errors='coerce').fillna(0).astype(int)
        opciones_mes = ["Todos"] + [f"{m} - {MESES_NOMBRES.get(m, 'Mes')}" for m in sorted(list(df_sel[df_sel[col_mes]>0][col_mes].unique()))]
        mes_f = st.sidebar.selectbox("📆 Mes:", opciones_mes)
        if mes_f != "Todos": df_sel = df_sel[df_sel[col_mes] == int(mes_f.split(" - ")[0])]

    clientes = ["Todos"] + sorted(list(df_sel[col_cli].dropna().unique()))
    cli_f = st.sidebar.selectbox("👤 Cliente:", clientes)
    if cli_f != "Todos": df_sel = df_sel[df_sel[col_cli] == cli_f]

    # Clasificación Auditoría (NC, ANULADA, VIGENTE)
    def clasificar_auditoria(row):
        txt = str(row.get(col_car, "")).upper()
        if "NC" in txt: return "NC"
        if any(x in txt for x in ["ANULADA", "CANCELADO", "ANULADO"]): return "ANULADA"
        return "VIGENTE"

    # Clasificación Financiera Detallada
    def clasificar_financiero(row):
        audit = clasificar_auditoria(row)
        if audit != "VIGENTE": return audit
        txt = str(row.get(col_car, "")).upper()
        if "CRUCE" in txt: return "🟠 CRUCE DE CUENTAS"
        if "PAGADA" in txt or pd.notnull(row.get('Fecha de Pago')): return "🔵 PAGADA"
        f_v = pd.to_datetime(row.get(col_ven), errors='coerce')
        if pd.isnull(f_v): return "⚪ SIN FECHA"
        return "🔴 EN MORA" if f_v < hoy else "🟢 AL DÍA"

    df_sel['Estado_Auditoria'] = df_sel.apply(clasificar_auditoria, axis=1)
    df_sel['Estado_Final'] = df_sel.apply(clasificar_financiero, axis=1)
    df_sel[col_tot] = pd.to_numeric(df_sel[col_tot], errors='coerce').fillna(0)

    # --- KPIs DE GESTIÓN (Con formato financiero) ---
    st.header(f"Gestión Detallada: {pais_sel}")
    k1, k2, k3, k4, k5 = st.columns(5)
    
    # Cartera Local Total (Solo documentos vigentes)
    v_total_vigente = df_sel[df_sel['Estado_Auditoria']=='VIGENTE'][col_tot].sum()
    mora_vigente = df_sel[df_sel['Estado_Final']=='🔴 EN MORA'][col_tot].sum()
    recaudado_vigente = df_sel[df_sel['Estado_Final'].isin(['🔵 PAGADA', '🟠 CRUCE DE CUENTAS'])][col_tot].sum()
    
    k1.metric("Cartera Local (Vigente)", f"$ {v_total_vigente:,.2f}")
    k2.metric("En Mora", f"$ {mora_vigente:,.2f}")
    k3.metric("Recaudado/Cruce", f"$ {recaudado_vigente:,.2f}")
    
    # DSO Local Simplificado
    p_cobrar_local = df_sel[df_sel['Estado_Final'].isin(["🔴 EN MORA", "🟢 AL DÍA"])][col_tot].sum()
    dso_l = (p_cobrar_local / v_total_vigente * 360) if v_total_vigente > 0 else 0
    k4.metric("DSO (Días)", f"{dso_l:.0f}")
    
    k5.metric("Emitidas", f"{len(df_sel):,d}")

    st.markdown("---")
    
    # --- GRÁFICAS DEL DETALLE ---
    c1, c2, c3 = st.columns(3)
    with c1:
        # Pie Chart: Cartera por Monto
        fig_p = px.pie(df_sel, values=col_tot, names='Estado_Final', hole=0.5, 
                       title="Monto por Estado ($)",
                       color='Estado_Final', color_discrete_map={
                           "🔵 PAGADA": "#1976d2", "🔴 EN MORA": "#d32f2f", 
                           "🟠 CRUCE DE CUENTAS": "#ffa000", "🟢 AL DÍA": "#388e3c", 
                           "NC": "#7b1fa2", "ANULADA": "#616161"})
        fig_p.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_p, use_container_width=True)
        
    with c2:
        # Bar Chart: Auditoría (Solicitada: Anulada, NC, Vigente)
        df_audit_cnt = df_sel['Estado_Auditoria'].value_counts().reset_index()
        fig_audit = px.bar(df_audit_cnt, x='count', y='Estado_Auditoria', orientation='h', 
                           text_auto=',d', title="Auditoría: Tipo de Documento",
                           color='Estado_Auditoria', color_discrete_map={
                               "NC": "#7b1fa2", "ANULADA": "#616161", "VIGENTE": "#388e3c"})
        fig_audit.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_audit, use_container_width=True)
        
    with c3:
        # Bar Chart: Servicios
        if col_ser in df_sel.columns:
            fig_s = px.bar(df_sel[col_ser].value_counts().reset_index(), 
                           x='count', y=col_ser, orientation='h', text_auto=',d',
                           color='count', color_continuous_scale='Blues', title="Volumen por Servicio")
            fig_s.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_s, use_container_width=True)

    # Maestro de Facturación Final con Formato
    st.subheader("Maestro de Facturación Analizado")
    st.dataframe(df_sel[[col_cli, col_ser, col_tot, 'Estado_Final']]
                 .sort_values(by=col_tot, ascending=False)
                 .style.format({col_tot: "{:,.2f}"}))

else:
    st.error("No se pudo conectar con el archivo de Drive. Verifica que sea público y el ID sea correcto.")