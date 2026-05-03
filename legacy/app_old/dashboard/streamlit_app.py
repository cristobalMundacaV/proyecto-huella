import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


from sklearn.ensemble import IsolationForest
import numpy as np
import streamlit as st
import plotly.express as px


from legacy.app_old.main import run_pipeline

st.set_page_config(page_title="Huella de Carbono", layout="wide")

# Carga de datos
df, metricas = run_pipeline(
    "data/raw/datos_emisiones.csv",
    "data/external/factores_emision.csv",
)

# Header
st.title("Huella")
st.caption("Plataforma de inteligencia para el análisis y optimización de la huella de carbono empresarial")

st.divider()
# Filtros
st.sidebar.header("Filtros")
empresas = ["Todas"] + sorted(df["empresa"].unique().tolist())
actividades = ["Todas"] + sorted(df["actividad"].unique().tolist())
empresa_seleccionada = st.sidebar.selectbox("Selecciona una empresa", empresas)
actividad_seleccionada = st.sidebar.selectbox("Selecciona una actividad", actividades)

df_filtrado = df.copy()

if empresa_seleccionada != "Todas":
    df_filtrado = df_filtrado[df_filtrado["empresa"] == empresa_seleccionada]
if actividad_seleccionada != "Todas":
    df_filtrado = df_filtrado[df_filtrado["actividad"] == actividad_seleccionada]

# Metricas bajo filtros

total_emisiones_filtrado = df_filtrado["emisiones"].sum()
emisiones_por_empresa_filtrado = (
    df_filtrado.groupby("empresa")["emisiones"]
    .sum()
    .sort_values(ascending=False)
)
emisiones_por_actividad_filtrado = (
    df_filtrado.groupby("actividad")["emisiones"]
    .sum()
    .sort_values(ascending=False)
)

actividad_critica = emisiones_por_actividad_filtrado.idxmax() if not emisiones_por_actividad_filtrado.empty else "Sin datos"
empresa_critica = emisiones_por_empresa_filtrado.idxmax() if not emisiones_por_empresa_filtrado.empty else "Sin datos"

# KPIS

col1, col2, col3 = st.columns(3)

col1.metric("Total Emisiones (kg CO2e)", round(total_emisiones_filtrado, 2))
col2.metric("Actividad Crítica", actividad_critica)
col3.metric("Empresa Crítica", empresa_critica)

st.divider()

# Insights
st.subheader("Insights")

if total_emisiones_filtrado > 0 and not emisiones_por_actividad_filtrado.empty:
    actividad_top = emisiones_por_actividad_filtrado.idxmax()
    valor_top = emisiones_por_actividad_filtrado.max()
    porcentaje = (valor_top / total_emisiones_filtrado * 100)

    st.success(
        f"La actividad '{actividad_top}' es la más crítica, representando el {porcentaje:.2f}% de las emisiones totales."
    )
else:
    st.info("No hay datos suficientes para generar insights.")

st.divider()

st.subheader("Simulación de Reducción de Emisiones")

st.divider()

st.subheader("Detección de Anomalías")

# Preparar datos
df_ml = df.copy()

# Crear feature relevante
df_ml["intensidad"] = df_ml["emisiones"] / df_ml["cantidad"]

# Modelo
model = IsolationForest(contamination=0.25, random_state=42)
df_ml["anomaly"] = model.fit_predict(df_ml[["intensidad"]])

df_ml["anomaly"] = df_ml["anomaly"].map({1: "Normal", -1: "Anómalo"})

st.dataframe(df_ml[["empresa", "actividad", "intensidad", "anomaly"]])

anomalias = df_ml[df_ml["anomaly"] == "Anómalo"]

if not anomalias.empty:
    st.warning(
        f"Se detectaron anomalías en: {', '.join(anomalias['empresa'] + ' - ' + anomalias['actividad'])}"
    )
else:
    st.success("No se detectaron anomalías relevantes")

st.divider()
st.subheader("🔮 Proyección de Emisiones")

crecimiento = st.slider(
    "Crecimiento de actividad (%)",
    min_value=-50,
    max_value=100,
    value=10
)

df_proy = df.copy()

df_proy["cantidad"] = df_proy["cantidad"] * (1 + crecimiento / 100)
df_proy["emisiones"] = df_proy["cantidad"] * df_proy["factor_emision"]

emisiones_futuras = df_proy["emisiones"].sum()

col_pred1, col_pred2 = st.columns(2)

col_pred1.metric("Emisiones actuales", round(df["emisiones"].sum(), 2))
col_pred2.metric("Emisiones proyectadas", round(emisiones_futuras, 2))

delta = emisiones_futuras - df["emisiones"].sum()

if delta > 0:
    st.warning(f"Las emisiones aumentarían en {round(delta,2)} kg CO2e")
else:
    st.success(f"Las emisiones disminuirían en {round(abs(delta),2)} kg CO2e")

actividad_simulada = st.selectbox(
    "Selecciona una actividad para simular la reducción de emisiones",
    df["actividad"].unique()
)

porcentaje_reduccion = st.slider(
    "Porcentaje de reducción",
    min_value=0,
    max_value=100,
    value=10
)

df_simulado = df.copy()

mask = df_simulado["actividad"] == actividad_simulada

df_simulado.loc[mask,"cantidad"] *= (1 - porcentaje_reduccion / 100)

df_simulado["emisiones"] = df_simulado["cantidad"] * df_simulado["factor_emision"]

nuevo_total_emisiones = df_simulado["emisiones"].sum()

col_sim1, col_sim2 = st.columns(2)

col_sim1.metric("Emisiones Actuales (kg CO2e)", round(total_emisiones_filtrado, 2))

col_sim2.metric("Emisiones Simuladas (kg CO2e)", round(nuevo_total_emisiones, 2))

diferencia = total_emisiones_filtrado - nuevo_total_emisiones

st.success(f"Podrias reducir {round(diferencia, 2)} kg CO2e optimizando {actividad_simulada} en un {porcentaje_reduccion}%")


# Gráficos
col_graf1, col_graf2 = st.columns(2)


with col_graf1:
    st.subheader("Emisiones por Empresa")
    
    fig_empresa = px.bar(
        emisiones_por_empresa_filtrado,
        x=emisiones_por_empresa_filtrado.index,
        y=emisiones_por_empresa_filtrado.values,
        labels={"x":"Empresa", "y":"Emisiones (kg CO2e)"},
        text_auto=True
    )

    fig_empresa.update_layout(
        xaxis_title="Empresa",
        yaxis_title="Emisiones (kg CO2e)",
        showlegend=False
    )

    st.plotly_chart(fig_empresa, use_container_width=True)

with col_graf2:
    st.subheader("Emisiones por Actividad")

    fig_actividad = px.bar(
        emisiones_por_actividad_filtrado,
        x=emisiones_por_actividad_filtrado.index,
        y=emisiones_por_actividad_filtrado.values,
        labels={"x":"Actividad", "y":"Emisiones (kg CO2e)"},
        text_auto=True
    )
    fig_actividad.update_layout(
        xaxis_title="Actividad",
        yaxis_title="Emisiones (kg CO2e)",
        showlegend=False
    )
    st.plotly_chart(fig_actividad, use_container_width=True)

st.divider()

# Ranking

st.subheader("Ranking de Emisiones por Empresa")
st.dataframe(emisiones_por_empresa_filtrado.reset_index().rename(columns={"empresa": "Empresa", "emisiones": "Emisiones (kg CO2e)"}))

st.divider()

# Datos procesados

st.subheader("Datos Procesados")
st.dataframe(df_filtrado,use_container_width=True)
