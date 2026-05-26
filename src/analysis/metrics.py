def calcular_metricas(datos):
    total_emisiones = float(datos["emisiones"].sum())

    emisiones_por_constructora = (
        datos.groupby("constructora")["emisiones"]
        .sum()
        .sort_values(ascending=False)
    )
    emisiones_por_fuente = (
        datos.groupby("fuente_emision")["emisiones"]
        .sum()
        .sort_values(ascending=False)
    )
    return {
        "total_emisiones": total_emisiones,
        "emisiones_por_constructora": emisiones_por_constructora,
        "emisiones_por_fuente" : emisiones_por_fuente
    }