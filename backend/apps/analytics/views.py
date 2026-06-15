from collections import defaultdict
from decimal import Decimal

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Count, Sum
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from .models import (
    ConfiguracionConstructora,
    Constructora,
    EtapaObra,
    EvidenciaObra,
    FactorEmision,
    MaterialConstruccion,
    Obra,
    RegistroEmision,
    TransporteObra,
    UsuarioConstructora,
)
from .serializers import (
    ConfiguracionConstructoraSerializer,
    ConstructoraSerializer,
    EtapaObraSerializer,
    EvidenciaObraSerializer,
    FactorEmisionSerializer,
    MaterialConstruccionSerializer,
    ObraSerializer,
    RegistroEmisionSerializer,
    TransporteObraSerializer,
    UsuarioConstructoraCreateSerializer,
    UsuarioConstructoraSerializer,
)
from .services.local_advisor import generar_analisis_local

try:
    from .services.ai_advisor import generar_analisis_ia
except Exception:
    generar_analisis_ia = None


def to_float(value):
    return float(value or 0)


def sorted_group(grouped):
    return dict(sorted(grouped.items(), key=lambda item: item[1], reverse=True))


def get_constructora_or_404(constructora_id):
    return get_object_or_404(Constructora, constructora_id=constructora_id)


def get_obra_or_404(codigo_obra):
    return get_object_or_404(Obra, codigo_obra=codigo_obra)


def serialize_auth_user(user):
    if not user or not user.is_authenticated:
        return None

    perfiles = UsuarioConstructora.objects.select_related("constructora").filter(
        user=user,
        activo=True,
    )
    constructoras_usuario = [
        {
            "constructora_id": perfil.constructora.constructora_id,
            "constructora_nombre": perfil.constructora.nombre,
            "preset": perfil.constructora.preset,
            "rol": perfil.rol,
        }
        for perfil in perfiles
    ]
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "nombre": user.get_full_name().strip() or user.username,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "constructoras": constructoras_usuario,
    }


@ensure_csrf_cookie
@csrf_exempt
@api_view(["GET"])
def auth_me(request):
    return Response(
        {
            "authenticated": bool(request.user and request.user.is_authenticated),
            "user": serialize_auth_user(request.user),
            "has_users": User.objects.exists(),
        }
    )


@ensure_csrf_cookie
@api_view(["GET", "POST"])
def auth_csrf_token(request):
    return Response({"csrfToken": get_token(request)})


@ensure_csrf_cookie
@csrf_exempt
@api_view(["POST"])
def auth_login(request):
    username = (request.data.get("username") or "").strip()
    password = request.data.get("password") or ""
    user = authenticate(request, username=username, password=password)
    if not user:
        return Response(
            {"error": "Credenciales invalidas."}, status=status.HTTP_400_BAD_REQUEST
        )
    if not user.is_active:
        return Response(
            {"error": "El usuario esta inactivo."}, status=status.HTTP_403_FORBIDDEN
        )
    login(request, user)
    return Response({"authenticated": True, "user": serialize_auth_user(user)})


@csrf_exempt
@api_view(["POST"])
def auth_logout(request):
    logout(request)
    return Response({"authenticated": False})


@csrf_exempt
@api_view(["POST"])
def auth_bootstrap(request):
    if User.objects.exists():
        return Response(
            {"error": "El usuario inicial ya fue creado."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    username = (request.data.get("username") or "").strip()
    password = request.data.get("password") or ""
    if not username or len(password) < 8:
        return Response(
            {"error": "Ingresa usuario y una clave de al menos 8 caracteres."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = User.objects.create_superuser(
        username=username,
        email=(request.data.get("email") or "").strip(),
        password=password,
        first_name=(request.data.get("first_name") or "").strip(),
        last_name=(request.data.get("last_name") or "").strip(),
    )
    constructora = Constructora.objects.order_by("nombre").first()
    if constructora:
        UsuarioConstructora.objects.create(
            user=user,
            constructora=constructora,
            rol=UsuarioConstructora.Rol.ADMIN,
            cargo="Administrador",
        )
    login(request, user)
    return Response({"authenticated": True, "user": serialize_auth_user(user)})


def build_system_status():
    return {
        "constructoras": Constructora.objects.count(),
        "etapas": EtapaObra.objects.count(),
        "obras": Obra.objects.count(),
        "registros_emision": RegistroEmision.objects.count(),
        "evidencias": EvidenciaObra.objects.count(),
        "transportes": TransporteObra.objects.count(),
        "factores": FactorEmision.objects.count(),
        "materiales": MaterialConstruccion.objects.count(),
    }


def build_environmental_summary(registros, obras=None, evidencias=None):
    obras = obras or Obra.objects.filter(
        id__in=registros.values_list("obra_id", flat=True)
    )
    evidencias = evidencias or EvidenciaObra.objects.filter(obra__in=obras)

    total = to_float(registros.aggregate(total=Sum("emisiones_kg_co2e"))["total"])
    por_categoria = defaultdict(float)
    por_etapa = defaultdict(lambda: {"emisiones": 0.0, "registros": 0})
    por_obra = defaultdict(float)
    fuentes = defaultdict(
        lambda: {"emisiones": 0.0, "categoria": "Otros", "obra": "", "etapa": ""}
    )

    for registro in registros.select_related("obra", "etapa"):
        emisiones = to_float(registro.emisiones_kg_co2e)
        categoria = registro.categoria or RegistroEmision.Categoria.OTROS
        etapa_nombre = registro.etapa.nombre if registro.etapa_id else "Sin etapa"
        obra_nombre = registro.obra.nombre if registro.obra_id else "Sin obra"
        fuente = registro.fuente_emision or "Sin fuente"

        por_categoria[categoria] += emisiones
        por_etapa[etapa_nombre]["emisiones"] += emisiones
        por_etapa[etapa_nombre]["registros"] += 1
        por_obra[obra_nombre] += emisiones
        fuentes[fuente]["emisiones"] += emisiones
        fuentes[fuente]["categoria"] = categoria
        fuentes[fuente]["obra"] = obra_nombre
        fuentes[fuente]["etapa"] = etapa_nombre

    categoria_critica = max(por_categoria, key=por_categoria.get, default="Sin datos")
    obra_critica = max(por_obra, key=por_obra.get, default="Sin datos")
    etapa_critica = max(
        por_etapa, key=lambda key: por_etapa[key]["emisiones"], default="Sin datos"
    )
    fuente_critica = max(
        fuentes, key=lambda key: fuentes[key]["emisiones"], default="Sin datos"
    )
    superficie_total = sum(to_float(obra.superficie_m2) for obra in obras)
    intensidad = None if superficie_total <= 0 else total / superficie_total
    registros_count = registros.count()
    evidencias_count = evidencias.count()
    registros_con_evidencia = (
        registros.filter(evidencias__isnull=False).distinct().count()
    )
    cobertura_documental = (
        None
        if registros_count == 0
        else round((registros_con_evidencia / registros_count) * 100, 2)
    )

    top_fuentes = [
        {
            "fuente_emision": fuente,
            "categoria": data["categoria"],
            "obra_etapa": data["etapa"],
            "obra": data["obra"],
            "emisiones_kg_co2e": round(data["emisiones"], 3),
            "porcentaje": round((data["emisiones"] / total) * 100, 2) if total else 0,
        }
        for fuente, data in sorted(
            fuentes.items(), key=lambda item: item[1]["emisiones"], reverse=True
        )[:5]
    ]

    return {
        "total_emisiones": round(total, 3),
        "emisiones_totales": round(total, 3),
        "obra_critica": obra_critica,
        "categoria_critica": categoria_critica,
        "fuente_critica": fuente_critica,
        "etapa_critica": etapa_critica,
        "intensidad_carbono": None if intensidad is None else round(intensidad, 3),
        "intensidad_carbono_estado": (
            "Pendiente de superficie" if intensidad is None else "Calculada"
        ),
        "evidencia_respaldada": (
            "Pendiente de vinculacion"
            if cobertura_documental is None
            else cobertura_documental
        ),
        "evidencias_count": evidencias_count,
        "registros_count": registros_count,
        "emisiones_por_categoria": sorted_group(por_categoria),
        "emisiones_por_etapa": [
            {
                "etapa": etapa,
                "emisiones_kg_co2e": round(data["emisiones"], 3),
                "porcentaje": (
                    round((data["emisiones"] / total) * 100, 2) if total else 0
                ),
                "registros": data["registros"],
            }
            for etapa, data in sorted(
                por_etapa.items(), key=lambda item: item[1]["emisiones"], reverse=True
            )
        ],
        "top_fuentes_criticas": top_fuentes,
        "estado_ambiental": classify_environmental_status(
            total, por_categoria, registros_count, cobertura_documental
        ),
        "insight": build_category_insight(categoria_critica, total),
    }


def classify_environmental_status(
    total, por_categoria, registros_count, cobertura_documental
):
    if total <= 0 or registros_count == 0:
        return "Sin datos"
    max_share = max(por_categoria.values(), default=0) / total if total else 0
    if max_share > 0.6:
        return "Critica"
    if (
        cobertura_documental is not None
        and cobertura_documental >= 70
        and max_share <= 0.5
    ):
        return "Controlada"
    if len([value for value in por_categoria.values() if value > 0]) >= 3:
        return "En seguimiento"
    return "Inicial"


def build_category_insight(categoria, total):
    if not total:
        return "Agrega registros de emision para identificar las fuentes criticas de la obra."
    insights = {
        "Materiales": "Materiales concentra el mayor impacto ambiental. Revisa hormigon, acero, aridos y proveedores para evaluar alternativas de menor carbono incorporado.",
        "Transporte": "Transporte aparece como foco critico. Evalua proveedores mas cercanos, consolidacion de viajes y reduccion de kilometros recorridos.",
        "Maquinaria": "Maquinaria concentra emisiones relevantes. Controlar ralenti, consumo por equipo y mantencion puede reducir el impacto operativo.",
        "Energia": "Energia es una fuente relevante. Revisa uso de generadores, consumo electrico y posibilidades de conexion temporal a red.",
        "Residuos": "Residuos aparece como foco de impacto. Separar residuos valorizables y mejorar trazabilidad de retiro puede reducir disposicion final.",
        "Agua": "Agua requiere seguimiento operativo. Monitorear consumo por etapa ayuda a detectar desviaciones y mejorar eficiencia.",
    }
    return insights.get(
        categoria,
        "Clasifica mejor los registros para priorizar acciones con mayor impacto.",
    )


@api_view(["GET"])
def sistema_estado(request):
    return Response(build_system_status())


@api_view(["GET"])
def dashboard_data(request):
    registros = RegistroEmision.objects.select_related(
        "constructora", "obra", "etapa"
    ).all()
    obras = Obra.objects.all()
    evidencias = EvidenciaObra.objects.all()
    payload = build_environmental_summary(registros, obras=obras, evidencias=evidencias)
    payload["datos"] = RegistroEmisionSerializer(
        registros.order_by("-fecha", "-created_at")[:200], many=True
    ).data
    payload["constructoras_count"] = Constructora.objects.count()
    payload["obras_count"] = obras.count()
    return Response(payload)


@api_view(["GET", "POST"])
def constructoras(request):
    if request.method == "GET":
        serializer = ConstructoraSerializer(
            Constructora.objects.order_by("nombre"), many=True
        )
        return Response(serializer.data)
    serializer = ConstructoraSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    constructora = serializer.save()
    ConfiguracionConstructora.objects.get_or_create(constructora=constructora)
    return Response(
        ConstructoraSerializer(constructora).data, status=status.HTTP_201_CREATED
    )


@api_view(["GET", "PATCH", "DELETE"])
def constructora_detail(request, constructora_id):
    constructora = get_constructora_or_404(constructora_id)
    if request.method == "GET":
        return Response(ConstructoraSerializer(constructora).data)
    if request.method == "DELETE":
        constructora.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    serializer = ConstructoraSerializer(constructora, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(["GET", "PATCH"])
def constructora_configuracion(request, constructora_id):
    constructora = get_constructora_or_404(constructora_id)
    configuracion, _ = ConfiguracionConstructora.objects.get_or_create(
        constructora=constructora
    )
    if request.method == "GET":
        return Response(ConfiguracionConstructoraSerializer(configuracion).data)
    serializer = ConfiguracionConstructoraSerializer(
        configuracion, data=request.data, partial=True
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(["GET"])
def constructora_estado(request, constructora_id):
    constructora = get_constructora_or_404(constructora_id)
    registros = RegistroEmision.objects.filter(constructora=constructora)
    return Response(
        {
            "constructora_id": constructora.constructora_id,
            "preset": constructora.preset,
            "etapas": constructora.etapas.count(),
            "obras": constructora.obras.count(),
            "registros": registros.count(),
            "evidencias": constructora.evidencias.count(),
            "emisiones_kg_co2e": to_float(
                registros.aggregate(total=Sum("emisiones_kg_co2e"))["total"]
            ),
        }
    )


@api_view(["GET"])
def constructora_dashboard(request, constructora_id):
    constructora = get_constructora_or_404(constructora_id)
    registros = RegistroEmision.objects.filter(
        constructora=constructora
    ).select_related("obra", "etapa")
    obras = Obra.objects.filter(constructora=constructora)
    evidencias = EvidenciaObra.objects.filter(constructora=constructora)
    payload = build_environmental_summary(registros, obras=obras, evidencias=evidencias)
    payload["constructora_id"] = constructora.constructora_id
    payload["constructora_nombre"] = constructora.nombre
    payload["preset"] = constructora.preset
    payload["datos"] = RegistroEmisionSerializer(
        registros.order_by("-fecha", "-created_at")[:200], many=True
    ).data
    return Response(payload)


@api_view(["GET", "POST"])
def constructora_usuarios(request, constructora_id):
    constructora = get_constructora_or_404(constructora_id)
    if request.method == "GET":
        perfiles = UsuarioConstructora.objects.select_related(
            "user", "constructora"
        ).filter(constructora=constructora)
        return Response(UsuarioConstructoraSerializer(perfiles, many=True).data)
    serializer = UsuarioConstructoraCreateSerializer(
        data=request.data, context={"constructora": constructora}
    )
    serializer.is_valid(raise_exception=True)
    perfil = serializer.save()
    return Response(
        UsuarioConstructoraSerializer(perfil).data, status=status.HTTP_201_CREATED
    )


@api_view(["GET", "POST"])
def constructora_etapas(request, constructora_id):
    constructora = get_constructora_or_404(constructora_id)
    if request.method == "GET":
        return Response(
            EtapaObraSerializer(constructora.etapas.order_by("nombre"), many=True).data
        )
    serializer = EtapaObraSerializer(
        data={**request.data, "constructora": constructora.id}
    )
    serializer.is_valid(raise_exception=True)
    etapa = serializer.save()
    return Response(EtapaObraSerializer(etapa).data, status=status.HTTP_201_CREATED)


@api_view(["GET", "POST"])
def constructora_obras(request, constructora_id):
    constructora = get_constructora_or_404(constructora_id)
    if request.method == "GET":
        return Response(
            ObraSerializer(
                constructora.obras.select_related("etapa_principal").order_by(
                    "-created_at"
                ),
                many=True,
            ).data
        )
    serializer = ObraSerializer(data={**request.data, "constructora": constructora.id})
    serializer.is_valid(raise_exception=True)
    obra = serializer.save()
    return Response(ObraSerializer(obra).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def constructora_reportes(request, constructora_id):
    constructora = get_constructora_or_404(constructora_id)
    registros = RegistroEmision.objects.filter(
        constructora=constructora
    ).select_related("obra", "etapa")
    payload = build_environmental_summary(
        registros,
        obras=Obra.objects.filter(constructora=constructora),
        evidencias=EvidenciaObra.objects.filter(constructora=constructora),
    )
    payload["constructora_id"] = constructora.constructora_id
    payload["constructora_nombre"] = constructora.nombre
    payload["preset"] = constructora.preset
    payload["reporte"] = {
        "lectura_ejecutiva": payload["insight"],
        "unidad_visual_emisiones": "kg CO2e",
        "agrupacion": "categoria",
    }
    return Response(payload)


@api_view(["GET", "POST"])
def constructora_registros_emision(request, constructora_id):
    constructora = get_constructora_or_404(constructora_id)
    if request.method == "GET":
        registros = (
            RegistroEmision.objects.filter(constructora=constructora)
            .select_related("obra", "etapa")
            .order_by("-fecha", "-created_at")
        )
        return Response(RegistroEmisionSerializer(registros, many=True).data)
    data = request.data.copy()
    data["constructora"] = constructora.id
    serializer = RegistroEmisionSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    registro = serializer.save()
    return Response(
        RegistroEmisionSerializer(registro).data, status=status.HTTP_201_CREATED
    )


@api_view(["GET", "POST"])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def constructora_evidencias(request, constructora_id):
    constructora = get_constructora_or_404(constructora_id)
    if request.method == "GET":
        evidencias = (
            EvidenciaObra.objects.filter(constructora=constructora)
            .select_related("obra", "etapa", "registro_emision")
            .order_by("-created_at")
        )
        return Response(
            EvidenciaObraSerializer(
                evidencias, many=True, context={"request": request}
            ).data
        )
    data = request.data.copy()
    data["constructora"] = constructora.id
    serializer = EvidenciaObraSerializer(data=data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    evidencia = serializer.save()
    return Response(
        EvidenciaObraSerializer(evidencia, context={"request": request}).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET", "POST"])
def obras(request):
    if request.method == "GET":
        return Response(
            ObraSerializer(
                Obra.objects.select_related("constructora", "etapa_principal").order_by(
                    "-created_at"
                ),
                many=True,
            ).data
        )
    serializer = ObraSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    obra = serializer.save()
    return Response(ObraSerializer(obra).data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH", "DELETE"])
def obra_detail(request, codigo_obra):
    obra = get_obra_or_404(codigo_obra)
    if request.method == "GET":
        payload = ObraSerializer(obra).data
        registros = obra.registros_emision.select_related("etapa", "obra")
        payload["analisis_ambiental"] = build_environmental_summary(
            registros,
            obras=Obra.objects.filter(pk=obra.pk),
            evidencias=obra.evidencias.all(),
        )
        return Response(payload)
    if request.method == "DELETE":
        obra.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    serializer = ObraSerializer(obra, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(["GET", "POST"])
def obra_registros_emision(request, codigo_obra):
    obra = get_obra_or_404(codigo_obra)
    if request.method == "GET":
        registros = obra.registros_emision.select_related(
            "constructora", "etapa"
        ).order_by("-fecha", "-created_at")
        return Response(RegistroEmisionSerializer(registros, many=True).data)
    data = request.data.copy()
    data["constructora"] = obra.constructora_id
    data["obra"] = obra.id
    serializer = RegistroEmisionSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    registro = serializer.save()
    return Response(
        RegistroEmisionSerializer(registro).data, status=status.HTTP_201_CREATED
    )


@api_view(["GET", "POST"])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def obra_evidencias(request, codigo_obra):
    obra = get_obra_or_404(codigo_obra)
    if request.method == "GET":
        evidencias = obra.evidencias.select_related(
            "constructora", "etapa", "registro_emision"
        ).order_by("-created_at")
        return Response(
            EvidenciaObraSerializer(
                evidencias, many=True, context={"request": request}
            ).data
        )
    data = request.data.copy()
    data["constructora"] = obra.constructora_id
    data["obra"] = obra.id
    serializer = EvidenciaObraSerializer(data=data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    evidencia = serializer.save()
    return Response(
        EvidenciaObraSerializer(evidencia, context={"request": request}).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET", "POST"])
def obra_transportes(request, codigo_obra):
    obra = get_obra_or_404(codigo_obra)
    if request.method == "GET":
        return Response(
            TransporteObraSerializer(
                obra.transportes.select_related("etapa").order_by("-fecha_hora"),
                many=True,
            ).data
        )
    data = request.data.copy()
    data["obra"] = obra.id
    serializer = TransporteObraSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    transporte = serializer.save()
    return Response(
        TransporteObraSerializer(transporte).data, status=status.HTTP_201_CREATED
    )


@api_view(["GET"])
def verificar_obra(request, codigo_obra):
    obra = get_obra_or_404(codigo_obra)
    registros = obra.registros_emision.all()
    resumen = build_environmental_summary(
        registros,
        obras=Obra.objects.filter(pk=obra.pk),
        evidencias=obra.evidencias.all(),
    )
    return Response(
        {
            "codigo_obra": obra.codigo_obra,
            "obra": obra.nombre,
            "constructora": obra.constructora.nombre,
            "estado": obra.estado,
            "resumen": resumen,
            "mensaje": "Ficha ambiental verificable de obra generada por Carbono Zero.",
        }
    )


@api_view(["GET", "POST"])
def factores_emision(request):
    if request.method == "GET":
        queryset = FactorEmision.objects.order_by("categoria", "actividad")
        filters = {
            "preset": request.query_params.get("preset"),
            "categoria": request.query_params.get("categoria"),
            "unidad": request.query_params.get("unidad"),
            "module": request.query_params.get("module"),
            "actividad_key": request.query_params.get("actividad_key"),
        }
        for field, value in filters.items():
            if value:
                queryset = queryset.filter(**{field: value})
        activo = request.query_params.get("activo")
        if activo not in (None, ""):
            queryset = queryset.filter(
                activo=str(activo).lower() in {"1", "true", "si", "yes"}
            )
        return Response(FactorEmisionSerializer(queryset, many=True).data)
    serializer = FactorEmisionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    factor = serializer.save()
    return Response(
        FactorEmisionSerializer(factor).data, status=status.HTTP_201_CREATED
    )


@api_view(["GET", "PATCH"])
def factores_emision_detail(request, factor_id):
    factor = get_object_or_404(FactorEmision, pk=factor_id)

    if request.method == "GET":
        return Response(FactorEmisionSerializer(factor).data)

    serializer = FactorEmisionSerializer(factor, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    factor = serializer.save()
    return Response(FactorEmisionSerializer(factor).data)


@api_view(["POST"])
def constructora_registro_aplicar_factor(request, constructora_id, registro_id):
    constructora = get_constructora_or_404(constructora_id)
    registro = get_object_or_404(
        RegistroEmision, pk=registro_id, constructora=constructora
    )
    factor_id = request.data.get("factor_id")
    if not factor_id:
        return Response(
            {"error": "factor_id es obligatorio."}, status=status.HTTP_400_BAD_REQUEST
        )
    factor = get_object_or_404(FactorEmision, pk=factor_id, activo=True)
    metadata = dict(registro.metadata or {})
    metadata["factor_aplicado_id"] = factor.id
    metadata["factor_fuente"] = factor.fuente
    metadata["factor_preset"] = factor.preset
    metadata["factor_module"] = factor.module
    registro.factor_emision = factor.factor_emision
    registro.categoria = map_factor_category_to_registro_category(factor.categoria)
    registro.unidad = registro.unidad or factor.unidad
    registro.metadata = metadata
    registro.save()
    return Response(RegistroEmisionSerializer(registro).data)


def map_factor_category_to_registro_category(category):
    mapping = {
        "Materia prima": RegistroEmision.Categoria.MATERIALES,
        "Produccion": RegistroEmision.Categoria.PROCESOS_EXTERNOS,
        "Secado": RegistroEmision.Categoria.ENERGIA,
        "Combustible": RegistroEmision.Categoria.TRANSPORTE,
        "Rutas": RegistroEmision.Categoria.TRANSPORTE,
        "Flota": RegistroEmision.Categoria.MAQUINARIA,
        "Mantencion": RegistroEmision.Categoria.MAQUINARIA,
        "Carga": RegistroEmision.Categoria.TRANSPORTE,
        "Subproductos": RegistroEmision.Categoria.RESIDUOS,
        "Procesos": RegistroEmision.Categoria.PROCESOS_EXTERNOS,
    }
    return mapping.get(
        category,
        (
            category
            if category in dict(RegistroEmision.Categoria.choices)
            else RegistroEmision.Categoria.OTROS
        ),
    )


@api_view(["GET", "POST"])
def materiales_construccion(request):
    if request.method == "GET":
        return Response(
            MaterialConstruccionSerializer(
                MaterialConstruccion.objects.order_by("nombre"), many=True
            ).data
        )
    serializer = MaterialConstruccionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    material = serializer.save()
    return Response(
        MaterialConstruccionSerializer(material).data, status=status.HTTP_201_CREATED
    )


@api_view(["GET"])
def factores_catalogo(request):
    return Response(
        {
            "categorias": [choice[0] for choice in RegistroEmision.Categoria.choices],
            "unidades_sugeridas": [
                "kg",
                "ton",
                "m3",
                "m2",
                "kWh",
                "litros diesel",
                "horas maquina",
            ],
            "factores": FactorEmisionSerializer(
                FactorEmision.objects.order_by("categoria", "actividad"), many=True
            ).data,
        }
    )


@api_view(["POST"])
def ai_advisor(request):
    payload = request.data or {}
    if generar_analisis_ia:
        try:
            return Response(generar_analisis_ia(payload))
        except Exception:
            pass
    return Response(generar_analisis_local(payload))


@api_view(["POST"])
def calcular_distancia_ruta(request):
    origen = request.data.get("origen") or {}
    destino = request.data.get("destino") or {}
    try:
        lat1 = Decimal(str(origen.get("lat")))
        lon1 = Decimal(str(origen.get("lng")))
        lat2 = Decimal(str(destino.get("lat")))
        lon2 = Decimal(str(destino.get("lng")))
    except Exception:
        return Response(
            {"error": "Ingresa coordenadas de origen y destino."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    distancia = (((lat2 - lat1) ** 2 + (lon2 - lon1) ** 2) ** Decimal("0.5")) * Decimal(
        "111.0"
    )
    return Response(
        {"distancia_km": round(float(distancia), 2), "fuente": "estimacion_geografica"}
    )
