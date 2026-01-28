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
        st.error(f"Error de conexión: {e}")
        return None

# --- 2. CARGA DE DATOS ---
datos_excel = cargar_toda_la_cartera(ID_DRIVE)

if datos_excel:
    # Excluimos hojas técnicas y específicamente ALTABIX
    hojas_excluir = ['Dashboard', 'Hoja 2', 'Hoja 4', 'altabix', 'ALTABIX', 'Instrucciones']
    hojas_paises = [h for h in datos_excel.keys() if h not in hojas_excluir]

    st.title("🌎 Dashboard de Cartera Consolidado (USD)")
    st.markdown("---")

    # --- 3. LÓGICA DE CONVERSIÓN A USD (ANÁLISIS GLOBAL) ---
    resumen_global = []
    hoy = datetime.now()

    # Tasas de cambio de referencia (puedes ajustarlas aquí o el código las toma del Excel si existen)
    TASAS_DEFAULT = {"COP": 3950, "MXN": 17.5, "GTQ": 7.8, "USD": 1}

    for pais in hojas_paises:
        df_temp = datos_excel[pais].copy()
        
        # Limpieza rápida de cabeceras
        if 'Total' not in df_temp.columns and 'TOTAL' not in df_temp.columns:
            df_temp.columns = df_temp.iloc[0]
            df_temp = df_temp[1:].reset_index(drop=True)
        
        df_temp.columns = [str(c).strip() for c in df_temp.columns]
        
        # Mapeo de columnas
        col_t = next((c for c in df_temp.columns if c.upper() == 'TOTAL'), None)
        col_v = next((c for c in df_temp.columns if 'vencimiento' in c.lower()), None)
        col_tc = next((c for c in df_temp.columns if 'Cambio' in c or 'TRM' in c), None)
        col_mon = next((c for c in df_temp.columns if 'Moneda' in c), None)
        col_est = next((c for c in df_temp.columns if c in ['Cartera', 'Estado', 'Estado de pago']), 'Estado')

        if col_t and col_v:
            df_temp[col_t] = pd.to_numeric(df_temp[col_t], errors='coerce').fillna(0)
            df_temp[col_v] = pd.to_datetime(df_temp[col_v], errors='coerce')
            
            # Identificar Mora
            df_mora = df_temp[df_temp[col_v] < hoy].copy()
            # Excluir las ya pagadas o cruzadas
            if col_est in df_mora.columns:
                df_mora = df_mora[~df_mora[col_est].str.contains("PAGADA|Cruce|NC", case=False, na=False)]
            
            total_local = df_mora[col_t].sum()
            
            # Obtener Tasa de Cambio
            tasa = 1
            moneda = str(df_temp[col_mon].iloc[0]).upper() if col_mon and not df_temp.empty else "USD"
            
            if col_tc and not df_temp.empty:
                tasa_val = pd.to_numeric(df_temp[col_tc], errors='coerce').median()
                tasa = tasa_val if tasa_val > 0 else TASAS_DEFAULT.get(moneda, 1)
            else:
                tasa = TASAS_DEFAULT.get(moneda, 1)
            
            # Convertir a USD
            total_usd = total_local / tasa if tasa != 0 else total_local
            resumen_global.append({"País": pais, "Mora USD": total_usd})

    df_global_usd = pd.DataFrame(resumen_global)

    # --- 4. VISUALIZACIÓN GLOBAL ---
    st.subheader("⚠️ Resumen de Mora por País (Equivalente en USD)")
    
    if not df_global_usd.empty:
        c1, c2 = st.columns([2, 1])
        with c1:
            fig_global = px.bar(df_global_usd.sort_values("Mora USD", ascending=False), 
                                x="País", y="Mora USD", 
                                text_auto='.2s',
                                title="Deuda en Mora Consolidada (Dólares)",
                                color="Mora USD", color_continuous_scale="Reds")
            st.plotly_chart(fig_global, use_container_width=True)
        
        with c2:
            total_mora_region = df_global_usd["Mora USD"].sum()
            st.metric("Total Mora Regional", f"USD {total_mora_region:,.2f}")
            st.info("Nota: Los valores de COP, MXN y GTQ han sido convertidos a USD usando la tasa de cambio de la factura o promedio del mercado.")
    
    st.markdown("---")

    # --- 5. DETALLE POR PAÍS SELECCIONADO ---
    st.sidebar.header("Detalle Individual")
    pais_sel = st.sidebar.selectbox("🚩 Seleccionar País para ver facturas:", hojas_paises)
    
    # Aquí reutilizamos tu lógica anterior para el detalle del país
    df_pais = datos_excel[pais_sel].copy()
    if 'Total' not in df_pais.columns and 'TOTAL' not in df_pais.columns:
        df_pais.columns = df_pais.iloc[0]
        df_pais = df_pais[1:].reset_index(drop=True)
    
    df_pais.columns = [str(c).strip() for c in df_pais.columns]
    col_t_p = next((c for c in df_pais.columns if c.upper() == 'TOTAL'), 'Total')
    col_c_p = next((c for c in df_pais.columns if c in ['Cliente', 'NOMBRE', 'Nombre Receptor']), 'Cliente')
    
    st.subheader(f"Facturación Detallada: {pais_sel}")
    st.dataframe(df_pais[[col_c_p, col_t_p]].head(10))

else:
    st.error("No se pudo cargar la información desde Google Drive. Revisa los permisos.")