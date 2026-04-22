import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Cartera DVPNYX", layout="wide")

st.title("📊 Cartera DVPNYX")

# -----------------------------
# CONEXION GOOGLE SHEETS
# -----------------------------

SHEET_ID = "1IlCy67vBvvcj1LrdCtUTJk9EjZADOOqN"
SHEET_NAME = "Base"

url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

df = pd.read_csv(url)

# -----------------------------
# LIMPIEZA DE DATOS
# -----------------------------

df["Fecha_factura"] = pd.to_datetime(df["Fecha_factura"])
df["Fecha_vencimiento"] = pd.to_datetime(df["Fecha_vencimiento"])

hoy = pd.to_datetime(datetime.today())

df["dias_mora"] = (hoy - df["Fecha_vencimiento"]).dt.days
df["dias_mora"] = df["dias_mora"].apply(lambda x: x if x > 0 else 0)

df["estado_cartera"] = df["dias_mora"].apply(lambda x: "Vencido" if x > 0 else "Al día")

# -----------------------------
# CAMPOS DE TIEMPO
# -----------------------------

df["Año"] = df["Fecha_factura"].dt.year
df["Mes"] = df["Fecha_factura"].dt.month_name()

# -----------------------------
# FILTROS
# -----------------------------

st.sidebar.header("Filtros")

anio = st.sidebar.multiselect(
    "Año",
    options=df["Año"].unique(),
    default=df["Año"].unique()
)

pais = st.sidebar.multiselect(
    "País",
    options=df["Pais"].unique(),
    default=df["Pais"].unique()
)

mes = st.sidebar.multiselect(
    "Mes",
    options=df["Mes"].unique(),
    default=df["Mes"].unique()
)

cliente = st.sidebar.multiselect(
    "Cliente",
    options=df["Cliente"].unique(),
    default=df["Cliente"].unique()
)

df_filtrado = df[
    (df["Año"].isin(anio)) &
    (df["Pais"].isin(pais)) &
    (df["Mes"].isin(mes)) &
    (df["Cliente"].isin(cliente))
]

# -----------------------------
# KPIs
# -----------------------------

cartera_total = df_filtrado["Valor"].sum()
cartera_vencida = df_filtrado[df_filtrado["estado_cartera"]=="Vencido"]["Valor"].sum()
cartera_dia = df_filtrado[df_filtrado["estado_cartera"]=="Al día"]["Valor"].sum()

porcentaje_mora = (cartera_vencida / cartera_total)*100 if cartera_total>0 else 0

dias_promedio = df_filtrado[df_filtrado["estado_cartera"]=="Vencido"]["dias_mora"].mean()

def semaforo(p):
    if p <= 15:
        return "🟢 Riesgo Bajo"
    elif p <= 35:
        return "🟡 Riesgo Medio"
    elif p <= 60:
        return "🟠 Riesgo Alto"
    else:
        return "🔴 Riesgo Crítico"

col1,col2,col3,col4,col5 = st.columns(5)

col1.metric("Cartera Total USD", f"${cartera_total:,.0f}")
col2.metric("Cartera al Día", f"${cartera_dia:,.0f}")
col3.metric("Cartera Vencida", f"${cartera_vencida:,.0f}")
col4.metric("% Mora", f"{porcentaje_mora:.2f}%")
col5.metric("Promedio días mora", f"{dias_promedio:.1f}")

st.subheader(f"Semáforo de riesgo: {semaforo(porcentaje_mora)}")

# -----------------------------
# RESUMEN POR PAIS
# -----------------------------

st.subheader("Resumen de Cartera por País (USD)")

resumen_pais = df_filtrado.pivot_table(
    values="Valor",
    index="Pais",
    columns="estado_cartera",
    aggfunc="sum",
    fill_value=0
).reset_index()

st.dataframe(resumen_pais, use_container_width=True)

# -----------------------------
# GRAFICO CARTERA POR PAIS
# -----------------------------

cartera_pais = df_filtrado.groupby("Pais")["Valor"].sum().reset_index()

fig_pais = px.bar(
    cartera_pais,
    x="Pais",
    y="Valor",
    title="Cartera Total por País"
)

st.plotly_chart(fig_pais, use_container_width=True)

# -----------------------------
# DISTRIBUCION CARTERA
# -----------------------------

estado_data = df_filtrado.groupby("estado_cartera")["Valor"].sum().reset_index()

fig_pie = px.pie(
    estado_data,
    names="estado_cartera",
    values="Valor",
    title="Distribución de Cartera"
)

st.plotly_chart(fig_pie, use_container_width=True)

# -----------------------------
# EVOLUCION MENSUAL
# -----------------------------

df_filtrado["Periodo"] = df_filtrado["Fecha_factura"].dt.to_period("M").astype(str)

evolucion = df_filtrado.groupby("Periodo")["Valor"].sum().reset_index()

fig_line = px.line(
    evolucion,
    x="Periodo",
    y="Valor",
    title="Evolución mensual de la cartera"
)

st.plotly_chart(fig_line, use_container_width=True)

# -----------------------------
# TABLA DE GESTION
# -----------------------------

st.subheader("Gestión de Cartera")

tabla = df_filtrado[
    ["Cliente","Pais","Factura","Fecha_factura","Fecha_vencimiento","Valor","dias_mora","estado_cartera","Observaciones"]
]

st.dataframe(tabla, use_container_width=True)