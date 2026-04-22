import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Cartera DVPNYX",
    layout="wide"
)

# -----------------------------
# ESTILO
# -----------------------------
st.markdown("""
<style>
body {
    background-color: #0D1B2A;
    color: white;
}
h1 {
    font-family: 'Playfair Display', serif;
}
</style>
""", unsafe_allow_html=True)

st.title("📊 Cartera DVPNYX")

# -----------------------------
# CARGA DE DATOS
# -----------------------------

url = "https://docs.google.com/spreadsheets/d/1IlCy67vBvvcj1LrdCtUTJk9EjZADOOqN/export?format=xlsx"

@st.cache_data
def load_data():

    sheets = [
        " Colombia",
        "Ecuador",
        " Guatemala",
        "DVP Mx",
        "NYX",
        " EEUU"
    ]

    df_list = []

    for sheet in sheets:
        temp = pd.read_excel(url, sheet_name=sheet, header=1)
        temp["Pais"] = sheet.strip()
        df_list.append(temp)

    df = pd.concat(df_list, ignore_index=True)

    return df

df = load_data()

# -----------------------------
# LIMPIEZA
# -----------------------------

df["Cliente"] = df["Cliente"].astype(str)
df["SALDO"] = pd.to_numeric(df["SALDO"], errors="coerce")
df["Dias"] = pd.to_numeric(df["Dias"], errors="coerce")

# -----------------------------
# EXCLUIR INTERCOMPANY
# -----------------------------

excluir = [
"TRADIOH LLC",
"N&X TECNOLOGIA Y NEGOCIOS",
"DVP SOFTWARE AND CONSULTING SA DE CV",
"DOUBLE V PARTNERS ECUADOR DVP",
"DOUBLE V PARTNERS GUATEMALA SOCIEDAD ANONIMA"
]

df = df[~df["Cliente"].isin(excluir)]

# -----------------------------
# FILTROS
# -----------------------------

st.sidebar.header("Filtros")

anio = st.sidebar.multiselect(
    "Año",
    options=sorted(df["Año"].dropna().unique()),
    default=df["Año"].dropna().unique()
)

pais = st.sidebar.multiselect(
    "País",
    options=df["Pais"].unique(),
    default=df["Pais"].unique()
)

mes = st.sidebar.multiselect(
    "Mes",
    options=sorted(df["Mes"].dropna().unique()),
    default=df["Mes"].dropna().unique()
)

cliente = st.sidebar.multiselect(
    "Cliente",
    options=df["Cliente"].unique()
)

df_f = df[
    (df["Año"].isin(anio)) &
    (df["Pais"].isin(pais)) &
    (df["Mes"].isin(mes))
]

if cliente:
    df_f = df_f[df_f["Cliente"].isin(cliente)]

# -----------------------------
# KPIs
# -----------------------------

total_cartera = df_f["SALDO"].sum()

vencido = df_f[df_f["Dias"] > 0]["SALDO"].sum()

aldia = df_f[df_f["Dias"] <= 0]["SALDO"].sum()

mora = (vencido / total_cartera * 100) if total_cartera > 0 else 0

col1, col2, col3, col4 = st.columns(4)

col1.metric("Cartera Total", f"${total_cartera:,.0f}")
col2.metric("Cartera Vencida", f"${vencido:,.0f}")
col3.metric("Cartera al día", f"${aldia:,.0f}")
col4.metric("% Mora", f"{mora:.2f}%")

# -----------------------------
# RESUMEN POR PAIS
# -----------------------------

st.subheader("Resumen por País")

resumen = df_f.groupby("Pais").agg(
    Clientes=("Cliente","nunique"),
    Total_Cartera=("SALDO","sum"),
    Vencido=("SALDO",lambda x: x[df_f["Dias"]>0].sum())
).reset_index()

st.dataframe(resumen, use_container_width=True)

# -----------------------------
# GRAFICA CARTERA POR PAIS
# -----------------------------

st.subheader("Distribución de Cartera por País")

fig = px.pie(
    df_f,
    values="SALDO",
    names="Pais",
    hole=0.5
)

st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# ANTIGÜEDAD CARTERA
# -----------------------------

st.subheader("Antigüedad de Cartera")

def bucket(d):
    if pd.isna(d):
        return "Al día"
    if d <= 30:
        return "1-30"
    if d <= 60:
        return "31-60"
    if d <= 90:
        return "61-90"
    return "+90"

df_f["Rango"] = df_f["Dias"].apply(bucket)

fig2 = px.bar(
    df_f,
    x="Rango",
    y="SALDO",
    color="Rango"
)

st.plotly_chart(fig2, use_container_width=True)

# -----------------------------
# TABLA PRINCIPAL
# -----------------------------

st.subheader("Tabla de Cartera")

tabla = df_f[[
"Cliente",
"Pais",
"Moneda",
"SALDO",
"Fecha de vencimiento",
"Dias",
"Estado"
]]

st.dataframe(tabla, use_container_width=True)