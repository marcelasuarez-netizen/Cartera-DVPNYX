import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import io

# ---------------- CONFIGURACIÓN ----------------

ID_DRIVE = "1IlCy67vBvvcj1LrdCtUTJk9EjZADOOqN"

st.set_page_config(
    page_title="Cartera DVPNYX",
    layout="wide"
)

# ---------------- ESTILO ----------------

st.markdown("""
<style>
.stApp {background-color:#e3f2fd;}

[data-testid="stMetric"]{
background:white;
padding:10px;
border-radius:10px;
}

h1,h2,h3{color:#0d47a1;}
</style>
""", unsafe_allow_html=True)

# ---------------- CLIENTES INTERNOS ----------------

CLIENTES_EXCLUIR = [
"TRADIOH LLC",
"N&X TECNOLOGIA Y NEGOCIOS",
"NYX DESARROLLADORA DE SOFTWARE Y SOLUCIONES TECNOLOGICAS",
"DOUBLE V PARTNERS GUATEMALA SOCIEDAD ANONIMA",
"DVP SOFTWARE AND CONSULTING SA DE CV",
"DOUBLE V PARTNERS ECUADOR DVP"
]

INTERNOS_CLEAN = [c.strip().upper() for c in CLIENTES_EXCLUIR]

# ---------------- CONEXIÓN GOOGLE SHEETS ----------------

@st.cache_data(ttl=300)
def cargar_datos(id_file):

    url = f"https://docs.google.com/spreadsheets/d/{id_file}/export?format=xlsx"

    try:

        response = requests.get(url)

        if response.status_code != 200:
            st.error("No se pudo acceder al archivo")
            return None

        excel = pd.read_excel(
            io.BytesIO(response.content),
            sheet_name=None,
            engine="openpyxl"
        )

        return excel

    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return None


datos_excel = cargar_datos(ID_DRIVE)

if datos_excel is None:
    st.stop()

# ---------------- CONFIGURACIÓN GLOBAL ----------------

hojas_excluir = [
"Dashboard",
"Hoja 2",
"Hoja 4",
"altabix",
"ALTABIX",
"Instrucciones"
]

hojas_paises = [h for h in datos_excel.keys() if h not in hojas_excluir]

TASAS_REF = {
"COP":4000,
"MXN":18.5,
"GTQ":7.8,
"USD":1
}

hoy = datetime.now()

# ---------------- FUNCIONES ----------------

def limpiar_columnas(df):

    df.columns = [str(c).strip() for c in df.columns]

    if "Total" not in df.columns and "TOTAL" not in df.columns:

        try:
            df.columns = df.iloc[0]
            df = df[1:].reset_index(drop=True)
        except:
            pass

    return df


def encontrar_columna(df, lista):

    for c in lista:
        if c in df.columns:
            return c

    return None


# ---------------- PROCESAMIENTO GLOBAL ----------------

resumen = []
salud = []

for pais in hojas_paises:

    df = datos_excel[pais].copy()

    df = limpiar_columnas(df)

    col_total = encontrar_columna(df,["Total","TOTAL"])
    col_saldo = encontrar_columna(df,["Saldo","SALDO"])
    col_cliente = encontrar_columna(df,["Cliente","NOMBRE","Nombre Receptor"])
    col_moneda = encontrar_columna(df,["Moneda"])

    if col_total is None or col_cliente is None:
        continue

    df["CLI_CLEAN"] = df[col_cliente].astype(str).str.upper().str.strip()

    df = df[~df["CLI_CLEAN"].isin(INTERNOS_CLEAN)]

    tasa = 1

    if col_moneda and not df.empty:

        moneda = str(df[col_moneda].iloc[0]).upper()

        tasa = TASAS_REF.get(moneda,1)

    ventas = pd.to_numeric(df[col_total],errors="coerce").fillna(0).sum()

    saldo = 0

    if col_saldo:
        saldo = pd.to_numeric(df[col_saldo],errors="coerce").fillna(0).sum()

    ventas_usd = ventas/tasa
    saldo_usd = saldo/tasa

    resumen.append({
        "País":pais,
        "Ventas":ventas_usd,
        "Saldo":saldo_usd
    })

    score = (1 - saldo_usd/ventas_usd) if ventas_usd>0 else 0

    salud.append({
        "País":pais,
        "Score":score
    })

df_global = pd.DataFrame(resumen)
df_salud = pd.DataFrame(salud).sort_values("Score",ascending=False)

# ---------------- TITULO ----------------

st.title("📊 Dashboard Cartera DVPNYX")

# ---------------- PODIO ----------------

st.subheader("🏆 Ranking Salud de Cartera")

if not df_salud.empty:

    top3 = df_salud.head(3)

    col1,col2,col3 = st.columns(3)

    for i,row in top3.iterrows():

        if i==0:
            medal="🥇"
        elif i==1:
            medal="🥈"
        else:
            medal="🥉"

        with [col1,col2,col3][i]:

            st.metric(
                f"{medal} {i+1} Lugar",
                row["País"]
            )

# ---------------- GRÁFICAS ----------------

if not df_global.empty:

    col1,col2 = st.columns(2)

    with col1:

        fig1 = px.bar(
            df_global,
            x="País",
            y="Ventas",
            title="Ventas Totales USD"
        )

        st.plotly_chart(fig1,use_container_width=True)

    with col2:

        fig2 = px.bar(
            df_global,
            x="País",
            y="Saldo",
            title="Saldo por Cobrar USD",
            color_discrete_sequence=["#e53935"]
        )

        st.plotly_chart(fig2,use_container_width=True)

# ---------------- FILTROS ----------------

st.sidebar.header("Filtros")

pais_sel = st.sidebar.selectbox(
"Seleccionar País",
hojas_paises
)

df = datos_excel[pais_sel].copy()

df = limpiar_columnas(df)

col_cliente = encontrar_columna(df,["Cliente","NOMBRE"])
col_saldo = encontrar_columna(df,["Saldo","SALDO"])
col_total = encontrar_columna(df,["Total","TOTAL"])

if col_cliente:

    df["CLI_CLEAN"] = df[col_cliente].astype(str).str.upper().str.strip()

    df = df[~df["CLI_CLEAN"].isin(INTERNOS_CLEAN)]

# ---------------- MÉTRICAS ----------------

st.subheader(f"Gestión Detallada {pais_sel}")

if col_saldo:

    df[col_saldo] = pd.to_numeric(df[col_saldo],errors="coerce").fillna(0)

    total_saldo = df[col_saldo].sum()

    clientes = df[col_cliente].nunique()

    promedio = df[col_saldo].mean()

    c1,c2,c3 = st.columns(3)

    c1.metric("Saldo Total",f"$ {total_saldo:,.0f}")
    c2.metric("Clientes",clientes)
    c3.metric("Promedio",f"$ {promedio:,.0f}")

# ---------------- TABLA ----------------

st.subheader("Clientes con mayor saldo")

if col_cliente and col_saldo:

    df = df.sort_values(col_saldo,ascending=False)

    st.dataframe(
        df[[col_cliente,col_saldo]],
        use_container_width=True
    )

    fig = px.bar(
        df.head(10),
        x=col_cliente,
        y=col_saldo,
        title="Top 10 Clientes con mayor saldo"
    )

    st.plotly_chart(fig,use_container_width=True)