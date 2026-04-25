import pandas as pd
from django.conf import settings
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from .services.local_advisor import generar_analisis_local
from src.analysis.metrics import calcular_metricas
from src.cleaning.limpia_datos import limpiar_datos
from src.emissions.calculadora import calcular_emisiones

try:
    from .services.ai_advisor import generar_analisis_ia
except Exception:
    generar_analisis_ia = None


def build_dashboard_response(df):
    df_limpio = limpiar_datos(df)

    df_emisiones = calcular_emisiones(
        df_limpio,
        ruta_factores=str(settings.EXTERNAL_DATA_DIR / "factores_emision.csv"),
    )

    metricas = calcular_metricas(df_emisiones)

    return {
        "total_emisiones": float(metricas["total_emisiones"]),
        "datos": df_emisiones.to_dict(orient="records"),
        "emisiones_por_empresa": metricas["emisiones_por_empresa"].to_dict(),
        "emisiones_por_actividad": metricas["emisiones_por_actividad"].to_dict(),
    }


def read_uploaded_dataset(file):
    if file.name.endswith(".csv"):
        return pd.read_csv(file)
    if file.name.endswith((".xlsx", ".xls")):
        return pd.read_excel(file)
    raise ValueError("Formato no soportado")


def process_dataset(df):
    df_limpio = limpiar_datos(df)

    return calcular_emisiones(
        df_limpio,
        ruta_factores=str(settings.EXTERNAL_DATA_DIR / "factores_emision.csv"),
    )


def get_critical_activity(df):
    activity_totals = df.groupby("actividad")["emisiones"].sum()

    if activity_totals.empty:
        return "Sin datos"

    return activity_totals.idxmax()


def get_best_optimized_company(df_actual, df_simulado):
    actual = df_actual.groupby("empresa")["emisiones"].sum()
    simulated = df_simulado.groupby("empresa")["emisiones"].sum()
    comparison = pd.DataFrame({"actual": actual, "simulado": simulated}).fillna(0)
    comparison = comparison[comparison["actual"] > 0]

    if comparison.empty:
        return {"empresa": "Sin datos", "reduccion_pct": 0}

    comparison["reduccion_pct"] = (
        (comparison["actual"] - comparison["simulado"]) / comparison["actual"]
    ) * 100
    best_company = comparison["reduccion_pct"].idxmax()

    return {
        "empresa": best_company,
        "reduccion_pct": float(comparison.loc[best_company, "reduccion_pct"]),
    }


def get_recommendation(df_actual, df_simulado, total_actual):
    actual_by_activity = df_actual.groupby("actividad")["emisiones"].sum()
    simulated_by_activity = df_simulado.groupby("actividad")["emisiones"].sum()

    if "diesel" not in actual_by_activity or total_actual <= 0:
        return "Prioriza la actividad con mayor impacto y compara su reduccion antes de escalar el plan."

    diesel_actual = actual_by_activity.get("diesel", 0)
    diesel_simulado = simulated_by_activity.get("diesel", 0)
    diesel_reduction = max(diesel_actual - diesel_simulado, 0)
    diesel_impact_pct = (diesel_reduction / total_actual) * 100

    if diesel_impact_pct > 0:
        return (
            "Reducir diesel en el escenario simulado genera un impacto "
            f"estimado de -{diesel_impact_pct:.1f}% en emisiones totales. "
            "Considera electrificacion o combustibles alternativos."
        )

    return "Diesel sigue siendo un foco de riesgo. Considera electrificacion o combustibles alternativos."


def comparar_escenarios(df_actual, df_simulado):
    emisiones_actuales = process_dataset(df_actual)
    emisiones_simuladas = process_dataset(df_simulado)

    total_actual = float(emisiones_actuales["emisiones"].sum())
    total_simulado = float(emisiones_simuladas["emisiones"].sum())
    reduccion_pct = (
        ((total_actual - total_simulado) / total_actual) * 100
        if total_actual > 0
        else 0
    )
    actividad_actual = get_critical_activity(emisiones_actuales)
    actividad_simulada = get_critical_activity(emisiones_simuladas)

    return {
        "total_actual": total_actual,
        "total_simulado": total_simulado,
        "reduccion_pct": float(reduccion_pct),
        "actividad_critica_actual": actividad_actual,
        "actividad_critica_simulada": actividad_simulada,
        "actividad_critica_cambio": actividad_actual != actividad_simulada,
        "empresa_mas_optimizada": get_best_optimized_company(
            emisiones_actuales,
            emisiones_simuladas,
        ),
        "recomendacion": get_recommendation(
            emisiones_actuales,
            emisiones_simuladas,
            total_actual,
        ),
    }


@api_view(["GET"])
def dashboard_data(request):
    try:
        df = pd.read_csv(settings.DATOS_EMISIONES_PATH)
        return Response(build_dashboard_response(df))
    except Exception as exc:
        return Response({"error": str(exc)}, status=400)


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def upload_dashboard_data(request):
    archivo = request.FILES.get("file")

    if not archivo:
        return Response({"error": "No se recibio ningun archivo"}, status=400)

    try:
        df = read_uploaded_dataset(archivo)
        return Response(build_dashboard_response(df))
    except Exception as exc:
        return Response({"error": str(exc)}, status=400)


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def compare_dashboard_data(request):
    dataset_actual = request.FILES.get("dataset_actual")
    dataset_simulado = request.FILES.get("dataset_simulado")

    if not dataset_actual or not dataset_simulado:
        return Response(
            {"error": "Debes subir un dataset actual y un dataset simulado"},
            status=400,
        )

    try:
        df_actual = read_uploaded_dataset(dataset_actual)
        df_simulado = read_uploaded_dataset(dataset_simulado)
        return Response(comparar_escenarios(df_actual, df_simulado))
    except Exception as exc:
        return Response({"error": str(exc)}, status=400)


@api_view(["POST"])
def ai_advisor(request):
    try:
        if generar_analisis_ia:
            analisis = generar_analisis_ia(request.data)
            fuente = "openai"
        else:
            raise RuntimeError("OpenAI no disponible")
    except Exception:
        analisis = generar_analisis_local(request.data)
        fuente = "huella_engine"

    return Response({"analisis": analisis, "fuente": fuente})
