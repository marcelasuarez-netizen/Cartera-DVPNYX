import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# ---------------------------------------------------
# CONFIGURACIÓN GENERAL
# ---------------------------------------------------

st.set_page_config(
    page_title="Cartera DVPNXY",
    layout="wide"
)

# ---------------------------------------------------
# ESTILOS (Modo oscuro fintech)
# ---------------------------------------------------

st.markdown("""
<style>

body {
background-color:#0D1B2A;
color:white;
font-family:'DM Sans', sans-serif;
}

h1,h2,h3{
font-family:'Playfair Display', serif;
}

.metric-container{
background:#1B263B;
padding:15px;
border-radius:10px;
}

</style>
""", unsafe_allow_html=True)

st.title("💼 Cartera DVPNXY")

# ---------------------------------------------------
# CONEXIÓN GOOGLE SHEETS
# ---------------------------------------------------

SHEET_ID = "1IlCy67vBvvcj1LrdCtUTJk9EjZADOOqN"
SHEET_NAME = "Base"

url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

df = pd.read_csv(url)

# limpiar columnas
df.columns = df.columns.str.strip()
df.columns = df.columns.str.replace(" ", "_")

# ---------------------------------------------------
# FILTROS INTERCOMPAÑIAS (EXCLUIR)
# ---------------------------------------------------

excluir = [
"TRADIOH LLC",
"N&X TECNOLOGIA Y NEGOCIOS",
"DVP SOFTWARE AND CONSULTING SA DE CV",
"DOUBLE V PARTNERS ECUADOR DVP",
"DOUBLE V PARTNERS GUATEMALA SOCIEDAD ANONIMA"
]

df = df[~df["Cliente"].isin(excluir)]

# ---------------------------------------------------
# FECHAS Y CÁLCULOS
# ---------------------------------------------------

df["Fecha_vencimiento"] = pd.to_datetime(df["Fecha_vencimiento"], errors="coerce")
df["Fecha_factura"] = pd.to_datetime(df["Fecha_factura"], errors="coerce")

hoy = pd.to_datetime(datetime.today())

df["dias_atraso"] = (hoy - df["Fecha_vencimiento"]).dt.days
df["dias_atraso"] = df["dias_atraso"].apply(lambda x: x if x > 0 else 0)

df["Estado"] = df["dias_atraso"].apply(
lambda x:
"🔴 Mora" if x>0 else "🟢 Al día"
)

# ---------------------------------------------------
# HEADER FILTROS
# ---------------------------------------------------

col1,col2 = st.columns(2)

with col1:

    pais = st.multiselect(
        "País",
        df["Pais"].unique(),
        default=df["Pais"].unique()
    )

with col2:

    fechas = st.date_input(
        "Rango de fechas",
        []
    )

df = df[df["Pais"].isin(pais)]

# ---------------------------------------------------
# KPIs
# ---------------------------------------------------

cartera_total = df["Valor_USD"].sum()

vencido = df[df["dias_atraso"]>0]["Valor_USD"].sum()

al_dia = df[df["dias_atraso"]==0]["Valor_USD"].sum()

promedio_dias = df["dias_atraso"].mean()

porcentaje_mora = (vencido / cartera_total)*100 if cartera_total>0 else 0

k1,k2,k3,k4,k5 = st.columns(5)

k1.metric("Cartera Total", f"${cartera_total:,.0f}")

k2.metric("Total Vencido", f"${vencido:,.0f}")

k3.metric("Total al día", f"${al_dia:,.0f}")

k4.metric("Promedio días atraso", f"{promedio_dias:.1f}")

k5.metric("% Mora", f"{porcentaje_mora:.1f}%")

# ---------------------------------------------------
# RESUMEN POR PAIS
# ---------------------------------------------------

st.subheader("Resumen por país")

resumen = df.groupby("Pais").agg(
clientes=("Cliente","nunique"),
total=("Valor_USD","sum"),
vencido=("dias_atraso",lambda x: (x>0).sum())
).reset_index()

st.dataframe(resumen,use_container_width=True)

# ---------------------------------------------------
# TABLA PRINCIPAL CARTERA
# ---------------------------------------------------

st.subheader("Cartera de clientes")

tabla = df[[
"Cliente",
"Pais",
"Moneda",
"Valor_Original",
"Valor_USD",
"Fecha_vencimiento",
"dias_atraso",
"Estado",
"Notas_credito",
"Saldo_neto"
]]

def color_estado(val):
    if val>60:
        return "background-color:red"
    elif val>30:
        return "background-color:orange"
    elif val>0:
        return "background-color:yellow"
    else:
        return "background-color:green"

tabla_style = tabla.style.applymap(color_estado, subset=["dias_atraso"])

st.dataframe(tabla_style,use_container_width=True)

# ---------------------------------------------------
# GRÁFICA 1 PIE CARTERA POR PAIS
# ---------------------------------------------------

st.subheader("Distribución de cartera por país")

fig = px.pie(
df,
values="Valor_USD",
names="Pais",
hole=0.5
)

st.plotly_chart(fig,use_container_width=True)

# ---------------------------------------------------
# GRAFICA 2 VENCIDO VS AL DIA
# ---------------------------------------------------

estado = df.copy()

estado["tipo"] = estado["dias_atraso"].apply(
lambda x: "Vencido" if x>0 else "Al día"
)

graf2 = estado.groupby(["Pais","tipo"])["Valor_USD"].sum().reset_index()

fig2 = px.bar(
graf2,
x="Pais",
y="Valor_USD",
color="tipo",
barmode="group"
)

st.plotly_chart(fig2,use_container_width=True)

# ---------------------------------------------------
# GRAFICA 3 ANTIGÜEDAD CARTERA
# ---------------------------------------------------

bins = [0,30,60,90,9999]

labels = ["1-30","31-60","61-90","+90"]

df["rango"] = pd.cut(df["dias_atraso"],bins=bins,labels=labels)

antig = df.groupby("rango")["Valor_USD"].sum().reset_index()

fig3 = px.bar(
antig,
x="rango",
y="Valor_USD",
color="rango"
)

st.plotly_chart(fig3,use_container_width=True)

# ---------------------------------------------------
# GRAFICA 4 EVOLUCIÓN MENSUAL
# ---------------------------------------------------

df["mes"] = df["Fecha_factura"].dt.to_period("M").astype(str)

evol = df.groupby("mes")["Valor_USD"].sum().reset_index()

fig4 = px.line(
evol,
x="mes",
y="Valor_USD"
)

st.plotly_chart(fig4,use_container_width=True)

# ---------------------------------------------------
# SEMÁFORO CLIENTES
# ---------------------------------------------------

st.subheader("Semáforo de clientes")

def categoria(x):

    if x==0:
        return "🟢 Al día"

    elif x<=30:
        return "🟡 1-30"

    elif x<=60:
        return "🟠 31-60"

    else:
        return "🔴 +60"

df["categoria"]=df["dias_atraso"].apply(categoria)

sem = df.groupby("categoria")["Cliente"].nunique().reset_index()

st.dataframe(sem)
