from pathlib import Path

from src.ingestion.carga_datos import carga_datos
from src.cleaning.limpia_datos import limpiar_datos
from src.emissions.calculadora import calcular_emisiones
from src.analysis.metrics import calcular_metricas

def run_pipeline(ruta_datos, ruta_factores, ruta_salida=None):
    # Paso 1: Cargar datos
    datos = carga_datos(ruta_datos)
    
    # Paso 2: Limpiar datos
    datos_limpios = limpiar_datos(datos)
    
    # Paso 3: Calcular emisiones
    datos_emisiones = calcular_emisiones(datos_limpios, ruta_factores)
    
    # Paso 4: Calcular métricas
    metricas = calcular_metricas(datos_emisiones)

    if ruta_salida:
        ruta_salida = Path(ruta_salida)
        ruta_salida.parent.mkdir(parents=True, exist_ok=True)
        datos_emisiones.to_csv(ruta_salida, index=False)

    return datos_emisiones, metricas

if __name__ == "__main__":
    datos_emisiones,metricas = run_pipeline(
        ruta_datos="data/raw/datos_emisiones.csv",
        ruta_factores="data/external/factores_emision.csv",
        ruta_salida="data/processed/datos_emisiones_procesados.csv",
    )
    print(datos_emisiones)
    print(metricas)
