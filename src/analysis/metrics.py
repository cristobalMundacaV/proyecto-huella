def calcular_metricas(datos):
    total_emisiones = float(datos["emisiones"].sum())

    emisiones_por_empresa = (
        datos.groupby("empresa")["emisiones"]
        .sum()
        .sort_values(ascending=False)
    )
    emisiones_por_actividad = (
        datos.groupby("actividad")["emisiones"]
        .sum()
        .sort_values(ascending=False)
    )
    return {
        "total_emisiones": total_emisiones,
        "emisiones_por_empresa": emisiones_por_empresa,
        "emisiones_por_actividad" : emisiones_por_actividad
    }