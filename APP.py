import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import io

# --- 1. CONFIGURACIÓN Y CONEXIÓN ---
ID_DRIVE = "1IlCy67vBvvcj1LrdCtUTJk9EjZADOOqN" 

st.set_page_config(page_title="Dashboard Cartera DVP-NYX 360", layout="wide")

# --- ESTILO CSS (Fondo Azul Claro, Tarjetas y Números Optimizados) ---
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

# Lista de Clientes Intercompany a filtrar
CLIENTES_INTERNOS = [
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

    # --- 3. PROCESAMIENTO GLOBAL USD (Filtrado) ---
    resumen_global = []
    for p in hojas_paises:
        df_p = datos_excel[p].copy()
        if 'Total' not in df_p.columns and 'TOTAL' not in df_p.columns:
            df_p.columns = df_p.iloc[0]; df_p = df_p[1:].reset_index(drop=True)
        df_p.columns = [str(c).strip() for c in df_p.columns]
        
        c_tot = next((c for c in df_p.columns if c.upper() == 'TOTAL'), 'Total')
        c_sal_g = next((c for c in df_p.columns if c.upper() == 'SALDO'), 'Saldo')
        c_mon = next((c for c in df_p.columns if 'Moneda' in c), None)
        c_cli = next((c for c in df_p.columns if c in ['Cliente', 'NOMBRE', 'Nombre Receptor']), 'Cliente')

        if c_tot in df_p.columns:
            # EXCLUSIÓN INTERCOMPANY
            df_p_ext = df_p[~df_p[c_cli].astype(str).str.upper().isin([c.upper() for c in CLIENTES_INTERNOS])]
            
            tasa = TASAS_REF.get(str(df_p[c_mon].iloc[0]).upper() if c_mon and not df_p.empty else "USD", 1)
            total_v_usd = pd.to_numeric(df_p_ext[c_tot], errors='coerce').fillna(0).sum() / tasa
            total_s_usd = pd.to_numeric(df_p_ext[c_sal_g], errors='coerce').fillna(0).sum() / tasa if c_sal_g in df_p_ext.columns else 0
            resumen_global.append({"País": p, "Venta_Total_USD": total_v_usd, "Saldo_USD": total_s_usd})

    df_global = pd.DataFrame(resumen_global)
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.plotly_chart(px.bar(df_global, x="País", y="Venta_Total_USD", text_auto=',.0f', title="Venta Externa (USD)", color="País").update_layout(template="plotly_white", paper_bgcolor='rgba(0,0,0,0)'), use_container_width=True)
    with col_g2:
        st.plotly_chart(px.bar(df_global, x="País", y="Saldo_USD", text_auto=',.0f', title="Saldo Pendiente Externo (USD)", color_discrete_sequence=['#e53935']).update_layout(template="plotly_white", paper_bgcolor='rgba(0,0,0,0)'), use_container_width=True)

    st.markdown("---")

    # --- 4. DETALLE POR PAÍS (Con todos los filtros originales) ---
    st.sidebar.header("Menú de Filtros")
    pais_sel = st.sidebar.selectbox("🚩 Seleccionar País:", hojas_paises)
    
    df_sel = datos_excel[pais_sel].copy()
    if 'Total' not in df_sel.columns and 'TOTAL' not in df_sel.columns:
        df_sel.columns = df_sel.iloc[0]; df_sel = df_sel[1:].reset_index(drop=True)
    df_sel.columns = [str(c).strip() for c in df_sel.columns]

    # Mapeo de columnas
    col_sal = next((c for c in df_sel.columns if c.upper() == 'SALDO'), 'Saldo')
    col_sub = next((c for c in df_sel.columns if c.upper() in ['SUBTOTAL', 'SERVICIOS']), 'Subtotal')
    col_iva = next((c for c in df_sel.columns if c.upper() in ['IVA', 'TOTAL IVA']), 'IVA')
    col_rets = [c for c in df_sel.columns if any(x in c.upper() for x in ['RETE', 'RET.'])]
    col_año = next((c for c in df_sel.columns if c.upper() in ['AÑO', 'Año']), 'Año')
    col_mes = next((c for c in df_sel.columns if c.upper() == 'MES'), 'Mes')
    col_cli = next((c for c in df_sel.columns if c in ['Cliente', 'NOMBRE', 'Nombre Receptor']), 'Cliente')
    col_tot = next((c for c in df_sel.columns if c.upper() == 'TOTAL'), 'Total')
    col_ser = next((c for c in df_sel.columns if c.upper() in ['SERVICIO', 'SERVICIO ']), 'Servicio')
    col_car = next((c for c in df_sel.columns if c in ['Cartera', 'Estado', 'Estado de pago', 'Estatus']), 'Cartera')
    col_ven = next((c for c in df_sel.columns if 'vencimiento' in str(c).lower() or 'Vencimiento' in str(c)), None)

    # SEPARAR DATOS INTERNOS PARA EL EXPANDER
    df_solo_internos = df_sel[df_sel[col_cli].astype(str).str.upper().isin([c.upper() for c in CLIENTES_INTERNOS])].copy()
    
    # FILTRAR PARA EL DASHBOARD PRINCIPAL (Externa)
    df_sel = df_sel[~df_sel[col_cli].astype(str).str.upper().isin([c.upper() for c in CLIENTES_INTERNOS])]

    # Conversión Financiera
    fin_cols = [col_sub, col_iva, col_tot, col_sal] + col_rets
    for c in fin_cols:
        if c in df_sel.columns: df_sel[c] = pd.to_numeric(df_sel[c], errors='coerce').fillna(0)
    df_sel['Total_Retenciones'] = df_sel[col_rets].sum(axis=1).abs() if col_rets else 0

    # RESTAURACIÓN DE FILTROS ORIGINALES
    if col_año in df_sel.columns:
        df_sel[col_año] = pd.to_numeric(df_sel[col_año], errors='coerce').fillna(0).astype(int)
        año_f = st.sidebar.selectbox("📅 Año:", ["Todos"] + sorted(list(df_sel[df_sel[col_año]>0][col_año].unique()), reverse=True))
        if año_f != "Todos": df_sel = df_sel[df_sel[col_año] == año_f]
    if col_mes in df_sel.columns:
        df_sel[col_mes] = pd.to_numeric(df_sel[col_mes], errors='coerce').fillna(0).astype(int)
        mes_f = st.sidebar.selectbox("📆 Mes:", ["Todos"] + [f"{m} - {MESES_NOMBRES.get(m, 'Mes')}" for m in sorted(list(df_sel[df_sel[col_mes]>0][col_mes].unique()))])
        if mes_f != "Todos": df_sel = df_sel[df_sel[col_mes] == int(mes_f.split(" - ")[0])]
    cli_f = st.sidebar.selectbox("👤 Cliente:", ["Todos"] + sorted(list(df_sel[col_cli].dropna().unique())))
    if cli_f != "Todos": df_sel = df_sel[df_sel[col_cli] == cli_f]

    # Estados
    def cls_fin(row):
        t = str(row.get(col_car, "")).upper()
        if "NC" in t: return "NC"
        if any(x in t for x in ["ANULADA", "CANCELADO"]): return "ANULADA"
        if row.get(col_sal, 0) == 0: return "🔵 PAGADA"
        f_v = pd.to_datetime(row.get(col_ven), errors='coerce')
        return "🔴 EN MORA" if pd.notnull(f_v) and f_v < hoy else ("🟢 AL DÍA" if pd.notnull(f_v) else "⚪ SIN FECHA")
    
    df_sel['Estado_Final'] = df_sel.apply(cls_fin, axis=1)

    # --- KPIs DETALLADOS ---
    st.header(f"Gestión Detallada Externa: {pais_sel}")
    
    r1c1, r1c2, r1c3, r1c4, r1c5 = st.columns(5)
    v_bruta = df_sel[~df_sel['Estado_Final'].isin(["NC", "ANULADA"])][col_tot].sum()
    saldo_p = df_sel[col_sal].sum()
    mora_p = df_sel[df_sel['Estado_Final']=='🔴 EN MORA'][col_sal].sum()
    
    r1c1.metric("Venta Bruta (Vig)", f"$ {v_bruta:,.2f}")
    r1c2.metric("SALDO PENDIENTE", f"$ {saldo_p:,.2f}")
    r1c3.metric("Monto en Mora", f"$ {mora_p:,.2f}")
    r1c4.metric("DSO (Días Rotación)", f"{(saldo_p / v_bruta * 360) if v_bruta > 0 else 0:.0f}")
    r1c5.metric("Emitidas", f"{len(df_sel):,d} Und")

    r2c1, r2c2, r2c3, r2c4 = st.columns(4)
    r2c1.metric("Subtotal", f"$ {df_sel[col_sub].sum():,.2f}")
    r2c2.metric("IVA", f"$ {df_sel[col_iva].sum():,.2f}")
    r2c3.metric("Retenciones", f"$ {df_sel['Total_Retenciones'].sum():,.2f}")
    r2c4.metric("Recaudado Real", f"$ {v_bruta - saldo_p:,.2f}")

    st.markdown("---")
    
    # --- GRÁFICAS ---
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(px.pie(df_sel, values=col_tot, names='Estado_Final', hole=0.5, title="Cartera por Estado ($)", color='Estado_Final', color_discrete_map={"🔵 PAGADA": "#1e88e5", "🔴 EN MORA": "#e53935", "🟠 CRUCE": "#fb8c00", "🟢 AL DÍA": "#43a047", "NC": "#8e24aa", "ANULADA": "#757575"}).update_layout(paper_bgcolor='rgba(0,0,0,0)'), use_container_width=True)
    with c2:
        df_audit = df_sel['Estado_Final'].apply(lambda x: x if x in ["NC", "ANULADA"] else "VIGENTE").value_counts().reset_index()
        df_audit.columns = ['Tipo', 'Cantidad']
        st.plotly_chart(px.bar(df_audit, x='Cantidad', y='Tipo', orientation='h', title="Auditoría: Tipo de Documento", color='Tipo', color_discrete_map={"NC": "#8e24aa", "ANULADA": "#757575", "VIGENTE": "#43a047"}).update_layout(paper_bgcolor='rgba(0,0,0,0)', showlegend=False), use_container_width=True)

    # Maestro de Facturación
    st.subheader("Listado Maestro de Facturación")
    cols_f = [col_cli, col_ser, col_sub, col_iva, 'Total_Retenciones', col_tot, col_sal, 'Estado_Final']
    st.dataframe(df_sel[cols_f].sort_values(by=col_sal, ascending=False).style.format({c: "{:,.2f}" for c in fin_cols if c in cols_f}))

    # --- PESTAÑA SEPARADA PARA CLIENTES INTERNOS ---
    st.markdown("---")
    with st.expander("🏢 VER FACTURACIÓN INTERNA (INTERCOMPANY)"):
        if not df_solo_internos.empty:
            st.info(f"Facturas de entidades del grupo en {pais_sel}")
            st.dataframe(df_solo_internos[[col_cli, col_ser, col_tot, col_sal]])
        else:
            st.write("No se encontraron registros internos en este país.")

else:
    st.error("Error al cargar Drive.")