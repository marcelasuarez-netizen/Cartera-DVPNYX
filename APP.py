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
# LIMPIAR NOMBRES DE COLUMNAS
# -----------------------------

df.columns = df.columns.str.strip()
df.columns = df.columns.str.replace(" ", "_")

# ver columnas cargadas
st.write("Columnas detectadas:", df.columns)

# -----------------------------
# FECHAS
# -----------------------------

df["Fecha_factura"] = pd.to_datetime(df["Fecha_factura"], errors="coerce")
df["Fecha_vencimiento"] = pd.to_datetime(df["Fecha_vencimiento"], errors="coerce")

hoy = pd.to_datetime(datetime.today())

# -----------------------------
# CALCULO DE MORA
# -----------------------------

df["dias_mora"] = (hoy - df["Fecha_vencimiento"]).dt.days
df["dias_mora"] = df["dias_mora"].apply(lambda x: x if x > 0 else 0)

df["estado_cartera"] = df["dias_mora"].apply(
    lambda x: "Vencido" if x > 0 else "Al día"
)

# -----------------------------
# CAMPOS TIEMPO
# -----------------------------

df["Año"] = df["Fecha_factura"].dt.year
df["Mes"] = df["Fecha_factura"].dt.month_name()

# -----------------------------
# FILTROS
# -----------------------------

st.sidebar.header("Filtros")

anio = st.sidebar.multiselect("Año", df["Año"].dropna().unique(), default=df["Año"].dropna().unique())
pais = st.sidebar.multiselect("País", df["Pais"].dropna().unique(), default=df["Pais"].dropna().unique())
mes = st.sidebar.multiselect("Mes", df["Mes"].dropna().unique(), default=df["Mes"].dropna().unique())
cliente = st.sidebar.multiselect("Cliente", df["Cliente"].dropna().unique(), default=df["Cliente"].dropna().unique())

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
cartera_dia = df_filtrado[df_filtrado["estado_cartera"]=="Al_día"]["Valor"].sum()

porcentaje_mora = (cartera_vencida / cartera_total)*100 if cartera_total>0 else 0

col1,col2,col3 = st.columns(3)

col1.metric("Cartera Total USD", f"${cartera_total:,.0f}")
col2.metric("Cartera al Día", f"${cartera_dia:,.0f}")
col3.metric("Cartera Vencida", f"${cartera_vencida:,.0f}")