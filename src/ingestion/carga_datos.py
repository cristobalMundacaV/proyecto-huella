import pandas as pd
from pathlib import Path

def carga_datos(ruta_archivo):
    ruta = Path(ruta_archivo)

    if not ruta.exists():
        raise FileNotFoundError(f"El archivo {ruta_archivo} no existe.")
    
    if ruta.suffix == '.csv':
        return pd.read_csv(ruta_archivo)
    
    if ruta.suffix in [".xlsx", ".xls"]:
        return pd.read_excel(ruta_archivo)
    
    raise ValueError("Formato de archivo no soportado. Use .csv o .xlsx")