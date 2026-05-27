def limpiar_datos(datos):
    datos = datos.copy()

    datos.columns = (
        datos.columns
        .str.strip()
        .str.lower()
        .str.replace(' ', '_')
    )

    datos = datos.drop_duplicates()

    columnas_obligatorias = ["constructora", "fuente_emision", "cantidad"]

    for columna in columnas_obligatorias:
        if columna not in datos.columns:
            raise ValueError(f"Falta la columna obligatoria: {columna}")
        
    datos["constructora"] = (
        datos["constructora"]
        .astype(str)
        .str.strip()
        .str.lower()
        .str.title()
    )
    datos["fuente_emision"] = (
        datos["fuente_emision"]
        .astype(str)
        .str.strip()
        .str.lower()
        .str.title()
    )
    datos["cantidad"] = datos["cantidad"].astype(float)

    datos = datos.dropna(subset=columnas_obligatorias)

    return datos