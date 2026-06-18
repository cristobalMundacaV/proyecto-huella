from rest_framework.decorators import api_view
from rest_framework.response import Response

from .services.intelligence_engine import build_recommendation_context, generate_recommendations


@api_view(["POST"])
def recommendation_context(request):
    payload = request.data or {}
    return Response(build_recommendation_context(payload))


@api_view(["POST"])
def recomendaciones(request):
    payload = request.data or {}
    return Response(generate_recommendations(payload))
