import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import io

# --- 1. CONFIGURACIÓN ---
ID_DRIVE = "1IlCy67vBvvcj1LrdCtUTJk9EjZADOOqN" 

st.set_page_config(page_title="Dashboard Cartera DVP-NYX 360", layout="wide")

@st.cache_data(ttl=300)
def cargar_datos_completos(id_file):
    url = f"https://docs.google.com/spreadsheets/d/{id_file}/export?format=xlsx"
    try:
        response = requests.get(url)
        # Cargamos todas las hojas en un diccionario
        return pd.read_excel(io.BytesIO(response.content), sheet_name=None, engine='openpyxl')
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

# --- 2. CARGA Y LIMPIEZA ---
st.title("📊 Dashboard Financiero Global: Mora, Rotación y Servicios")
st.markdown("---")

datos_excel = cargar_datos_completos(ID_DRIVE)

if datos_excel:
    # Excluir Altabix y hojas de sistema
    hojas_excluir = ['Dashboard', 'Hoja 2', 'Hoja 4', 'altabix', 'ALTABIX', 'Instrucciones']
    hojas_paises = [h for h in datos_excel.keys() if h not in hojas_excluir]
    
    TASAS_REF = {"COP": 4000, "MXN": 18.5, "GTQ": 7.8, "USD": 1}
    hoy = datetime.now()

    # --- 3. ANÁLISIS GLOBAL (USD Y ROTACIÓN DSO) ---
    resumen_global = []
    
    for p in hojas_paises:
        df_p = datos_excel[p].copy()
        
        # Limpieza de cabecera: saltar basura si 'Total' no es columna
        if 'Total' not in df_p.columns and 'TOTAL' not in df_p.columns:
            df_p.columns = df_p.iloc[0]
            df_p = df_p[1:].reset_index(drop=True)
        
        df_p.columns = [str(c).strip() for c in df_p.columns]
        
        # Columnas Clave
        c_tot = next((c for c in df_p.columns if c.upper() == 'TOTAL'), 'Total')
        c_ven = next((c for c in df_p.columns if 'vencimiento' in c.lower()), None)
        c_mon = next((c for c in df_p.columns if 'Moneda' in c), None)
        c_est = next((c for c in df_p.columns if c in ['Cartera', 'Estado', 'Estado de pago']), 'Estado')

        if c_tot in df_p.columns:
            df_p[c_tot] = pd.to_numeric(df_p[c_tot], errors='coerce').fillna(0)
            
            # Clasificación de cobro
            def es_cobrado(row):
                txt = str(row.get(c_est, "")).upper()
                return "CRUCE" in txt or "PAGADA" in txt or pd.notnull(row.get('Fecha de Pago'))

            df_p['Es_Cobrado'] = df_p.apply(es_cobrado, axis=1)
            
            # Tasas y Conversión
            moneda = str(df_p[c_mon].iloc[0]).upper() if c_mon and not df_p.empty else "USD"
            tasa = TASAS_REF.get(moneda, 1)
            
            total_facturado_usd = df_p[c_tot].sum() / tasa
            total_pendiente_usd = df_p[~df_p['Es_Cobrado']][c_tot].sum() / tasa
            
            # DSO (Rotación) = (Pendiente / Total) * 360 días
            dso = (total_pendiente_usd / total_facturado_usd * 360) if total_facturado_usd > 0 else 0
            
            resumen_global.append({
                "País": p, 
                "Mora_USD": total_pendiente_usd, 
                "DSO_Dias": dso
            })

    df_global = pd.DataFrame(resumen_global)

    # --- 4. SECCIÓN GLOBAL (GRÁFICAS EN USD) ---
    st.subheader("🌎 Vista Gerencial Consolidada (USD)")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Monto en Mora por País**")
        fig_m = px.bar(df_global.sort_values("Mora_USD", ascending=False), 
                       x="País", y="Mora_USD", text_auto='.2s', color="Mora_USD",
                       color_continuous_scale="Reds")
        st.plotly_chart(fig_m, use_container_width=True)

    with col2:
        st.markdown("**Días de Rotación (DSO) - Eficiencia de Cobro**")
        fig_d = px.bar(df_global.sort_values("DSO_Dias"), 
                       x="País", y="DSO_Dias", text_auto='.0f', color="DSO_Dias",
                       color_continuous_scale="Blues_r")
        st.plotly_chart(fig_d, use_container_width=True)

    st.markdown("---")

    # --- 5. DETALLE POR PAÍS Y CLIENTE ---
    st.sidebar.header("Filtros Específicos")
    pais_sel = st.sidebar.selectbox("🚩 Seleccionar País:", hojas_paises)
    
    df_sel = datos_excel[pais_sel].copy()
    if 'Total' not in df_sel.columns and 'TOTAL' not in df_sel.columns:
        df_sel.columns = df_sel.iloc[0]
        df_sel = df_sel[1:].reset_index(drop=True)
    df_sel.columns = [str(c).strip() for c in df_sel.columns]

    # Mapeo de columnas solicitado (Servicio)
    col_año = next((c for c in df_sel.columns if c.upper() == 'AÑO'), 'Año')
    col_cli = next((c for c in df_sel.columns if c in ['Cliente', 'NOMBRE', 'Nombre Receptor']), 'Cliente')
    col_tot = next((c for c in df_sel.columns if c.upper() == 'TOTAL'), 'Total')
    col_ser = next((c for c in df_sel.columns if c.upper() in ['SERVICIO', 'SERVICIO ']), 'Servicio') # Búsqueda exacta
    col_ven = next((c for c in df_sel.columns if 'vencimiento' in c.lower()), None)
    col_car = next((c for c in df_sel.columns if c in ['Cartera', 'Estado', 'Estado de pago']), 'Cartera')

    # Filtros de Barra Lateral
    if col_año in df_sel.columns:
        df_sel[col_año] = pd.to_numeric(df_sel[col_año], errors='coerce').fillna(0).astype(int)
        list_a = ["Todos"] + sorted(list(df_sel[df_sel[col_año]>0][col_año].unique()), reverse=True)
        año_f = st.sidebar.selectbox("📅 Filtrar por Año:", list_a)
        if año_f != "Todos": df_sel = df_sel[df_sel[col_año] == año_f]

    cli_f = st.sidebar.selectbox("👤 Filtrar por Cliente:", ["Todos"] + sorted(list(df_sel[col_cli].dropna().unique())))
    if cli_f != "Todos": df_sel = df_sel[df_sel[col_cli] == cli_f]

    # Clasificación de Estados
    def clasificar_fin(row):
        txt = str(row.get(col_car, "")).upper()
        if "CRUCE" in txt: return "🟠 CRUCE DE CUENTAS"
        if "NC" in txt: return "🟣 NOTA CRÉDITO"
        if "PAGADA" in txt or pd.notnull(row.get('Fecha de Pago')): return "🔵 PAGADA"
        f_v = pd.to_datetime(row.get(col_ven), errors='coerce')
        if pd.isnull(f_v): return "⚪ SIN FECHA"
        return "🔴 EN MORA" if f_v < hoy else "🟢 AL DÍA"

    df_sel['Estado_Final'] = df_sel.apply(clasificar_fin, axis=1)
    df_sel[col_tot] = pd.to_numeric(df_sel[col_tot], errors='coerce').fillna(0)

    # Dashboard de Detalle
    st.header(f"Gestión Detallada: {pais_sel}")
    
    # Rotación local (DSO)
    ventas_loc = df_sel[col_tot].sum()
    pend_loc = df_sel[df_sel['Estado_Final'].isin(["🔴 EN MORA", "🟢 AL DÍA"])][col_tot].sum()
    dso_loc = (pend_loc / ventas_loc * 360) if ventas_loc > 0 else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Cartera Local", f"$ {df_sel[col_tot].sum():,.0f}")
    k2.metric("En Mora", f"$ {df_sel[df_sel['Estado_Final']=='🔴 EN MORA'][col_tot].sum():,.0f}", delta="Riesgo")
    k3.metric("Recaudado/Cruce", f"$ {df_sel[df_sel['Estado_Final'].isin(['🔵 PAGADA', '🟠 CRUCE DE CUENTAS'])][col_tot].sum():,.0f}")
    k4.metric("Días de Rotación", f"{dso_loc:.0f} Días")

    st.markdown("---")

    cp1, cp2 = st.columns(2)
    with cp1:
        st.subheader("Estado Financiero")
        fig_p = px.pie(df_sel, values=col_tot, names='Estado_Final', hole=0.4, 
                       color='Estado_Final', color_discrete_map={
                           "🔵 PAGADA": "#2980B9", "🔴 EN MORA": "#C0392B", 
                           "🟠 CRUCE DE CUENTAS": "#E67E22", "🟢 AL DÍA": "#27AE60", "⚪ SIN FECHA": "#BDC3C7"
                       })
        st.plotly_chart(fig_p, use_container_width=True)
    
    with cp2:
        st.subheader("Mix de Facturación por Servicio")
        if col_ser in df_sel.columns:
            # Gráfica de servicios solicitada
            fig_s = px.bar(df_sel[col_ser].value_counts().reset_index(), 
                           x='count', y=col_ser, orientation='h', color='count',
                           labels={'count': 'Cantidad de Facturas', col_ser: 'Servicio'},
                           color_continuous_scale='Greens')
            st.plotly_chart(fig_s, use_container_width=True)
        else:
            st.warning("No se encontró la columna de servicio en esta hoja.")

    st.subheader("Maestro de Facturación Analizado")
    st.dataframe(df_sel[[col_cli, col_ser, col_tot, 'Estado_Final']].sort_values(by=col_tot, ascending=False))

else:
    st.error("No se pudo conectar con el Drive. Revisa permisos.")