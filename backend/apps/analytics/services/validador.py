from typing import Optional
from django.db import transaction

from ..models import HistorialCambioLote, ExtraccionDocumento
from .carbono import calcular_balance_lote, calcular_carbono_almacenado
from .pasaporte import calcular_pasaporte_lote
from .ocr import aplicar_datos_validados


class ValidadorDatos:
    @staticmethod
    @transaction.atomic
    def validar_extraccion(
        extraccion: ExtraccionDocumento,
        datos_validados: dict,
        usuario: Optional[str] = None,
        aplicar_calculo: bool = True,
    ) -> dict:
        """
        Valida una `ExtraccionDocumento`: guarda datos validados, crea un registro
        de `HistorialCambioLote`, aplica los datos (crea actividades) y recalcula
        resumen/pasaporte del lote.
        Retorna un dict con la extraccion serializada, conteo de actividades creadas
        y el nuevo pasaporte.
        """
        lote = extraccion.documento.lote

        # Aplica datos validados en el sistema (crea/actualiza EmisionLote, TransporteLote, etc.)
        created_activities = aplicar_datos_validados(extraccion, datos_validados) if aplicar_calculo else []

        # Actualiza la extraccion y documento
        extraccion.datos_validados = datos_validados
        extraccion.estado_revision = ExtraccionDocumento.EstadoRevision.VALIDADO
        extraccion.save(update_fields=["datos_validados", "estado_revision", "updated_at"])
        extraccion.documento.estado_validacion = extraccion.documento.EstadoValidacion.VALIDADO
        extraccion.documento.save(update_fields=["estado_validacion", "updated_at"])

        # Crea entrada de historial
        HistorialCambioLote.objects.create(
            lote=lote,
            tipo=HistorialCambioLote.TipoCambio.VALIDADO,
            fuente="manual",
            usuario=usuario or "",
            documento=extraccion.documento,
            extraccion=extraccion,
            raw_payload=extraccion.datos_sugeridos or {},
            normalized_payload=datos_validados or {},
            metadata={"created_activities": len(created_activities)},
        )

        # Recalcular métricas y pasaporte
        carbono = calcular_carbono_almacenado(lote)
        balance = calcular_balance_lote(lote)
        pasaporte = calcular_pasaporte_lote(lote)

        return {
            "extraccion_id": extraccion.pk,
            "actividades_creadas": len(created_activities),
            "carbono": carbono,
            "balance": balance,
            "pasaporte": pasaporte,
        }


__all__ = ["ValidadorDatos"]
