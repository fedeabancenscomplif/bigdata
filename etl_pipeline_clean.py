from pyspark.sql import SparkSession
from pyspark.sql.functions import col, to_date, countDistinct, count, when, rand, lit, sum as F_sum
from pyspark.sql.types import DateType
import pandas as pd
from cassandra.cluster import Cluster

# Configurar Spark
spark = SparkSession.builder \
    .appName("Fintech ETL Clean") \
    .getOrCreate()

print("🚀 ETL LIMPIO - FINANCIAL TECHNOLOGY")
print("=" * 50)

# 1. CARGAR DATASETS
print("\n📊 ETAPA 1: CARGA DE DATOS")

# Cargar datasets
df_onboarding = spark.read.option("header", True).option("inferSchema", True).csv("lk_onboarding.csv")
df_users = spark.read.option("header", True).option("inferSchema", True).csv("dim_users.csv")
df_transactions = spark.read.option("header", True).option("inferSchema", True).csv("bt_users_transactions.csv")

print(f"Datasets cargados:")
print(f"- Onboarding: {df_onboarding.count()} registros")
print(f"- Users: {df_users.count()} registros")
print(f"- Transactions: {df_transactions.count()} registros")

# Análisis inicial de usuarios
onboarding_users = df_onboarding.select("user_id").distinct()
transaction_users = df_transactions.select("user_id").distinct()

print(f"\n📈 ANÁLISIS INICIAL DE USUARIOS:")
print(f"- Usuarios únicos en onboarding: {onboarding_users.count()}")
print(f"- Usuarios únicos con transacciones: {transaction_users.count()}")

# Usuarios sin transacciones (importante para el funnel)
users_without_transactions = onboarding_users.join(transaction_users, "user_id", "left_anti")
print(f"- Usuarios sin transacciones: {users_without_transactions.count()}")

# 2. LIMPIEZA Y PREPARACIÓN
print("\n🧹 ETAPA 2: LIMPIEZA Y PREPARACIÓN")

# Mantener TODOS los usuarios de onboarding (incluyendo los sin transacciones)
df_onboarding_clean = df_onboarding

# Para transacciones, solo limpiar inconsistencias de segmentos
df_transactions_clean = df_transactions

# Resolver inconsistencias de segmentos (solo para usuarios con transacciones)
segment_fix = df_transactions_clean.groupBy("user_id", "segment").agg(
    count("*").alias("segment_count")
).orderBy("user_id", col("segment_count").desc())

from pyspark.sql.window import Window
from pyspark.sql.functions import row_number

window_spec = Window.partitionBy("user_id").orderBy(col("segment_count").desc())
segment_fix = segment_fix.withColumn("rn", row_number().over(window_spec))
segment_fix = segment_fix.filter(col("rn") == 1).select("user_id", "segment")

# 3. FORMATEAR FECHAS
print("\n📅 FORMATEANDO FECHAS...")

for colname in ["first_login_dt", "activacion_dt", "habito_dt", "setup_dt"]:
    df_onboarding_clean = df_onboarding_clean.withColumn(colname, to_date(col(colname), "yyyy-MM-dd"))

df_transactions_clean = df_transactions_clean.withColumn("transaction_dt", to_date(col("transaction_dt"), "yyyy-MM-dd"))

# 4. ASIGNAR GRUPOS A/B TESTING
print("\n🔬 ASIGNANDO GRUPOS A/B TESTING...")

# Crear grupos: 5% control, 95% tratamiento
df_onboarding_clean = df_onboarding_clean.withColumn("random", rand())
df_onboarding_clean = df_onboarding_clean.withColumn(
    "ab_group", 
    when(col("random") <= 0.05, "control").otherwise("treatment")
)

ab_distribution = df_onboarding_clean.groupBy("ab_group").count()
print("Distribución A/B Testing:")
ab_distribution.show()

# 5. CALCULAR MÉTRICAS DE NEGOCIO
print("\n📈 ETAPA 3: TRANSFORMACIÓN Y CÁLCULO DE MÉTRICAS")

# Unir datos - LEFT JOIN para mantener todos los usuarios de onboarding
df = df_onboarding_clean.join(
    segment_fix, 
    on="user_id", 
    how="left"
)

# FILTRAR USUARIOS SIN SEGMENTO
print(f"\n🔍 FILTRANDO USUARIOS SIN SEGMENTO...")
total_before = df.count()
df = df.filter(col("segment").isNotNull())
total_after = df.count()
filtered_out = total_before - total_after

print(f"Usuarios antes del filtro: {total_before:,}")
print(f"Usuarios después del filtro: {total_after:,}")
print(f"Usuarios filtrados (sin segmento): {filtered_out:,}")

# Calcular métricas
df = df.withColumn("drop", when(col("return") == 0, 1).otherwise(0))

# Análisis de distribución por segmento después del filtrado
print(f"\n📊 DISTRIBUCIÓN POR SEGMENTO (después del filtrado):")
segment_distribution = df.groupBy("segment").count().orderBy("segment")
segment_distribution.show()

# Preparar transacciones para hábito (solo usuarios con transacciones)
df_tx = df_transactions_clean.join(
    df.select("user_id", "first_login_dt", "segment", "ab_group").withColumnRenamed("segment", "user_segment"), 
    on="user_id", how="inner"
)
df_tx = df_tx.withColumn("diff_days", (col("transaction_dt").cast(DateType()) - col("first_login_dt").cast(DateType())).cast("int"))
df_tx = df_tx.filter((col("diff_days") >= 0) & (col("diff_days") <= 30))

# Hábito individuals: ≥5 días distintos
habit_indiv = df_tx.filter(col("user_segment") == 1) \
    .groupBy("user_id", "ab_group").agg(countDistinct("transaction_dt").alias("active_days")) \
    .withColumn("habito_calc", when(col("active_days") >= 5, 1).otherwise(0)) \
    .select("user_id", "ab_group", "habito_calc")

# Hábito sellers: ≥5 cobros (type 8 o 9)
habit_seller = df_tx.filter((col("user_segment") == 2) & (col("type").isin(8, 9))) \
    .groupBy("user_id", "ab_group").agg(count("*").alias("cobros")) \
    .withColumn("habito_calc", when(col("cobros") >= 5, 1).otherwise(0)) \
    .select("user_id", "ab_group", "habito_calc")

# Unir resultados de hábito
habit_all = habit_indiv.unionByName(habit_seller)

# Merge con datos finales - LEFT JOIN para mantener todos los usuarios
df_final = df.join(habit_all.select("user_id", "habito_calc"), on="user_id", how="left")
df_final = df_final.withColumn("habito_calc", when(col("habito_calc").isNull(), 0).otherwise(col("habito_calc")))

# 6. SELECCIÓN FINAL - SOLO HÁBITO CALCULADO
df_metrics = df_final.select(
    "user_id", "segment", "ab_group", "drop", "activacion", "setup", "habito_calc"
)

print(f"\n✅ MÉTRICAS CALCULADAS: {df_metrics.count()} registros")
print(f"Usuarios únicos finales: {df_metrics.select('user_id').distinct().count()}")

# 7. ANÁLISIS A/B TESTING
print("\n🔬 ANÁLISIS A/B TESTING")

# Métricas por grupo
ab_metrics = df_metrics.groupBy("ab_group").agg(
    count("*").alias("total_users"),
    (F_sum("drop") / count("*") * 100).alias("drop_rate"),
    (F_sum("activacion") / count("*") * 100).alias("activation_rate"),
    (F_sum("setup") / count("*") * 100).alias("setup_rate"),
    (F_sum("habito_calc") / count("*") * 100).alias("habit_rate")
)

print("Métricas por grupo A/B:")
ab_metrics.show()

# 8. ANÁLISIS DEL FUNNEL COMPLETO
print("\n🔄 ANÁLISIS DEL FUNNEL COMPLETO")

funnel_analysis = df_metrics.agg(
    count("*").alias("total_users"),
    F_sum("activacion").alias("activated_users"),
    F_sum("setup").alias("setup_users"),
    F_sum("habito_calc").alias("habit_users")
).collect()[0]

total = funnel_analysis["total_users"]
activated = funnel_analysis["activated_users"]
setup = funnel_analysis["setup_users"]
habit = funnel_analysis["habit_users"]

print(f"FUNNEL DE ONBOARDING (solo usuarios con segmento):")
print(f"1. Usuarios Registrados: {total:,} (100%)")
print(f"2. Activación: {activated:,} ({activated/total*100:.1f}%)")
print(f"3. Setup: {setup:,} ({setup/total*100:.1f}%)")
print(f"4. Hábito: {habit:,} ({habit/total*100:.1f}%)")

# 9. GUARDAR EN CASSANDRA
print("\n💾 GUARDANDO EN CASSANDRA...")

# Convertir a pandas
pandas_df = df_metrics.toPandas()

try:
    cluster = Cluster(['localhost'], port=9042)
    session = cluster.connect()
    
    session.execute("USE fintech_analytics")
    
    # Crear tabla limpia con solo hábito calculado
    create_table_query = """
    CREATE TABLE IF NOT EXISTS user_onboarding_metrics_clean (
        user_id TEXT,
        segment INT,
        ab_group TEXT,
        "drop" INT,
        activacion INT,
        setup INT,
        habito_calc INT,
        PRIMARY KEY (user_id)
    )
    """
    
    session.execute(create_table_query)
    
    # Limpiar tabla anterior
    session.execute("TRUNCATE user_onboarding_metrics_clean")
    
    # Insertar datos
    insert_query = """
    INSERT INTO user_onboarding_metrics_clean 
    (user_id, segment, ab_group, "drop", activacion, setup, habito_calc) 
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    
    prepared = session.prepare(insert_query)
    
    for index, row in pandas_df.iterrows():
        session.execute(prepared, (
            str(row['user_id']),
            int(row['segment']) if pd.notna(row['segment']) else None,
            str(row['ab_group']),
            int(row['drop']) if pd.notna(row['drop']) else None,
            int(row['activacion']) if pd.notna(row['activacion']) else None,
            int(row['setup']) if pd.notna(row['setup']) else None,
            int(row['habito_calc']) if pd.notna(row['habito_calc']) else None
        ))
    
    print("✅ Datos cargados en Cassandra con éxito")
    
except Exception as e:
    print(f"❌ Error al cargar en Cassandra: {e}")

finally:
    if 'session' in locals():
        session.shutdown()
    if 'cluster' in locals():
        cluster.shutdown()

# 10. GUARDAR EN CSV
df_metrics.write \
    .mode("overwrite") \
    .option("header", "true") \
    .csv("artifacts/user_onboarding_metrics_clean")

print("\n✅ ETL LIMPIO COMPLETADO")
print(f"Total de registros procesados: {df_metrics.count()}")
print(f"Usuarios sin segmento filtrados: {filtered_out:,}")
print("Archivos guardados en artifacts/user_onboarding_metrics_clean")

spark.stop() 