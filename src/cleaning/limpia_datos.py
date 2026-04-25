def limpiar_datos(datos):
    datos = datos.copy()

    datos.columns = (
        datos.columns
        .str.strip()
        .str.lower()
        .str.replace(' ', '_')
    )

    datos = datos.drop_duplicates()

    columnas_obligatorias = ["empresa", "actividad", "cantidad"]

    for columna in columnas_obligatorias:
        if columna not in datos.columns:
            raise ValueError(f"Falta la columna obligatoria: {columna}")
        
    datos["empresa"] = datos["empresa"].astype(str).str.strip()
    datos["actividad"] = datos["actividad"].astype(str).str.strip().str.lower()
    datos["cantidad"] = datos["cantidad"].astype(float)

    datos = datos.dropna(subset=columnas_obligatorias)

    return datos