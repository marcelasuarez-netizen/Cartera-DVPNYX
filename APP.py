import streamlit as st
import pandas as pd

st.set_page_config(page_title="Dashboard Financiero", layout="wide")

st.title("📊 Dashboard de Datos - Google Sheets")

# ID del Google Sheet
sheet_id = "1IlCy67vBvvcj1LrdCtUTJk9EjZADOOqN"
gid = "2023435007"

# URL para leer el archivo como CSV
url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

# Leer datos
df = pd.read_csv(url)

# Mostrar tabla
st.subheader("Datos del archivo")
st.dataframe(df)

# =========================
# KPIs
# =========================

col1, col2, col3 = st.columns(3)

if len(df.columns) >= 3:
    col1.metric("Filas", len(df))
    col2.metric("Columnas", len(df.columns))
    col3.metric("Valores nulos", df.isnull().sum().sum())

# =========================
# Filtros
# =========================

st.sidebar.header("Filtros")

columna = st.sidebar.selectbox("Seleccionar columna", df.columns)

valor = st.sidebar.selectbox("Seleccionar valor", df[columna].dropna().unique())

df_filtrado = df[df[columna] == valor]

st.subheader("Datos filtrados")
st.dataframe(df_filtrado)

# =========================
# Gráfica
# =========================

st.subheader("Gráfica")

col_x = st.selectbox("Eje X", df.columns)
col_y = st.selectbox("Eje Y", df.columns)

try:
    st.bar_chart(df[[col_x, col_y]].set_index(col_x))
except:
    st.warning("Selecciona columnas válidas para graficar.")