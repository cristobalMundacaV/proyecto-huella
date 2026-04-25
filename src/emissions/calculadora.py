import pandas as pd

def calcular_emisiones(datos, ruta_factores):
    datos = datos.copy()
    factores = pd.read_csv(ruta_factores)

    factores.columns = (
        factores.columns
        .str.strip()
        .str.lower()
        .str.replace(' ', '_')
    )

    factores["actividad"] = factores["actividad"].astype(str).str.strip().str.lower()

    datos = datos.merge(
        factores,
        on="actividad",
        how="left"
    )

    if datos["factor_emision"].isna().any():
        actividades_sin_factor = datos.loc[
            datos["factor_emision"].isna(),
            "actividad"
            ].unique()
        raise ValueError(f"Faltan factores de emisión para las siguientes actividades: {actividades_sin_factor}"
        )
        
    datos["emisiones"] = datos["cantidad"] * datos["factor_emision"]

    return datos
