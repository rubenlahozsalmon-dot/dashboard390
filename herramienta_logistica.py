import streamlit as st
import pandas as pd
import plotly.express as px

# 1. LOGICA DE NEGOCIO Y PROCESAMIENTO
def procesar_datos(df_raw):
    """
    Limpia y transforma los datos brutos de logística.
    """
    # Mapeo de columnas basado en tu estructura original
    column_mapping = {
        0: 'Fecha',
        7: 'Repartidor',
        9: 'Intentos',
        10: 'Motivo_Incidencia',
        11: 'Detalle_Estatus',
        14: 'CP'
    }
    
    df = df_raw.copy()
    df.columns = range(df.shape[1]) # Normalizar índices de columnas
    df = df.rename(columns=column_mapping)
    
    # Definir éxito (Efectividad)
    df['Exito'] = df['Detalle_Estatus'].apply(lambda x: 1 if str(x).strip().lower() == 'efectividad' else 0)
    
    # Agrupación por CP y Repartidor
    resumen = df.groupby(['CP', 'Repartidor']).agg(
        Total_Pedidos=('Exito', 'count'),
        Entregas_Exitosas=('Exito', 'sum')
    ).reset_index()
    
    # Cálculo de KPIs
    resumen['Incidencias'] = resumen['Total_Pedidos'] - resumen['Entregas_Exitosas']
    resumen['Efectividad_%'] = (resumen['Entregas_Exitosas'] / resumen['Total_Pedidos']) * 100
    
    return resumen, df

# 2. CONFIGURACIÓN DE LA INTERFAZ
st.set_page_config(page_title="Auditoría Logística Pro", layout="wide")

st.title("📦 Sistema de Auditoría Last Mile")
st.markdown("Analizador de efectividad con SLA objetivo del *90%*.")

# Sidebar: Carga de archivos y filtros
st.sidebar.header("Configuración")
archivo = st.sidebar.file_uploader("Cargar Reporte (CSV o Excel)", type=['csv', 'xlsx', 'xls'])

TARGET_SLA = 90.0

if archivo:
    # Cargar datos según extensión
    if archivo.name.endswith('.csv'):
        df_input = pd.read_csv(archivo)
    else:
        df_input = pd.read_excel(archivo)

    # Procesar
    resumen_kpi, df_completo = procesar_datos(df_input)

    # Filtro de Repartidor
    lista_repartidores = ["Todos"] + sorted(resumen_kpi['Repartidor'].unique().tolist())
    rep_sel = st.sidebar.selectbox("Seleccionar Repartidor", lista_repartidores)

    if rep_sel != "Todos":
        resumen_kpi = resumen_kpi[resumen_kpi['Repartidor'] == rep_sel]
        df_completo = df_completo[df_completo['Repartidor'] == rep_sel]

    # --- MÉTRICAS PRINCIPALES ---
    m1, m2, m3, m4 = st.columns(4)
    avg_eff = resumen_kpi['Efectividad_%'].mean()
    
    m1.metric("Efectividad Media", f"{avg_eff:.1f}%", f"{avg_eff - TARGET_SLA:.1f}%")
    m2.metric("Total Pedidos", resumen_kpi['Total_Pedidos'].sum())
    m3.metric("Total Incidencias", int(resumen_kpi['Incidencias'].sum()))
    m4.metric("Zonas Auditadas", resumen_kpi['CP'].nunique())

    st.divider()

    # --- ANÁLISIS VISUAL ---
    col_izq, col_der = st.columns(2)

    with col_izq:
        st.subheader("📊 Análisis de Causa Raíz")
        fallos = df_completo[df_completo['Exito'] == 0]
        if not fallos.empty:
            fig_causas = px.bar(
                fallos['Motivo_Incidencia'].value_counts().reset_index(),
                x='count', y='Motivo_Incidencia', orientation='h',
                labels={'count': 'Casos', 'Motivo_Incidencia': 'Motivo'},
                color='count', color_continuous_scale='Reds'
            )
            st.plotly_chart(fig_causas, use_container_width=True)
        else:
            st.success("Sin incidencias registradas.")

    with col_der:
        st.subheader("📈 Distribución de Rendimiento")
        fig_hist = px.histogram(
            resumen_kpi, x="Efectividad_%", 
            nbins=15, title="Frecuencia de Efectividad"
        )
        fig_hist.add_vline(x=TARGET_SLA, line_dash="dash", line_color="red", annotation_text="Meta 90%")
        st.plotly_chart(fig_hist, use_container_width=True)

    # --- TABLA DE DETALLE ---
    st.subheader("📋 Detalle de Auditoría por Zona")
    
    # Formato condicional: Rojo si es menor al 90%
    def style_sla(v):
        color = 'background-color: #ffcccc' if v < TARGET_SLA else 'background-color: #ccffcc'
        return color

    st.dataframe(
        resumen_kpi.style.applymap(style_sla, subset=['Efectividad_%']),
        use_container_width=True
    )

    # Botón de Descarga
    csv = resumen_kpi.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Descargar Auditoría en CSV",
        data=csv,
        file_name=f"auditoria_{rep_sel}.csv",
        mime='text/csv'
    )

else:
  
