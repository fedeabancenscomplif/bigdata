# 🚀 Fintech Analytics - ETL Pipeline & Dashboard

## 📋 Descripción del Proyecto

Este proyecto implementa un pipeline ETL completo para analizar el onboarding de usuarios en una plataforma fintech, incluyendo un experimento de A/B testing para evaluar la efectividad de diferentes estrategias de activación de usuarios. **El dashboard consume datos directamente desde Cassandra en tiempo real.**

## 🎯 Objetivo

Analizar el comportamiento de los usuarios durante el proceso de onboarding para identificar puntos de fricción y optimizar la experiencia del usuario, reduciendo la tasa de abandono y aumentando la activación y retención.

## 🏗️ Arquitectura del Sistema

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Datasets CSV  │    │   Apache Spark  │    │  Apache Cassandra│
│                 │    │   (PySpark)     │    │                 │
│ • lk_onboarding │───▶│   ETL Pipeline  │───▶│   Base de Datos │
│ • dim_users     │    │                 │    │                 │
│ • transactions  │    │ • Limpieza      │    │ • Métricas      │
│                 │    │ • Transformación│    │ • A/B Testing   │
└─────────────────┘    │ • Carga         │    │ • Tiempo Real   │
                       └─────────────────┘    └─────────────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────┐
                                              │   Streamlit     │
                                              │   Dashboard     │
                                              │                 │
                                              │ • Visualización │
                                              │ • Análisis      │
                                              │ • Tiempo Real   │
                                              └─────────────────┘
```

### **Flujo de Datos:**
1. **Ingesta**: Datasets CSV → Apache Spark
2. **Procesamiento**: ETL con PySpark → Transformación y cálculo de métricas
3. **Almacenamiento**: Resultados → Apache Cassandra
4. **Visualización**: Dashboard Streamlit → Consume datos directamente desde Cassandra

## 📊 Datasets Utilizados

- **`lk_onboarding.csv`**: Información del proceso de onboarding de usuarios
- **`dim_users.csv`**: Detalles de los usuarios
- **`bt_users_transactions.csv`**: Transacciones de los usuarios

## 🔧 Tecnologías del Sistema

- **ETL**: Apache Spark (PySpark)
- **Base de Datos**: Apache Cassandra
- **Dashboard**: Streamlit
- **Visualización**: Plotly
- **Conexión**: Cassandra Driver para Python

## 📈 Lógicas de Negocio - Indicadores Calculados

### **Filtrado de Datos**
- **Usuarios sin segmento**: Se excluyen del análisis usuarios que no tienen segmento asignado
- **Segmentos válidos**: Solo se consideran segmento 1 (Individuals) y 2 (Sellers)
- **Calidad de datos**: Mejora la precisión del análisis al eliminar datos inconsistentes

### 1. **Drop Rate (Tasa de Abandono)**
- **Definición**: Usuarios que abandonan el proceso de onboarding
- **Cálculo**: `drop = 1` si `return = 0`, `drop = 0` si `return = 1`
- **Interpretación**: Porcentaje de usuarios que no completan el onboarding

### 2. **Activación Rate (Tasa de Activación)**
- **Definición**: Usuarios que completan el proceso de activación
- **Cálculo**: `activacion = 1` si existe fecha de `activacion_dt`, `activacion = 0` en caso contrario
- **Interpretación**: Porcentaje de usuarios que se activan después del registro

### 3. **Setup Rate (Tasa de Configuración)**
- **Definición**: Usuarios que completan la configuración inicial
- **Cálculo**: `setup = 1` si existe fecha de `setup_dt`, `setup = 0` en caso contrario
- **Interpretación**: Porcentaje de usuarios que configuran su cuenta

### 4. **Hábito Rate (Tasa de Hábito) - Calculado**
- **Definición**: Usuarios que desarrollan un hábito de uso de la plataforma
- **Cálculo por Segmento**:
  - **Individuals (Segmento 1)**: Usuario con ≥5 días distintos de transacciones en los primeros 30 días
  - **Sellers (Segmento 2)**: Usuario con ≥5 cobros (tipos 8 o 9) en los primeros 30 días
- **Interpretación**: Porcentaje de usuarios que adoptan la plataforma como hábito

## 🔬 A/B Testing

### **Asignación de Grupos**
- **Método**: Asignación aleatoria uniforme
- **Distribución**: 5% Control, 95% Tratamiento
- **Propósito**: Simular el flujo real de usuarios cuando el experimento esté en producción
- **Ventajas**:
  - Elimina sesgos de selección
  - Permite comparación estadísticamente válida
  - Replica condiciones reales de experimentación

### **Grupos del Experimento**
- **Control**: Grupo que recibe la experiencia actual (baseline)
- **Treatment**: Grupo que recibe la nueva experiencia/feature a testear

## 🏗️ Estructura del Proyecto

```
tpfinal_bigdata/
├── artifacts/                          # Resultados del ETL
│   └── user_onboarding_metrics_clean/  # Métricas limpias (solo hábito calculado)
├── etl_pipeline_clean.py              # ETL principal (versión limpia)
├── dashboard_cassandra.py              # Dashboard avanzado (Cassandra)
├── requirements.txt                    # Dependencias
├── docker-compose.yml                 # Configuración de servicios
├── README.md                          # Documentación
├── lk_onboarding.csv                  # Dataset de onboarding
├── dim_users.csv                      # Dataset de usuarios
└── bt_users_transactions.csv          # Dataset de transacciones
```

## 🚀 Instalación y Configuración

### 1. **Requisitos Previos**
- Python 3.8+
- Java 8+ (para Spark)
- Docker y Docker Compose

### 2. **Instalación de Dependencias**
```bash
pip install -r requirements.txt
```

**Dependencias incluidas:**
- `pyspark==3.5.0` - Procesamiento distribuido
- `cassandra-driver==3.28.0` - Conector para Cassandra
- `streamlit==1.28.1` - Framework de dashboard
- `plotly==5.17.0` - Visualizaciones interactivas
- `pandas==2.1.4` - Manipulación de datos
- `numpy==1.24.3` - Cálculos numéricos
- `matplotlib==3.8.2` - Visualizaciones básicas
- `seaborn==0.13.0` - Visualizaciones estadísticas

### 3. **Configuración de Servicios**
```bash
docker-compose up -d
```

## 📊 Ejecución del Pipeline

### 1. **Ejecutar ETL**
```bash
python3 etl_pipeline_clean.py
```

**El ETL realiza:**
- ✅ Carga de datasets CSV
- ✅ Limpieza y validación de datos
- ✅ Cálculo de métricas de negocio
- ✅ Asignación aleatoria de grupos A/B testing
- ✅ Almacenamiento en Cassandra
- ✅ Generación de archivos CSV de respaldo

### 2. **Ejecutar Dashboard**

```bash
streamlit run dashboard_cassandra.py
```

**Características del Dashboard:**
- ✅ **Datos en tiempo real** desde Cassandra
- ✅ **Configuración dinámica** de conexión (host, puerto, keyspace, tabla)
- ✅ **Prueba de conexión** antes de cargar datos
- ✅ **Cache inteligente** (5 minutos) para mejor rendimiento
- ✅ **Barra de progreso** durante la carga de datos
- ✅ **Navegación modular** por secciones
- ✅ **Estadísticas en tiempo real** de la base de datos
- ✅ **Filtros avanzados** por grupo A/B, segmento y métricas
- ✅ **Exportación de datos** filtrados a CSV
- ✅ **Monitoreo de conexión** y estadísticas

**Secciones del Dashboard:**
1. **📈 Dashboard Completo** - Vista general de todas las métricas
2. **🔄 Funnel** - Análisis del funnel de onboarding
3. **👥 Segmentos** - Comparación entre Individuals y Sellers
4. **🔬 A/B Testing** - Análisis del experimento
5. **📊 Datos Raw** - Datos filtrables y exportables

## 📈 Métricas y KPIs

### **Funnel de Onboarding**
1. **Registro**: 100% (usuarios que inician el proceso)
2. **Activación**: % de usuarios que completan la activación
3. **Setup**: % de usuarios que configuran su cuenta
4. **Hábito**: % de usuarios que desarrollan hábito de uso

### **Análisis por Segmento**
- **Individuals**: Usuarios individuales (segmento 1)
- **Sellers**: Vendedores/Comerciantes (segmento 2)

### **Análisis A/B Testing**
- Comparación de métricas entre grupos control y tratamiento
- Diferencias estadísticas en tasas de conversión
- Análisis de impacto por segmento

## 🔍 Características del Dashboard

### **⚙️ Configuración de Base de Datos**
- **Host configurable**: Por defecto localhost
- **Puerto configurable**: Por defecto 9042
- **Keyspace configurable**: Por defecto fintech_analytics
- **Tabla configurable**: Por defecto user_onboarding_metrics_clean

### **🔍 Prueba de Conexión**
- **Verificación automática**: Antes de cargar datos
- **Feedback visual**: Éxito, advertencia o error
- **Conteo de registros**: Muestra cuántos datos están disponibles

### **📊 Carga Inteligente**
- **Cache de 5 minutos**: Evita consultas repetidas
- **Barra de progreso**: Muestra el avance de la carga
- **Manejo de errores**: Robustez en la conexión
- **Estadísticas en tiempo real**: Métricas de la base de datos

### **🎯 Navegación Modular**
- **Dashboard Completo**: Vista general
- **Funnel**: Análisis del flujo de usuarios
- **Segmentos**: Comparación por tipo de usuario
- **A/B Testing**: Análisis del experimento
- **Datos Raw**: Datos filtrables y exportables

### **📈 Estadísticas Detalladas**
- **Total de registros**: Desde Cassandra
- **Distribución por segmento**: Individuals vs Sellers
- **Distribución A/B**: Control vs Treatment
- **Última actualización**: Timestamp de la carga
- **Fuente de datos**: Cassandra o CSV

### **🔧 Filtros Avanzados**
- **Por grupo A/B**: Control o Treatment
- **Por segmento**: Individuals o Sellers
- **Por métricas**: Con activación, setup, hábito, sin drop
- **Exportación**: Descarga de datos filtrados

## 🛠️ Tecnologías Utilizadas

- **Apache Spark**: Procesamiento distribuido de datos
- **Apache Cassandra**: Base de datos NoSQL para almacenamiento en tiempo real
- **Streamlit**: Framework para dashboards web interactivos
- **Plotly**: Librería de visualización interactiva
- **Cassandra Driver**: Conector Python para Cassandra
- **Docker**: Containerización de servicios

## 📝 Notas Técnicas

### **Procesamiento de Datos**
- **LEFT JOINs**: Para mantener todos los usuarios de onboarding
- **Filtrado por segmento**: Solo usuarios con segmento válido (1 o 2)
- **Cálculo de hábito**: Basado en transacciones reales
- **Resolución de inconsistencias**: De segmentos
- **Formateo de fechas**: Para análisis temporal

### **Optimizaciones**
- **Cache inteligente**: En Streamlit para mejor rendimiento
- **Agregaciones eficientes**: En Spark
- **Consultas optimizadas**: Para lectura rápida en Cassandra
- **Manejo de errores**: Robustez en la conexión

### **Ventajas de Cassandra**
- **Consultas rápidas**: Optimizado para lecturas
- **Escalabilidad**: Maneja grandes volúmenes de datos
- **Disponibilidad**: Alta disponibilidad y tolerancia a fallos
- **Tiempo real**: Datos actualizados instantáneamente

### **Limitaciones de Cassandra**
- **No GROUP BY**: En columnas que no son PRIMARY KEY
- **Consultas simples**: Para mejor rendimiento
- **Estadísticas con pandas**: Calculadas después de cargar datos

## 🔧 Solución de Problemas

### **Error de GROUP BY en Cassandra**
```
Error: Group by is currently only supported on the columns of the PRIMARY KEY
```
**Solución**: El dashboard calcula estadísticas usando pandas después de cargar los datos.

### **Conexión a Cassandra**
- Verificar que Docker esté ejecutándose
- Verificar que el puerto 9042 esté disponible
- Usar el botón "Probar Conexión" en el dashboard

### **Datos no disponibles**
- Ejecutar el ETL primero: `python3 etl_pipeline_clean.py`
- Verificar que Cassandra esté ejecutándose
- Verificar la conexión con el botón "Probar Conexión"

## 🤝 Contribución

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para detalles.

## 👥 Autores

- **Equipo de Big Data Engineering**
- **Fintech Analytics Project**

---

*Proyecto desarrollado para análisis de onboarding y optimización de experiencia de usuario en plataformas fintech con datos en tiempo real desde Cassandra.* 