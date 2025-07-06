import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
import numpy as np
from datetime import datetime
import time

# Configuración de la página
st.set_page_config(
    page_title="Fintech Analytics Dashboard - Cassandra",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título principal
st.title("🚀 Fintech Analytics Dashboard")
st.markdown("### Análisis de Onboarding y A/B Testing - Datos en Tiempo Real")

# Configuración de Cassandra en sidebar
st.sidebar.header("⚙️ Configuración de Base de Datos")

# Configuración de conexión
cassandra_host = st.sidebar.text_input("Host de Cassandra", value="localhost")
cassandra_port = st.sidebar.number_input("Puerto", value=9042, min_value=1, max_value=65535)
keyspace_name = st.sidebar.text_input("Keyspace", value="fintech_analytics")
table_name = st.sidebar.text_input("Tabla", value="user_onboarding_metrics_clean")

# Botón para probar conexión
if st.sidebar.button("🔍 Probar Conexión"):
    try:
        cluster = Cluster([cassandra_host], port=cassandra_port)
        session = cluster.connect()
        session.execute(f"USE {keyspace_name}")
        
        # Verificar que la tabla existe con una consulta simple
        rows = session.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = rows.one()[0]
        
        # Verificar que hay datos
        if count > 0:
            st.sidebar.success(f"✅ Conexión exitosa! {count:,} registros encontrados")
        else:
            st.sidebar.warning(f"⚠️ Conexión exitosa pero no hay datos en la tabla")
        
        session.shutdown()
        cluster.shutdown()
        
    except Exception as e:
        st.sidebar.error(f"❌ Error de conexión: {str(e)}")

# Función para cargar datos desde Cassandra con cache inteligente
@st.cache_data(ttl=300)  # Cache por 5 minutos
def load_data_from_cassandra(host, port, keyspace, table):
    """
    Carga datos desde Cassandra con manejo de errores mejorado
    """
    try:
        # Mostrar progreso
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("Conectando a Cassandra...")
        progress_bar.progress(25)
        
        # Conectar a Cassandra
        cluster = Cluster([host], port=port)
        session = cluster.connect()
        
        status_text.text("Ejecutando consulta...")
        progress_bar.progress(50)
        
        # Usar keyspace
        session.execute(f"USE {keyspace}")
        
        # Cargar datos con consulta optimizada
        query = f"""
        SELECT user_id, segment, ab_group, "drop", activacion, setup, habito_calc 
        FROM {table}
        """
        
        rows = session.execute(query)
        
        status_text.text("Procesando datos...")
        progress_bar.progress(75)
        
        # Convertir a DataFrame
        data = []
        for row in rows:
            data.append({
                'user_id': row.user_id,
                'segment': row.segment,
                'ab_group': row.ab_group,
                'drop': row.drop,
                'activacion': row.activacion,
                'setup': row.setup,
                'habito_calc': row.habito_calc
            })
        
        df = pd.DataFrame(data)
        
        status_text.text("Completado!")
        progress_bar.progress(100)
        time.sleep(0.5)
        progress_bar.empty()
        status_text.empty()
        
        # Cerrar conexión
        session.shutdown()
        cluster.shutdown()
        
        return df
        
    except Exception as e:
        st.error(f"❌ Error al cargar datos desde Cassandra: {str(e)}")
        return None

# Función para obtener estadísticas de la base de datos
def get_database_stats(host, port, keyspace, table):
    """
    Obtiene estadísticas de la base de datos usando pandas
    """
    try:
        cluster = Cluster([host], port=port)
        session = cluster.connect()
        session.execute(f"USE {keyspace}")
        
        # Contar registros
        count_query = f"SELECT COUNT(*) FROM {table}"
        total_rows = session.execute(count_query).one()[0]
        
        # Cerrar conexión
        session.shutdown()
        cluster.shutdown()
        
        return {
            'total_rows': total_rows
        }
        
    except Exception as e:
        st.error(f"Error al obtener estadísticas: {str(e)}")
        return None

# Cargar datos
st.header("📊 Carga de Datos")

with st.spinner("Cargando datos desde Cassandra..."):
    df = load_data_from_cassandra(cassandra_host, cassandra_port, keyspace_name, table_name)
    
    if df is not None:
        # Mostrar estadísticas de la base de datos
        stats = get_database_stats(cassandra_host, cassandra_port, keyspace_name, table_name)
        if stats:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Registros", f"{stats['total_rows']:,}")
            with col2:
                st.metric("Última Actualización", datetime.now().strftime("%H:%M:%S"))
            with col3:
                st.metric("Fuente", "Cassandra")
        
        # Calcular estadísticas adicionales usando pandas
        if not df.empty:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Usuarios Individuals", f"{len(df[df['segment'] == 1]):,}")
            with col2:
                st.metric("Usuarios Sellers", f"{len(df[df['segment'] == 2]):,}")
            with col3:
                st.metric("Grupo Control", f"{len(df[df['ab_group'] == 'control']):,}")
            with col4:
                st.metric("Grupo Treatment", f"{len(df[df['ab_group'] == 'treatment']):,}")

if df is None or df.empty:
    st.error("❌ No se pudieron cargar los datos desde Cassandra. Verifica la conexión y ejecuta el ETL primero.")
    st.stop()

# Mapear segmentos a nombres
segment_mapping = {1: 'Individuals', 2: 'Sellers'}
df['segment_nombre'] = df['segment'].map(segment_mapping)

# Mostrar información básica
st.sidebar.header("📊 Información General")
st.sidebar.metric("Total Usuarios", f"{len(df):,}")
st.sidebar.metric("Usuarios Únicos", f"{df['user_id'].nunique():,}")

# Selector de vista en sidebar
st.sidebar.header("🎯 Navegación")
view_option = st.sidebar.selectbox(
    "Selecciona la vista:",
    ["📈 Dashboard Completo", "🔄 Funnel", "👥 Segmentos", "🔬 A/B Testing", "📊 Datos Raw"]
)

# 1. ANÁLISIS DEL FUNNEL DE ONBOARDING
if view_option in ["📈 Dashboard Completo", "🔄 Funnel"]:
    st.header("🔄 Funnel de Onboarding")

    # Calcular métricas del funnel
    total_users = len(df)
    activated_users = df['activacion'].sum()
    setup_users = df['setup'].sum()
    habit_users = df['habito_calc'].sum()

    # Crear gráfico de funnel
    fig_funnel = go.Figure(go.Funnel(
        y = ["Registro", "Activación", "Setup", "Hábito"],
        x = [total_users, activated_users, setup_users, habit_users],
        textinfo = "value+percent initial"
    ))

    fig_funnel.update_layout(
        title="Funnel de Onboarding Completo",
        height=500,
        showlegend=False
    )

    st.plotly_chart(fig_funnel, use_container_width=True)

    # Métricas detalladas
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Registro", f"{total_users:,}", "100%")
        
    with col2:
        activation_rate = (activated_users / total_users) * 100
        st.metric("Activación", f"{activated_users:,}", f"{activation_rate:.1f}%")
        
    with col3:
        setup_rate = (setup_users / total_users) * 100
        st.metric("Setup", f"{setup_users:,}", f"{setup_rate:.1f}%")
        
    with col4:
        habit_rate = (habit_users / total_users) * 100
        st.metric("Hábito", f"{habit_users:,}", f"{habit_rate:.1f}%")

# 2. ANÁLISIS POR SEGMENTO
if view_option in ["📈 Dashboard Completo", "👥 Segmentos"]:
    st.header("👥 Análisis por Segmento")

    # Métricas por segmento usando nombres
    segment_metrics = df.groupby('segment_nombre').agg({
        'user_id': 'count',
        'activacion': 'sum',
        'setup': 'sum',
        'habito_calc': 'sum',
        'drop': 'sum'
    }).reset_index()

    segment_metrics.columns = ['Segmento', 'Total_Usuarios', 'Activados', 'Setup', 'Hábito', 'Drop']

    # Calcular tasas
    segment_metrics['Tasa_Activacion'] = (segment_metrics['Activados'] / segment_metrics['Total_Usuarios']) * 100
    segment_metrics['Tasa_Setup'] = (segment_metrics['Setup'] / segment_metrics['Total_Usuarios']) * 100
    segment_metrics['Tasa_Habito'] = (segment_metrics['Hábito'] / segment_metrics['Total_Usuarios']) * 100
    segment_metrics['Tasa_Drop'] = (segment_metrics['Drop'] / segment_metrics['Total_Usuarios']) * 100

    # Mostrar tabla
    st.subheader("Métricas por Segmento")
    st.dataframe(segment_metrics, use_container_width=True)

    # Gráfico de segmentos
    fig_segment = px.bar(
        segment_metrics,
        x='Segmento',
        y=['Tasa_Activacion', 'Tasa_Setup', 'Tasa_Habito'],
        title="Tasas por Segmento",
        barmode='group'
    )

    fig_segment.update_layout(height=500)
    st.plotly_chart(fig_segment, use_container_width=True)

# 3. ANÁLISIS A/B TESTING
if view_option in ["📈 Dashboard Completo", "🔬 A/B Testing"]:
    st.header("🔬 Análisis A/B Testing")

    # Métricas por grupo
    ab_metrics = df.groupby('ab_group').agg({
        'user_id': 'count',
        'activacion': 'sum',
        'setup': 'sum',
        'habito_calc': 'sum',
        'drop': 'sum'
    }).reset_index()

    ab_metrics.columns = ['Grupo', 'Total_Usuarios', 'Activados', 'Setup', 'Hábito', 'Drop']

    # Calcular tasas
    ab_metrics['Tasa_Activacion'] = (ab_metrics['Activados'] / ab_metrics['Total_Usuarios']) * 100
    ab_metrics['Tasa_Setup'] = (ab_metrics['Setup'] / ab_metrics['Total_Usuarios']) * 100
    ab_metrics['Tasa_Habito'] = (ab_metrics['Hábito'] / ab_metrics['Total_Usuarios']) * 100
    ab_metrics['Tasa_Drop'] = (ab_metrics['Drop'] / ab_metrics['Total_Usuarios']) * 100

    # Mostrar tabla de métricas
    st.subheader("Métricas por Grupo")
    st.dataframe(ab_metrics, use_container_width=True)

    # Gráfico comparativo
    fig_ab = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Tasa de Activación', 'Tasa de Setup', 'Tasa de Hábito', 'Tasa de Drop'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )

    # Activación
    fig_ab.add_trace(
        go.Bar(x=ab_metrics['Grupo'], y=ab_metrics['Tasa_Activacion'], name='Activación'),
        row=1, col=1
    )

    # Setup
    fig_ab.add_trace(
        go.Bar(x=ab_metrics['Grupo'], y=ab_metrics['Tasa_Setup'], name='Setup'),
        row=1, col=2
    )

    # Hábito
    fig_ab.add_trace(
        go.Bar(x=ab_metrics['Grupo'], y=ab_metrics['Tasa_Habito'], name='Hábito'),
        row=2, col=1
    )

    # Drop
    fig_ab.add_trace(
        go.Bar(x=ab_metrics['Grupo'], y=ab_metrics['Tasa_Drop'], name='Drop'),
        row=2, col=2
    )

    fig_ab.update_layout(height=600, showlegend=False)
    st.plotly_chart(fig_ab, use_container_width=True)

    # Análisis detallado de diferencias
    if len(ab_metrics) == 2:
        st.subheader("🔍 Análisis de Diferencias")
        
        control = ab_metrics[ab_metrics['Grupo'] == 'control'].iloc[0]
        treatment = ab_metrics[ab_metrics['Grupo'] == 'treatment'].iloc[0]
        
        activation_diff = treatment['Tasa_Activacion'] - control['Tasa_Activacion']
        setup_diff = treatment['Tasa_Setup'] - control['Tasa_Setup']
        habit_diff = treatment['Tasa_Habito'] - control['Tasa_Habito']
        drop_diff = treatment['Tasa_Drop'] - control['Tasa_Drop']
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Activación (Tratamiento - Control)", f"{activation_diff:+.2f}%")
            
        with col2:
            st.metric("Setup (Tratamiento - Control)", f"{setup_diff:+.2f}%")
            
        with col3:
            st.metric("Hábito (Tratamiento - Control)", f"{habit_diff:+.2f}%")
            
        with col4:
            st.metric("Drop (Tratamiento - Control)", f"{drop_diff:+.2f}%")

# 4. ANÁLISIS POR SEGMENTO Y A/B TESTING
if view_option in ["📈 Dashboard Completo", "👥 Segmentos", "🔬 A/B Testing"]:
    st.header("👥 Análisis por Segmento y A/B Testing")

    # Métricas por segmento y grupo A/B
    segment_ab_metrics = df.groupby(['segment_nombre', 'ab_group']).agg({
        'user_id': 'count',
        'activacion': 'sum',
        'setup': 'sum',
        'habito_calc': 'sum',
        'drop': 'sum'
    }).reset_index()

    segment_ab_metrics.columns = ['Segmento', 'Grupo', 'Total_Usuarios', 'Activados', 'Setup', 'Hábito', 'Drop']

    # Calcular tasas
    segment_ab_metrics['Tasa_Activacion'] = (segment_ab_metrics['Activados'] / segment_ab_metrics['Total_Usuarios']) * 100
    segment_ab_metrics['Tasa_Setup'] = (segment_ab_metrics['Setup'] / segment_ab_metrics['Total_Usuarios']) * 100
    segment_ab_metrics['Tasa_Habito'] = (segment_ab_metrics['Hábito'] / segment_ab_metrics['Total_Usuarios']) * 100
    segment_ab_metrics['Tasa_Drop'] = (segment_ab_metrics['Drop'] / segment_ab_metrics['Total_Usuarios']) * 100

    # Mostrar tabla
    st.subheader("Métricas por Segmento y Grupo A/B")
    st.dataframe(segment_ab_metrics, use_container_width=True)

    # Gráfico comparativo por segmento
    fig_segment_ab = px.bar(
        segment_ab_metrics,
        x='Segmento',
        y='Tasa_Habito',
        color='Grupo',
        title="Tasa de Hábito por Segmento y Grupo A/B",
        barmode='group'
    )

    fig_segment_ab.update_layout(height=500)
    st.plotly_chart(fig_segment_ab, use_container_width=True)

# 5. ANÁLISIS DETALLADO DEL HÁBITO
if view_option in ["📈 Dashboard Completo", "🔬 A/B Testing"]:
    st.header("📈 Análisis Detallado del Hábito")

    # Distribución del hábito
    habit_distribution = df['habito_calc'].value_counts()
    habit_distribution_pct = df['habito_calc'].value_counts(normalize=True) * 100

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Distribución del Hábito")
        fig_habit_dist = px.pie(
            values=habit_distribution.values,
            names=['Sin Hábito', 'Con Hábito'],
            title="Distribución de Usuarios por Hábito"
        )
        st.plotly_chart(fig_habit_dist, use_container_width=True)

    with col2:
        st.subheader("Estadísticas del Hábito")
        habit_users = df['habito_calc'].sum()
        total_users = len(df)
        habit_rate = (habit_users / total_users) * 100
        
        st.metric("Usuarios con Hábito", f"{habit_users:,}", f"{habit_rate:.1f}%")
        st.metric("Usuarios sin Hábito", f"{total_users - habit_users:,}", f"{100-habit_rate:.1f}%")
        
        # Hábito por grupo A/B
        habit_by_group = df.groupby('ab_group')['habito_calc'].agg(['sum', 'count']).reset_index()
        habit_by_group['rate'] = (habit_by_group['sum'] / habit_by_group['count']) * 100
        
        st.write("**Tasa de Hábito por Grupo A/B:**")
        for _, row in habit_by_group.iterrows():
            st.write(f"- {row['ab_group']}: {row['rate']:.1f}%")

# 6. DATOS RAW
if view_option == "📊 Datos Raw":
    st.header("📋 Datos Raw")

    # Filtros
    col1, col2, col3 = st.columns(3)

    with col1:
        selected_group = st.selectbox("Filtrar por Grupo A/B", ['Todos'] + list(df['ab_group'].unique()))

    with col2:
        selected_segment = st.selectbox("Filtrar por Segmento", ['Todos'] + list(df['segment_nombre'].unique()))

    with col3:
        selected_metric = st.selectbox("Filtrar por Métrica", ['Todos', 'Con Activación', 'Con Setup', 'Con Hábito', 'Sin Drop'])

    # Aplicar filtros
    filtered_df = df.copy()

    if selected_group != 'Todos':
        filtered_df = filtered_df[filtered_df['ab_group'] == selected_group]

    if selected_segment != 'Todos':
        filtered_df = filtered_df[filtered_df['segment_nombre'] == selected_segment]

    if selected_metric == 'Con Activación':
        filtered_df = filtered_df[filtered_df['activacion'] == 1]
    elif selected_metric == 'Con Setup':
        filtered_df = filtered_df[filtered_df['setup'] == 1]
    elif selected_metric == 'Con Hábito':
        filtered_df = filtered_df[filtered_df['habito_calc'] == 1]
    elif selected_metric == 'Sin Drop':
        filtered_df = filtered_df[filtered_df['drop'] == 0]

    # Mostrar estadísticas de filtros
    st.info(f"📊 Mostrando {len(filtered_df):,} de {len(df):,} registros")

    # Mostrar solo columnas relevantes en datos raw
    display_columns = ['user_id', 'segment_nombre', 'ab_group', 'drop', 'activacion', 'setup', 'habito_calc']
    st.dataframe(filtered_df[display_columns], use_container_width=True)

    # Botón para descargar datos filtrados
    if st.button("📥 Descargar Datos Filtrados"):
        csv = filtered_df[display_columns].to_csv(index=False)
        st.download_button(
            label="💾 Descargar CSV",
            data=csv,
            file_name=f"fintech_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

# Footer
st.markdown("---")
st.markdown("*Dashboard conectado a Cassandra - Fintech Analytics*")
st.markdown(f"*Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*") 