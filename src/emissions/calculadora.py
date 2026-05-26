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

    factores["fuente_emision_key"] = factores["fuente_emision"].astype(str).str.strip().str.lower()
    factores = factores.drop(columns=["fuente_emision"])
    datos["fuente_emision_key"] = datos["fuente_emision"].astype(str).str.strip().str.lower()

    datos = datos.merge(
        factores,
        on="fuente_emision_key",
        how="left"
    )

    if datos["factor_emision"].isna().any():
        fuentes_sin_factor = datos.loc[
            datos["factor_emision"].isna(),
            "fuente_emision"
            ].unique()
        raise ValueError(f"Faltan factores de emisión para las siguientes fuentes: {fuentes_sin_factor}"
        )
        
    datos["emisiones"] = datos["cantidad"] * datos["factor_emision"]
    datos = datos.drop(columns=["fuente_emision_key"])

    return datos
