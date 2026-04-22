import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Cartera DVPNYX", layout="wide")

# -----------------------------
# ESTILO
# -----------------------------
st.markdown("""
<style>

body{
background-color:#0D1B2A;
color:white;
}

.small-font{
font-size:13px;
}

</style>
""", unsafe_allow_html=True)

st.title("📊 Cartera DVPNYX")

# -----------------------------
# CARGA DATOS
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
df["Estado"] = df["Estado"].astype(str).str.lower()

# -----------------------------
# NORMALIZAR ESTADO
# -----------------------------

def clasificar_estado(x):

    x = str(x).lower()

    if "anul" in x:
        return "Anulada"

    if "nota" in x or "nc" in x:
        return "Nota Crédito"

    if "mora" in x:
        return "En Mora"

    if "dia" in x:
        return "Al día"

    return "Otro"

df["Estado_clasificado"] = df["Estado"].apply(clasificar_estado)

df = df[df["Estado_clasificado"].isin([
"Anulada",
"Nota Crédito",
"En Mora",
"Al día"
])]

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
options=sorted(df["Año"].dropna().unique())
)

pais = st.sidebar.multiselect(
"País",
options=df["Pais"].unique()
)

mes = st.sidebar.multiselect(
"Mes",
options=sorted(df["Mes"].dropna().unique())
)

cliente = st.sidebar.multiselect(
"Cliente",
options=df["Cliente"].unique()
)

df_f = df.copy()

if anio:
    df_f = df_f[df_f["Año"].isin(anio)]

if pais:
    df_f = df_f[df_f["Pais"].isin(pais)]

if mes:
    df_f = df_f[df_f["Mes"].isin(mes)]

if cliente:
    df_f = df_f[df_f["Cliente"].isin(cliente)]

# -----------------------------
# KPIs
# -----------------------------

total_cartera = df_f["SALDO"].sum()

vencido = df_f[df_f["Estado_clasificado"]=="En Mora"]["SALDO"].sum()

aldia = df_f[df_f["Estado_clasificado"]=="Al día"]["SALDO"].sum()

mora = (vencido / total_cartera * 100) if total_cartera > 0 else 0

col1,col2,col3,col4 = st.columns(4)

col1.metric("Total Cartera", f"${total_cartera:,.0f}")
col2.metric("Vencido", f"${vencido:,.0f}")
col3.metric("Al día", f"${aldia:,.0f}")
col4.metric("% Mora", f"{mora:.2f}%")

# -----------------------------
# RESUMEN POR PAIS (FIJO)
# -----------------------------

st.subheader("Resumen por País")

resumen = df.groupby("Pais").agg(
Clientes=("Cliente","nunique"),
Total_Cartera=("SALDO","sum"),
Vencido=("SALDO",lambda x: x[df.loc[x.index,"Estado_clasificado"]=="En Mora"].sum())
).reset_index()

resumen["% Mora"] = (resumen["Vencido"]/resumen["Total_Cartera"])*100

resumen["Total_Cartera"] = resumen["Total_Cartera"].map("${:,.0f}".format)
resumen["Vencido"] = resumen["Vencido"].map("${:,.0f}".format)
resumen["% Mora"] = resumen["% Mora"].map("{:.2f}%".format)

st.markdown('<div class="small-font">', unsafe_allow_html=True)
st.dataframe(resumen,use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------
# GRAFICA DISTRIBUCION
# -----------------------------

st.subheader("Distribución de cartera por país")

dist = df_f.groupby(["Pais","Estado_clasificado"])["SALDO"].sum().reset_index()

fig = px.bar(
dist,
x="Pais",
y="SALDO",
color="Estado_clasificado",
text_auto=True,
barmode="stack"
)

fig.update_layout(
yaxis_title="USD",
xaxis_title="País"
)

st.plotly_chart(fig,use_container_width=True)

# -----------------------------
# ANTIGÜEDAD CARTERA
# -----------------------------

st.subheader("Antigüedad de cartera")

def bucket(d):

    if pd.isna(d):
        return "Al día"

    if d<=30:
        return "1-30"

    if d<=60:
        return "31-60"

    if d<=90:
        return "61-90"

    return "+90"

df_f["Rango"]=df_f["Dias"].apply(bucket)

fig2 = px.bar(
df_f,
x="Rango",
y="SALDO",
color="Rango"
)

st.plotly_chart(fig2,use_container_width=True)

# -----------------------------
# TABLA PRINCIPAL
# -----------------------------

st.subheader("Detalle de cartera")

tabla = df_f[[
"Cliente",
"Pais",
"Moneda",
"SALDO",
"Fecha de vencimiento",
"Dias",
"Estado_clasificado"
]]

tabla["SALDO"] = tabla["SALDO"].map("${:,.0f}".format)

st.dataframe(tabla,use_container_width=True)