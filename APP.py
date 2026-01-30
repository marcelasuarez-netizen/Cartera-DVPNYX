import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import io

# --- 1. CONFIGURACIÓN Y CONEXIÓN ---
ID_DRIVE = "1IlCy67vBvvcj1LrdCtUTJk9EjZADOOqN" 

st.set_page_config(page_title="Dashboard Cartera DVP-NYX 360", layout="wide")

# --- ESTILO CSS (Fondo Azul Claro, Tarjetas y Letra Pequeña) ---
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
    [data-testid="stMetricValue"] { font-size: 1.15rem !important; color: #1565c0; font-weight: 700; }
    [data-testid="stMetricLabel"] { font-size: 0.75rem !important; color: #546e7a; }
    h1, h2, h3 { color: #0d47a1; }
    </style>
    """, unsafe_allow_html=True)

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
st.title("📊 Dashboard Financiero Global: Auditoría, Impuestos y Cartera")
st.markdown("---")

datos_excel = cargar_datos_completos(ID_DRIVE)

if datos_excel:
    hojas_excluir = ['Dashboard', 'Hoja 2', 'Hoja 4', 'altabix', 'ALTABIX', 'Instrucciones']
    hojas_paises = [h for h in datos_excel.keys() if h not in hojas_excluir]
    TASAS_REF = {"COP": 4000, "MXN": 18.5, "GTQ": 7.8, "USD": 1}
    hoy = datetime.now()

    # --- 3. PROCESAMIENTO GLOBAL USD ---
    resumen_global = []
    for p in hojas_paises:
        df_p = datos_excel[p].copy()
        if 'Total' not in df_p.columns and 'TOTAL' not in df_p.columns:
            df_p.columns = df_p.iloc[0]; df_p = df_p[1:].reset_index(drop=True)
        df_p.columns = [str(c).strip() for c in df_p.columns]
        c_tot = next((c for c in df_p.columns if c.upper() == 'TOTAL'), 'Total')
        c_mon = next((c for c in df_p.columns if 'Moneda' in c), None)
        c_est = next((c for c in df_p.columns if c in ['Cartera', 'Estado', 'Estado de pago', 'Estatus']), 'Estado')
        c_ven = next((c for c in df_p.columns if 'vencimiento' in str(c).lower() or 'Vencimiento' in str(c)), None)

        if c_tot in df_p.columns:
            df_p[c_tot] = pd.to_numeric(df_p[c_tot], errors='coerce').fillna(0)
            def es_mora_g(row):
                txt = str(row.get(c_est, "")).upper()
                if any(x in txt for x in ["NC", "ANULADA", "PAGADA", "CRUCE"]) or pd.notnull(row.get('Fecha de Pago')): return False
                f_v = pd.to_datetime(row.get(c_ven), errors='coerce')
                return f_v < hoy if pd.notnull(f_v) else False
            df_p['Es_Mora'] = df_p.apply(es_mora_g, axis=1)
            tasa = TASAS_REF.get(str(df_p[c_mon].iloc[0]).upper() if c_mon and not df_p.empty else "USD", 1)
            df_v = df_p[~df_p[c_est].str.contains("ANULADA|CANCELADO", case=False, na=False)]
            resumen_global.append({"País": p, "Cartera_Global_USD": df_v[c_tot].sum() / tasa, "Mora_USD": df_p[df_p['Es_Mora']][c_tot].sum() / tasa})

    df_global = pd.DataFrame(resumen_global)
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.plotly_chart(px.bar(df_global.sort_values("Cartera_Global_USD", ascending=False), x="País", y="Cartera_Global_USD", text_auto=',.0f', title="Cartera Global (USD)", color="País").update_layout(template="plotly_white", paper_bgcolor='rgba(0,0,0,0)'), use_container_width=True)
    with col_g2:
        st.plotly_chart(px.bar(df_global.sort_values("Mora_USD", ascending=False), x="País", y="Mora_USD", text_auto=',.0f', title="Mora por País (USD)", color_discrete_sequence=['#d32f2f']).update_layout(template="plotly_white", paper_bgcolor='rgba(0,0,0,0)'), use_container_width=True)

    st.markdown("---")

    # --- 4. DETALLE POR PAÍS ---
    st.sidebar.header("Menú de Filtros")
    pais_sel = st.sidebar.selectbox("🚩 Seleccionar País:", hojas_paises)
    df_sel = datos_excel[pais_sel].copy()
    if 'Total' not in df_sel.columns and 'TOTAL' not in df_sel.columns:
        df_sel.columns = df_sel.iloc[0]; df_sel = df_sel[1:].reset_index(drop=True)
    df_sel.columns = [str(c).strip() for c in df_sel.columns]

    # Mapeo de columnas
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

    # Convertir a Números
    for c in [col_sub, col_iva, col_tot] + col_rets:
        if c in df_sel.columns: df_sel[c] = pd.to_numeric(df_sel[c], errors='coerce').fillna(0)
    df_sel['Total_Retenciones'] = df_sel[col_rets].sum(axis=1).abs() if col_rets else 0

    # Filtros sidebar
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

    # --- CLASIFICACIÓN (Auditoría y Financiera) ---
    def cls_audit(row):
        t = str(row.get(col_car, "")).upper()
        if "NC" in t: return "NC"
        if any(x in t for x in ["ANULADA", "CANCELADO", "ANULADO"]): return "ANULADA"
        return "VIGENTE"

    def cls_fin(row):
        audit = cls_audit(row)
        if audit != "VIGENTE": return audit
        t = str(row.get(col_car, "")).upper()
        if "CRUCE" in t: return "🟠 CRUCE"
        if "PAGADA" in t or pd.notnull(row.get('Fecha de Pago')): return "🔵 PAGADA"
        f_v = pd.to_datetime(row.get(col_ven), errors='coerce')
        return "🔴 EN MORA" if pd.notnull(f_v) and f_v < hoy else ("🟢 AL DÍA" if pd.notnull(f_v) else "⚪ SIN FECHA")

    df_sel['Estado_Auditoria'] = df_sel.apply(cls_audit, axis=1)
    df_sel['Estado_Final'] = df_sel.apply(cls_fin, axis=1)

    # --- KPIs DETALLADOS ---
    st.header(f"Gestión Detallada: {pais_sel}")
    r1c1, r1c2, r1c3, r1c4 = st.columns(4)
    v_vig = df_sel[df_sel['Estado_Auditoria']=='VIGENTE'][col_tot].sum()
    mora = df_sel[df_sel['Estado_Final']=='🔴 EN MORA'][col_tot].sum()
    r1c1.metric("Cartera Local (Vig)", f"$ {v_vig:,.2f}")
    r1c2.metric("En Mora", f"$ {mora:,.2f}")
    r1c3.metric("Recaudado/Cruce", f"$ {df_sel[df_sel['Estado_Final'].isin(['🔵 PAGADA', '🟠 CRUCE'])][col_tot].sum():,.2f}")
    p_cobrar = df_sel[df_sel['Estado_Final'].isin(["🔴 EN MORA", "🟢 AL DÍA"])][col_tot].sum()
    dso_l = (p_cobrar / v_vig * 360) if v_vig > 0 else 0
    r1c4.metric("DSO (Días Rotación)", f"{dso_l:.0f}")

    r2c1, r2c2, r2c3, r2c4 = st.columns(4)
    r2c1.metric("Subtotal", f"$ {df_sel[col_sub].sum():,.2f}")
    r2c2.metric("IVA Total", f"$ {df_sel[col_iva].sum():,.2f}")
    r2c3.metric("Retenciones", f"$ {df_sel['Total_Retenciones'].sum():,.2f}")
    r2c4.metric("Emitidas", f"{len(df_sel):,d} Und")

    st.markdown("---")
    
    # --- GRÁFICAS ---
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(px.pie(df_sel, values=col_tot, names='Estado_Final', hole=0.5, title="Monto por Estado ($)", color='Estado_Final', color_discrete_map={"🔵 PAGADA": "#1e88e5", "🔴 EN MORA": "#e53935", "🟠 CRUCE": "#fb8c00", "🟢 AL DÍA": "#43a047", "NC": "#8e24aa", "ANULADA": "#757575"}).update_layout(paper_bgcolor='rgba(0,0,0,0)'), use_container_width=True)
    with c2:
        df_a = df_sel['Estado_Auditoria'].value_counts().reset_index()
        st.plotly_chart(px.bar(df_a, x='count', y='Estado_Auditoria', orientation='h', title="Auditoría: Tipo de Documento (Cant)", color='Estado_Auditoria', color_discrete_map={"NC": "#8e24aa", "ANULADA": "#757575", "VIGENTE": "#43a047"}).update_layout(paper_bgcolor='rgba(0,0,0,0)', showlegend=False), use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        comp_d = pd.DataFrame({"Concepto": ["Subtotal", "IVA", "Retenciones"], "Monto": [df_sel[col_sub].sum(), df_sel[col_iva].sum(), df_sel['Total_Retenciones'].sum()]})
        st.plotly_chart(px.bar(comp_d, x='Concepto', y='Monto', text_auto=',.2f', title="Composición Financiera", color='Concepto', color_discrete_sequence=['#2ecc71', '#3498db', '#e67e22']).update_layout(template="plotly_white", paper_bgcolor='rgba(0,0,0,0)'), use_container_width=True)
    with c4:
        if col_ser in df_sel.columns:
            st.plotly_chart(px.bar(df_sel[col_ser].value_counts().reset_index(), x='count', y=col_ser, orientation='h', text_auto=',d', title="Mix de Servicios (Cant)").update_layout(paper_bgcolor='rgba(0,0,0,0)'), use_container_width=True)

    # Maestro de Facturación Final
    st.subheader("Listado Maestro de Facturación")
    cols_tab = [col_cli, col_ser, col_sub, col_iva, 'Total_Retenciones', col_tot, 'Estado_Final']
    st.dataframe(df_sel[cols_tab].sort_values(by=col_tot, ascending=False).style.format({col_sub: "{:,.2f}", col_iva: "{:,.2f}", 'Total_Retenciones': "{:,.2f}", col_tot: "{:,.2f}"}))

else:
    st.error("Error al cargar Drive.")