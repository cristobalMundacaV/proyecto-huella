from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from apps.iot.models import DispositivoSensor

from ..models import (ActividadOperacional, ActivoOperacional, EvidenciaObra,
                      IndicadorAmbiental, MemoriaOrganizacion,
                      ProblematicaAmbiental, RestriccionContextual)
from .comparison_v2 import compare_values
from .environmental_context import evidence_summary
from .knowledge_v1 import compact_knowledge
from .materials_v2 import material_balance
from .sector_flows_v1 import record_summary
from .transport_v2 import journey_metrics


class ContextGateway:
    MAX_HISTORY = 10
    MAX_SERIES = 12
    MAX_MEMORY = 20

    @staticmethod
    def _tenant(instance, organization):
        owner_id = getattr(instance, "organizacion_id", None)
        if owner_id != organization.id:
            raise ValidationError("La referencia no pertenece a la organizacion.")

    def problem(self, problem, organization):
        self._tenant(problem, organization)
        evidence = evidence_summary(problem)
        evidence.pop("contenido_excluido", None)
        indicators = []
        for link in problem.indicadores_v2.select_related("indicador"):
            values = list(link.indicador.valores.order_by("-periodo_fin", "-version")[:2])
            comparison = compare_values(link.indicador, values[0].valor, values[1].valor) if len(values) > 1 else {"estado": "sin_base"}
            indicators.append({"id": link.indicador_id, "codigo": link.indicador.codigo, "rol": link.rol, "direccion": link.direccion_deseada, "meta": link.valor_objetivo, "actual": values[0].valor if values else None, "comparacion": comparison})
        cycles = problem.ciclos_reevaluacion.select_related("accion", "resultado").order_by("-numero")[:3]
        restrictions = self._active_restrictions(organization, problem)
        return {
            "context_type": "problem", "references": {"organization": organization.organizacion_id, "problem": problem.id},
            "problematica": {"titulo": problem.titulo, "descripcion": problem.descripcion[:500], "categoria": problem.categoria, "estado": problem.estado, "severidad": problem.nivel_riesgo, "objetivo": problem.objetivo_ambiental},
            "alcance": [{"unidad": row.unidad_operacional_id, "proceso": row.proceso_operacional_id, "activo": row.activo_operacional_id, "actividad": row.actividad_operacional_id, "indicador": row.indicador_id} for row in problem.alcances_v2.all()[:20]],
            "kpis": indicators,
            "ciclos": [{"numero": row.numero, "accion": row.accion.titulo, "fecha_inicio": row.fecha_inicio, "fecha_cierre": row.fecha_cierre, "resultado": row.resultado.estado if row.resultado_id else None, "metricas": row.resultado.metricas_comparadas if row.resultado_id else []} for row in cycles],
            "acciones_probadas": [{"id": row.id, "titulo": row.titulo, "estado": row.estado, "justificacion": row.justificacion[:300]} for row in problem.acciones.order_by("-created_at")[:self.MAX_HISTORY]],
            "restricciones": restrictions,
            "evidencia": evidence,
            "historial_resumido": [{"evento": row.evento, "estado": row.estado_nuevo, "detalle": row.detalle[:200], "fecha": row.created_at} for row in problem.historial.order_by("-created_at")[:self.MAX_HISTORY]],
            "conocimiento_comparable": compact_knowledge(problem),
        }

    def work(self, work, organization):
        self._tenant(work, organization)
        from .construction_v1 import work_context
        return work_context(work)

    def organization_memory(self, organization):
        now = timezone.now()
        rows = MemoriaOrganizacion.objects.filter(organizacion=organization, vigente_desde__lte=now).filter(Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gte=now))
        return {
            "context_type": "organization_memory", "references": {"organization": organization.organizacion_id},
            "items": [{"id": row.id, "tipo": row.tipo, "contenido": row.contenido, "fuente": row.fuente_origen, "problematica": row.problematica_id, "vigente_hasta": row.vigente_hasta} for row in rows.order_by("-created_at")[:self.MAX_MEMORY]],
            "restricciones": self._active_restrictions(organization), "limit": self.MAX_MEMORY,
        }

    def asset(self, asset, organization):
        self._tenant(asset, organization)
        return {"context_type": "asset", "references": {"organization": organization.organizacion_id, "asset": asset.id}, "activo": {"codigo": asset.codigo, "nombre": asset.nombre, "tipo": asset.tipo, "estado": asset.estado, "unidad": asset.unidad_operacional_id, "proceso": asset.proceso_operacional_id}, "condiciones_recientes": list(asset.condiciones.values("estado", "timestamp_inicio", "timestamp_fin").order_by("-timestamp_inicio")[:self.MAX_HISTORY])}

    def asset_maintenance(self, asset, organization):
        package = self.asset(asset, organization)
        package["context_type"] = "asset_maintenance"
        package["mantenimientos"] = list(asset.mantenimientos.values("id", "tipo", "estado", "fecha_programada", "fecha_realizada", "descripcion").order_by("-created_at")[:self.MAX_HISTORY])
        return package

    def sensor_health(self, sensor, organization):
        self._tenant(sensor, organization)
        calibration = sensor.calibraciones.order_by("-fecha").first()
        asset = sensor.activo_operacional
        return {"context_type": "sensor_health", "references": {"organization": organization.organizacion_id, "sensor": sensor.id}, "sensor": {"nombre": sensor.nombre, "tipo": sensor.tipo_sensor, "estado": sensor.estado, "habilitado": sensor.activo, "activo_id": sensor.activo_operacional_id, "activo": ({"id": asset.id, "codigo": asset.codigo, "nombre": asset.nombre, "estado": asset.estado} if asset else None), "last_seen_at": sensor.last_seen_at}, "ultima_calibracion": {"fecha": calibration.fecha, "resultado": calibration.resultado, "proxima": calibration.fecha_proxima_calibracion} if calibration else None, "lecturas_recientes": list(sensor.lecturas_v2.values("timestamp", "concepto", "unidad", "calidad_tecnica").order_by("-timestamp")[:self.MAX_HISTORY])}

    def indicator_history(self, indicator, organization):
        self._tenant(indicator, organization)
        return {"context_type": "indicator_history", "references": {"organization": organization.organizacion_id, "indicator": indicator.id}, "indicador": {"codigo": indicator.codigo, "nombre": indicator.nombre, "tipo": indicator.tipo, "unidad": indicator.unidad, "direccion": indicator.direccion_deseable}, "serie": list(indicator.valores.values("id", "periodo_inicio", "periodo_fin", "valor", "version").order_by("-periodo_fin", "-version")[:self.MAX_SERIES]), "limit": self.MAX_SERIES}

    def evidence(self, evidence, organization):
        self._tenant(evidence, organization)
        versions = evidence.versiones.values("id", "version", "nombre_original", "checksum_sha256", "created_at").order_by("-version")[:5]
        return {"context_type": "evidence", "references": {"organization": organization.organizacion_id, "evidence": evidence.id}, "evidencia": {"nombre": evidence.nombre, "tipo": evidence.tipo_evidencia, "estado": evidence.estado_documental, "fecha_documento": evidence.fecha_documento}, "versiones": list(versions), "contenido_excluido": ["archivo", "texto_extraido", "metadata_extraccion"]}

    def activity(self, activity, organization):
        self._tenant(activity, organization)
        package = {"context_type": "activity", "references": {"organization": organization.organizacion_id, "activity": activity.id}, "actividad": {"codigo": activity.codigo, "nombre": activity.nombre, "tipo": activity.tipo, "estado": activity.estado, "inicio": activity.timestamp_inicio}, "observaciones": list(activity.observaciones.values("id", "concepto", "valor_numerico", "unidad", "fuente__tipo", "estado").order_by("-timestamp_observacion")[:20])}
        journey = getattr(activity, "viaje", None)
        if journey:
            package["transporte"] = {"trayecto": journey.tipo_trayecto, "gestion": journey.tipo_gestion, "estado_carga": journey.estado_carga, "origen": journey.origen_nombre, "destino": journey.destino_nombre, "metricas": journey_metrics(journey), "metodologia_tercerizado": journey.metodologia_tercerizado}
        material_event = getattr(activity, "evento_material", None)
        if material_event:
            observation = material_event.observacion_cantidad
            package["material"] = {
                "id": material_event.material_id,
                "codigo": material_event.material.codigo,
                "nombre": material_event.material.nombre,
                "tipo_evento": material_event.tipo,
                "lote_id": material_event.lote_id,
                "obra_id": material_event.obra_id,
                "cantidad": observation.valor_numerico if observation else None,
                "unidad": observation.unidad if observation else None,
                "balance": material_balance(organization, material_event.material, lot=material_event.lote),
            }
        sector_record = getattr(activity, "registro_flujo_ambiental", None)
        if sector_record:
            package["flujo_ambiental"] = record_summary(sector_record)
        return package

    def intervention(self, problem, organization):
        self._tenant(problem, organization)
        return {"context_type": "intervention", "references": {"organization": organization.organizacion_id, "problem": problem.id}, "ciclos": [{"numero": cycle.numero, "accion": cycle.accion_id, "base": cycle.snapshot_base_id, "resultado_snapshot": cycle.snapshot_resultado_id, "resultado": cycle.resultado.estado if cycle.resultado_id else None} for cycle in problem.ciclos_reevaluacion.select_related("resultado").order_by("-numero")[:3]]}

    @staticmethod
    def _active_restrictions(organization, problem=None):
        now = timezone.now()
        rows = RestriccionContextual.objects.filter(organizacion=organization, activa=True, vigente_desde__lte=now).filter(Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gte=now))
        if problem:
            rows = rows.filter(Q(problematica__isnull=True) | Q(problematica=problem))
        return [{"id": row.id, "tipo": row.tipo, "descripcion": row.descripcion, "contenido": row.contenido, "vigente_hasta": row.vigente_hasta} for row in rows.order_by("-created_at")[:20]]
