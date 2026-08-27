from datetime import date
from decimal import Decimal

from django.apps import apps
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

import apps.analytics.models as public_models
from apps.analytics.models import (
    ActividadOperacional,
    ActivoOperacional,
    CalculoAmbiental,
    AreaOperacional,
    EspacioTrabajoOperacional,
    EtapaObra,
    EvidenciaObra,
    EventoMaterial,
    EventoAuditoriaSaaS,
    FactorAmbiental,
    FuenteDatos,
    CondicionOperacionalActivo,
    MantenimientoActivo,
    MapeoColumna,
    LoteMaterial,
    MaterialOperacional,
    Maquinaria,
    Organizacion,
    Observacion,
    Obra,
    ProcesoOperacional,
    PuntoAmbientalOperacional,
    PlantillaMapeo,
    ProcesoIngesta,
    RegistroExtraido,
    RegistroFlujoAmbiental,
    RutaOperacional,
    SuscripcionSaaS,
    UsuarioObraAcceso,
    UsuarioOrganizacion,
    UnidadOperacional,
    Vehiculo,
    VersionEvidencia,
    ViajeOperacional,
)

PLATFORM_MODELS = (
    Organizacion,
    SuscripcionSaaS,
    EventoAuditoriaSaaS,
    UsuarioOrganizacion,
    UsuarioObraAcceso,
)

EXPECTED_TABLES = {
    Organizacion: "analytics_organizacion",
    SuscripcionSaaS: "analytics_suscripcionsaas",
    EventoAuditoriaSaaS: "analytics_eventoauditoriasaas",
    UsuarioOrganizacion: "analytics_usuarioorganizacion",
    UsuarioObraAcceso: "analytics_usuarioobraacceso",
}

OPERATIONAL_CONTEXT_MODELS = (
    EtapaObra,
    Obra,
    AreaOperacional,
    EspacioTrabajoOperacional,
    UnidadOperacional,
    ProcesoOperacional,
)

OPERATIONAL_CONTEXT_TABLES = {
    EtapaObra: "analytics_etapaobra",
    Obra: "analytics_obra",
    AreaOperacional: "analytics_areaoperacional",
    EspacioTrabajoOperacional: "analytics_espaciotrabajooperacional",
    UnidadOperacional: "analytics_unidadoperacional",
    ProcesoOperacional: "analytics_procesooperacional",
}

ASSET_MODELS = (
    ActivoOperacional,
    Vehiculo,
    Maquinaria,
    MantenimientoActivo,
    CondicionOperacionalActivo,
    PuntoAmbientalOperacional,
)

ASSET_TABLES = {
    ActivoOperacional: "analytics_activooperacional",
    Vehiculo: "analytics_vehiculo",
    Maquinaria: "analytics_maquinaria",
    MantenimientoActivo: "analytics_mantenimientoactivo",
    CondicionOperacionalActivo: "analytics_condicionoperacionalactivo",
    PuntoAmbientalOperacional: "analytics_puntoambientaloperacional",
}

OPERATIONAL_DATA_MODELS = (
    FuenteDatos,
    ActividadOperacional,
    Observacion,
)

OPERATIONAL_DATA_TABLES = {
    FuenteDatos: "analytics_fuentedatos",
    ActividadOperacional: "analytics_actividadoperacional",
    Observacion: "analytics_observacion",
}

TRANSPORT_MODELS = (RutaOperacional, ViajeOperacional)
TRANSPORT_TABLES = {
    RutaOperacional: "analytics_rutaoperacional",
    ViajeOperacional: "analytics_viajeoperacional",
}

MATERIAL_MODELS = (MaterialOperacional, LoteMaterial, EventoMaterial)
MATERIAL_TABLES = {
    MaterialOperacional: "analytics_materialoperacional",
    LoteMaterial: "analytics_lotematerial",
    EventoMaterial: "analytics_eventomaterial",
}

PROVENANCE_MODELS = (EvidenciaObra, VersionEvidencia)
PROVENANCE_TABLES = {
    EvidenciaObra: "analytics_evidenciaobra",
    VersionEvidencia: "analytics_versionevidencia",
}

INGESTION_MODELS = (PlantillaMapeo, MapeoColumna, ProcesoIngesta, RegistroExtraido)
INGESTION_TABLES = {
    PlantillaMapeo: "analytics_plantillamapeo",
    MapeoColumna: "analytics_mapeocolumna",
    ProcesoIngesta: "analytics_procesoingesta",
    RegistroExtraido: "analytics_registroextraido",
}


class ModelModularizationContractTests(SimpleTestCase):
    def test_platform_models_live_in_platform_module(self):
        for model in PLATFORM_MODELS:
            with self.subTest(model=model.__name__):
                self.assertEqual(model.__module__, "apps.analytics.models.platform")

    def test_platform_models_keep_app_label_and_database_table(self):
        for model in PLATFORM_MODELS:
            with self.subTest(model=model.__name__):
                self.assertEqual(model._meta.app_label, "analytics")
                self.assertEqual(model._meta.db_table, EXPECTED_TABLES[model])

    def test_public_models_api_reexports_platform_models(self):
        for model in PLATFORM_MODELS:
            with self.subTest(model=model.__name__):
                self.assertIs(getattr(public_models, model.__name__), model)

    def test_public_models_api_still_exports_unmoved_models(self):
        for model in (
            ActividadOperacional,
            RegistroFlujoAmbiental,
            FactorAmbiental,
            CalculoAmbiental,
        ):
            with self.subTest(model=model.__name__):
                self.assertIs(getattr(public_models, model.__name__), model)

    def test_operational_context_models_live_in_owner_module(self):
        for model in OPERATIONAL_CONTEXT_MODELS:
            with self.subTest(model=model.__name__):
                self.assertEqual(
                    model.__module__, "apps.analytics.models.operational_context"
                )

    def test_operational_context_models_keep_app_label_and_database_table(self):
        for model in OPERATIONAL_CONTEXT_MODELS:
            with self.subTest(model=model.__name__):
                self.assertEqual(model._meta.app_label, "analytics")
                self.assertEqual(
                    model._meta.db_table, OPERATIONAL_CONTEXT_TABLES[model]
                )

    def test_public_api_and_registry_share_operational_context_model_identity(self):
        for model in OPERATIONAL_CONTEXT_MODELS:
            with self.subTest(model=model.__name__):
                self.assertIs(getattr(public_models, model.__name__), model)
                self.assertIs(apps.get_model("analytics", model.__name__), model)

    def test_asset_models_live_in_owner_module(self):
        for model in ASSET_MODELS:
            with self.subTest(model=model.__name__):
                self.assertEqual(model.__module__, "apps.analytics.models.assets")

    def test_asset_models_keep_app_label_and_database_table(self):
        for model in ASSET_MODELS:
            with self.subTest(model=model.__name__):
                self.assertEqual(model._meta.app_label, "analytics")
                self.assertEqual(model._meta.db_table, ASSET_TABLES[model])

    def test_public_api_and_registry_share_asset_model_identity(self):
        for model in ASSET_MODELS:
            with self.subTest(model=model.__name__):
                self.assertIs(getattr(public_models, model.__name__), model)
                self.assertIs(apps.get_model("analytics", model.__name__), model)

    def test_operational_data_models_live_in_owner_module(self):
        for model in OPERATIONAL_DATA_MODELS:
            with self.subTest(model=model.__name__):
                self.assertEqual(
                    model.__module__, "apps.analytics.models.operational_data"
                )

    def test_operational_data_models_keep_app_label_and_database_table(self):
        for model in OPERATIONAL_DATA_MODELS:
            with self.subTest(model=model.__name__):
                self.assertEqual(model._meta.app_label, "analytics")
                self.assertEqual(model._meta.db_table, OPERATIONAL_DATA_TABLES[model])

    def test_public_api_and_registry_share_operational_data_model_identity(self):
        for model in OPERATIONAL_DATA_MODELS:
            with self.subTest(model=model.__name__):
                self.assertIs(getattr(public_models, model.__name__), model)
                self.assertIs(apps.get_model("analytics", model.__name__), model)

    def test_transport_models_live_in_owner_module_and_keep_contract(self):
        for model in TRANSPORT_MODELS:
            with self.subTest(model=model.__name__):
                self.assertEqual(model.__module__, "apps.analytics.models.transport")
                self.assertEqual(model._meta.app_label, "analytics")
                self.assertEqual(model._meta.db_table, TRANSPORT_TABLES[model])
                self.assertIs(getattr(public_models, model.__name__), model)
                self.assertIs(apps.get_model("analytics", model.__name__), model)

    def test_material_models_live_in_owner_module_and_keep_contract(self):
        for model in MATERIAL_MODELS:
            with self.subTest(model=model.__name__):
                self.assertEqual(model.__module__, "apps.analytics.models.materials")
                self.assertEqual(model._meta.app_label, "analytics")
                self.assertEqual(model._meta.db_table, MATERIAL_TABLES[model])
                self.assertIs(getattr(public_models, model.__name__), model)
                self.assertIs(apps.get_model("analytics", model.__name__), model)

    def test_provenance_models_live_in_owner_module_and_keep_contract(self):
        for model in PROVENANCE_MODELS:
            with self.subTest(model=model.__name__):
                self.assertEqual(model.__module__, "apps.analytics.models.provenance")
                self.assertEqual(model._meta.app_label, "analytics")
                self.assertEqual(model._meta.db_table, PROVENANCE_TABLES[model])
                self.assertIs(getattr(public_models, model.__name__), model)
                self.assertIs(apps.get_model("analytics", model.__name__), model)

    def test_ingestion_models_live_in_owner_module_and_keep_contract(self):
        for model in INGESTION_MODELS:
            with self.subTest(model=model.__name__):
                self.assertEqual(model.__module__, "apps.analytics.models.ingestion")
                self.assertEqual(model._meta.app_label, "analytics")
                self.assertEqual(model._meta.db_table, INGESTION_TABLES[model])
                self.assertIs(getattr(public_models, model.__name__), model)
                self.assertIs(apps.get_model("analytics", model.__name__), model)

    def test_provenance_and_ingestion_relations_keep_their_targets(self):
        expected = {
            (EvidenciaObra, "organizacion"): Organizacion,
            (EvidenciaObra, "area_origen"): AreaOperacional,
            (EvidenciaObra, "usuario_origen"): User,
            (EvidenciaObra, "obra"): Obra,
            (EvidenciaObra, "etapa"): EtapaObra,
            (VersionEvidencia, "evidencia"): EvidenciaObra,
            (VersionEvidencia, "organizacion"): Organizacion,
            (PlantillaMapeo, "organizacion"): Organizacion,
            (PlantillaMapeo, "fuente_datos"): FuenteDatos,
            (MapeoColumna, "plantilla"): PlantillaMapeo,
            (ProcesoIngesta, "version_evidencia"): VersionEvidencia,
            (ProcesoIngesta, "fuente_datos"): FuenteDatos,
            (ProcesoIngesta, "plantilla_mapeo"): PlantillaMapeo,
            (RegistroExtraido, "proceso_ingesta"): ProcesoIngesta,
            (RegistroExtraido, "actividad_creada"): ActividadOperacional,
        }
        for (model, field_name), target in expected.items():
            with self.subTest(model=model.__name__, field=field_name):
                self.assertIs(
                    model._meta.get_field(field_name).remote_field.model, target
                )

        constraint_names = {item.name for item in VersionEvidencia._meta.constraints}
        self.assertIn("unique_version_evidencia", constraint_names)

    def test_transport_and_material_relations_keep_their_targets(self):
        expected = {
            (ViajeOperacional, "organizacion"): Organizacion,
            (ViajeOperacional, "actividad"): ActividadOperacional,
            (ViajeOperacional, "vehiculo"): Vehiculo,
            (ViajeOperacional, "ruta"): RutaOperacional,
            (MaterialOperacional, "organizacion"): Organizacion,
            (LoteMaterial, "material"): MaterialOperacional,
            (LoteMaterial, "fuente"): FuenteDatos,
            (EventoMaterial, "material"): MaterialOperacional,
            (EventoMaterial, "lote"): LoteMaterial,
            (EventoMaterial, "actividad"): ActividadOperacional,
            (EventoMaterial, "obra"): Obra,
            (EventoMaterial, "proceso"): ProcesoOperacional,
        }
        for (model, field_name), target in expected.items():
            with self.subTest(model=model.__name__, field=field_name):
                self.assertIs(
                    model._meta.get_field(field_name).remote_field.model, target
                )

    def test_operational_data_relations_resolve_to_expected_models(self):
        expected = {
            (ActividadOperacional, "organizacion"): Organizacion,
            (ActividadOperacional, "obra"): Obra,
            (ActividadOperacional, "unidad_operacional"): UnidadOperacional,
            (ActividadOperacional, "proceso_operacional"): ProcesoOperacional,
            (ActividadOperacional, "activos"): ActivoOperacional,
            (Observacion, "organizacion"): Organizacion,
            (Observacion, "actividad"): ActividadOperacional,
            (Observacion, "fuente"): FuenteDatos,
            (Observacion, "actor"): User,
            (FuenteDatos, "organizacion"): Organizacion,
        }
        for (model, field_name), related_model in expected.items():
            with self.subTest(model=model.__name__, field=field_name):
                self.assertIs(
                    model._meta.get_field(field_name).remote_field.model,
                    related_model,
                )

        for field_name, label in (
            ("evidencia", "analytics.EvidenciaObra"),
            ("version_evidencia", "analytics.VersionEvidencia"),
            ("registro_extraido", "analytics.RegistroExtraido"),
        ):
            with self.subTest(model="Observacion", field=field_name):
                self.assertEqual(
                    Observacion._meta.get_field(
                        field_name
                    ).remote_field.model._meta.label,
                    label,
                )

    def test_analytics_registry_contains_no_duplicate_model_labels(self):
        registered = [
            model for model in apps.get_models() if model._meta.app_label == "analytics"
        ]
        labels = [model._meta.label_lower for model in registered]
        self.assertEqual(len(labels), len(set(labels)))

    def test_critical_platform_relations_resolve_to_original_models(self):
        self.assertIs(
            UsuarioOrganizacion._meta.get_field("organizacion").remote_field.model,
            Organizacion,
        )
        self.assertIs(
            UsuarioObraAcceso._meta.get_field(
                "usuario_organizacion"
            ).remote_field.model,
            UsuarioOrganizacion,
        )
        self.assertEqual(
            UsuarioObraAcceso._meta.get_field("obra").remote_field.model._meta.label,
            "analytics.Obra",
        )


class ModelModularizationPersistenceTests(TestCase):
    def create_asset_context(self, suffix=""):
        organization = Organizacion.objects.create(nombre=f"Assets {suffix}")
        unit = UnidadOperacional.objects.create(
            organizacion=organization,
            nombre=f"Unidad {suffix}",
        )
        process = ProcesoOperacional.objects.create(
            organizacion=organization,
            unidad=unit,
            nombre=f"Proceso {suffix}",
        )
        work = Obra.objects.create(
            organizacion=organization,
            nombre=f"Obra {suffix}",
            fecha_inicio=date(2026, 8, 26),
        )
        asset = ActivoOperacional(
            organizacion=organization,
            unidad_operacional=unit,
            proceso_operacional=process,
            codigo=f"ACT-{suffix}",
            nombre=f"Activo {suffix}",
        )
        asset.full_clean()
        asset.save()
        return organization, unit, process, work, asset

    def test_organization_and_membership_can_still_be_created(self):
        user = User.objects.create_user(username="platform-member")
        organization = Organizacion.objects.create(nombre="Organización Platform")
        membership = UsuarioOrganizacion.objects.create(
            user=user,
            organizacion=organization,
            rol=UsuarioOrganizacion.Rol.ADMIN,
        )

        self.assertEqual(organization.organizacion_id, "ORGANIZACION_PLATFORM")
        self.assertEqual(membership.organizacion, organization)
        self.assertEqual(membership.user, user)

    def test_organization_work_and_area_can_still_be_created(self):
        organization = Organizacion.objects.create(nombre="Contexto Operacional")
        stage = EtapaObra.objects.create(
            organizacion=organization,
            nombre="Obra gruesa",
        )
        work = Obra.objects.create(
            organizacion=organization,
            etapa_principal=stage,
            nombre="Edificio Central",
            fecha_inicio=date(2026, 8, 26),
        )
        area = AreaOperacional.objects.create(
            organizacion=organization,
            nombre="Bodega",
            tipo=AreaOperacional.Tipo.BODEGA,
        )

        self.assertEqual(work.organizacion, organization)
        self.assertEqual(work.etapa_principal, stage)
        self.assertEqual(area.organizacion, organization)

    def test_operational_unit_and_process_can_still_be_created(self):
        organization = Organizacion.objects.create(nombre="Procesos Operacionales")
        unit = UnidadOperacional.objects.create(
            organizacion=organization,
            nombre="Faena principal",
            tipo=UnidadOperacional.Tipo.FAENA,
        )
        process = ProcesoOperacional.objects.create(
            organizacion=organization,
            unidad=unit,
            nombre="Movimiento de tierra",
        )

        self.assertEqual(process.organizacion, organization)
        self.assertEqual(process.unidad, unit)

    def test_membership_area_and_work_create_valid_workspace(self):
        user = User.objects.create_user(username="workspace-member")
        organization = Organizacion.objects.create(nombre="Workspace Válido")
        membership = UsuarioOrganizacion.objects.create(
            user=user,
            organizacion=organization,
        )
        area = AreaOperacional.objects.create(
            organizacion=organization,
            nombre="Operaciones",
        )
        work = Obra.objects.create(
            organizacion=organization,
            nombre="Obra Workspace",
            fecha_inicio=date(2026, 8, 26),
        )
        workspace = EspacioTrabajoOperacional(
            usuario_organizacion=membership,
            area=area,
            obra=work,
        )

        workspace.full_clean()
        workspace.save()

        self.assertEqual(workspace.usuario_organizacion, membership)
        self.assertEqual(workspace.area, area)
        self.assertEqual(workspace.obra, work)

    def test_workspace_still_rejects_cross_tenant_area_and_work(self):
        user = User.objects.create_user(username="cross-tenant-member")
        organization = Organizacion.objects.create(nombre="Tenant Uno")
        other_organization = Organizacion.objects.create(nombre="Tenant Dos")
        membership = UsuarioOrganizacion.objects.create(
            user=user,
            organizacion=organization,
        )
        foreign_area = AreaOperacional.objects.create(
            organizacion=other_organization,
            nombre="Área externa",
        )
        foreign_work = Obra.objects.create(
            organizacion=other_organization,
            nombre="Obra externa",
            fecha_inicio=date(2026, 8, 26),
        )
        workspace = EspacioTrabajoOperacional(
            usuario_organizacion=membership,
            area=foreign_area,
            obra=foreign_work,
        )

        with self.assertRaises(ValidationError) as context:
            workspace.full_clean()

        self.assertIn("area", context.exception.message_dict)

    def test_operational_asset_and_point_can_still_be_created(self):
        organization, unit, process, work, asset = self.create_asset_context("POINT")
        point = PuntoAmbientalOperacional.objects.create(
            organizacion=organization,
            codigo="PTO-POINT",
            nombre="Punto de medición",
            activo=asset,
            unidad_operacional=unit,
            proceso_operacional=process,
            obra=work,
        )

        self.assertEqual(point.activo, asset)
        self.assertEqual(point.obra, work)

    def test_vehicle_and_machinery_can_still_be_created(self):
        _, _, _, _, vehicle_asset = self.create_asset_context("VEHICLE")
        _, _, _, _, machine_asset = self.create_asset_context("MACHINE")
        vehicle = Vehiculo.objects.create(
            activo=vehicle_asset,
            patente="TEST-01",
            combustible="Diesel",
        )
        machinery = Maquinaria.objects.create(
            activo=machine_asset,
            tipo_maquinaria="Excavadora",
            combustible="Diesel",
        )

        self.assertEqual(vehicle.activo, vehicle_asset)
        self.assertEqual(machinery.activo, machine_asset)

    def test_maintenance_and_operational_condition_can_still_be_created(self):
        organization, _, _, _, asset = self.create_asset_context("STATE")
        maintenance = MantenimientoActivo(
            organizacion=organization,
            activo=asset,
            tipo="Preventivo",
        )
        maintenance.full_clean()
        maintenance.save()
        condition = CondicionOperacionalActivo.objects.create(
            activo=asset,
            timestamp_inicio=timezone.now(),
            estado=CondicionOperacionalActivo.Estado.OPERATIVO,
        )

        self.assertEqual(maintenance.activo, asset)
        self.assertEqual(condition.activo, asset)

    def test_asset_still_rejects_cross_tenant_operational_context(self):
        organization = Organizacion.objects.create(nombre="Asset Tenant")
        other_organization = Organizacion.objects.create(nombre="Context Tenant")
        foreign_unit = UnidadOperacional.objects.create(
            organizacion=other_organization,
            nombre="Unidad externa",
        )
        asset = ActivoOperacional(
            organizacion=organization,
            unidad_operacional=foreign_unit,
            codigo="ACT-CROSS",
            nombre="Activo cruzado",
        )

        with self.assertRaises(ValidationError) as context:
            asset.full_clean()

        self.assertIn("unidad_operacional", context.exception.message_dict)

    def test_point_still_rejects_cross_tenant_references(self):
        organization, _, _, _, _ = self.create_asset_context("LOCAL")
        _, _, _, _, foreign_asset = self.create_asset_context("FOREIGN")
        point = PuntoAmbientalOperacional(
            organizacion=organization,
            codigo="PTO-CROSS",
            nombre="Punto cruzado",
            activo=foreign_asset,
        )

        with self.assertRaises(ValidationError) as context:
            point.full_clean()

        self.assertIn("activo", context.exception.message_dict)

    def test_operational_source_activity_and_observations_can_be_created(self):
        organization, unit, process, work, asset = self.create_asset_context("DATA")
        source = FuenteDatos.objects.create(
            organizacion=organization,
            nombre="Registro manual",
        )
        activity = ActividadOperacional(
            organizacion=organization,
            obra=work,
            unidad_operacional=unit,
            proceso_operacional=process,
            codigo="ACT-DATA",
            nombre="Carga de combustible",
            timestamp_inicio=timezone.now(),
        )
        activity.full_clean()
        activity.save()
        activity.activos.add(asset)
        numeric = Observacion(
            organizacion=organization,
            actividad=activity,
            fuente=source,
            concepto="combustible_consumido",
            valor_numerico=Decimal("20.000000"),
            unidad="L",
            timestamp_observacion=timezone.now(),
        )
        numeric.full_clean()
        numeric.save()
        textual = Observacion(
            organizacion=organization,
            actividad=activity,
            fuente=source,
            concepto="estado_registro",
            valor_texto="Confirmado",
            timestamp_observacion=timezone.now(),
        )
        textual.full_clean()
        textual.save()

        self.assertEqual(numeric.actividad, activity)
        self.assertEqual(textual.fuente, source)
        self.assertEqual(list(activity.activos.all()), [asset])

    def test_activity_still_rejects_cross_tenant_context(self):
        organization = Organizacion.objects.create(nombre="Activity Tenant")
        other_organization = Organizacion.objects.create(nombre="Work Tenant")
        foreign_work = Obra.objects.create(
            organizacion=other_organization,
            nombre="Obra externa activity",
            fecha_inicio=date(2026, 8, 26),
        )
        activity = ActividadOperacional(
            organizacion=organization,
            obra=foreign_work,
            codigo="ACT-CROSS-TENANT",
            nombre="Actividad cruzada",
            timestamp_inicio=timezone.now(),
        )

        with self.assertRaises(ValidationError) as context:
            activity.full_clean()

        self.assertIn("obra", context.exception.message_dict)

    def test_observation_still_rejects_cross_tenant_source(self):
        organization = Organizacion.objects.create(nombre="Observation Tenant")
        other_organization = Organizacion.objects.create(nombre="Source Tenant")
        foreign_source = FuenteDatos.objects.create(
            organizacion=other_organization,
            nombre="Fuente externa",
        )
        observation = Observacion(
            organizacion=organization,
            fuente=foreign_source,
            concepto="dato_cruzado",
            valor_texto="Dato",
            timestamp_observacion=timezone.now(),
        )

        with self.assertRaises(ValidationError) as context:
            observation.full_clean()

        self.assertIn("fuente", context.exception.message_dict)

    def test_route_and_trip_can_still_be_created(self):
        organization, _, _, work, asset = self.create_asset_context("TRIP")
        vehicle = Vehiculo.objects.create(activo=asset, patente="ARQ-02F")
        activity = ActividadOperacional.objects.create(
            organizacion=organization,
            obra=work,
            tipo=ActividadOperacional.Tipo.TRANSPORTE,
            codigo="ACT-TRIP",
            nombre="Viaje de prueba",
            timestamp_inicio=timezone.now(),
        )
        route = RutaOperacional.objects.create(
            organizacion=organization,
            codigo="ROUTE-02F",
            origen_nombre="Origen",
            destino_nombre="Destino",
        )
        trip = ViajeOperacional.objects.create(
            organizacion=organization,
            actividad=activity,
            codigo="TRIP-02F",
            vehiculo=vehicle,
            ruta=route,
            origen_nombre="Origen",
            destino_nombre="Destino",
            fecha_salida=timezone.now(),
        )

        self.assertEqual(trip.ruta, route)
        self.assertEqual(trip.vehiculo, vehicle)
        self.assertEqual(trip.actividad, activity)

    def test_material_lot_and_event_can_still_be_created(self):
        organization, _, process, work, _ = self.create_asset_context("MATERIAL")
        source = FuenteDatos.objects.create(
            organizacion=organization,
            nombre="Fuente material",
        )
        material = MaterialOperacional.objects.create(
            organizacion=organization,
            codigo="MAT-02F",
            nombre="Material de prueba",
            categoria="prueba",
            unidad_base="kg",
        )
        lot = LoteMaterial.objects.create(
            organizacion=organization,
            material=material,
            codigo="LOT-02F",
            fuente=source,
        )
        activity = ActividadOperacional.objects.create(
            organizacion=organization,
            obra=work,
            proceso_operacional=process,
            tipo=ActividadOperacional.Tipo.MOVIMIENTO_MATERIAL,
            codigo="ACT-MAT-02F",
            nombre="Recepción de material",
            timestamp_inicio=timezone.now(),
        )
        event = EventoMaterial.objects.create(
            organizacion=organization,
            material=material,
            lote=lot,
            actividad=activity,
            tipo=EventoMaterial.Tipo.RECEPCION,
            fecha_hora=timezone.now(),
            obra=work,
            proceso=process,
            fuente=source,
        )

        self.assertEqual(event.material, material)
        self.assertEqual(event.lote, lot)
        self.assertEqual(event.actividad, activity)

    def create_provenance_context(self, suffix=""):
        organization = Organizacion.objects.create(nombre=f"Provenance {suffix}")
        work = Obra.objects.create(
            organizacion=organization,
            nombre=f"Obra provenance {suffix}",
            fecha_inicio=date(2026, 8, 27),
        )
        evidence = EvidenciaObra.objects.create(
            organizacion=organization,
            obra=work,
            nombre=f"Evidencia {suffix}",
            archivo=f"evidencias/test/{suffix}.pdf",
        )
        version = VersionEvidencia.objects.create(
            evidencia=evidence,
            organizacion=organization,
            version=1,
            archivo=f"evidencias/test/{suffix}-v1.pdf",
            nombre_original=f"{suffix}.pdf",
            checksum_sha256=(suffix.lower() or "a").ljust(64, "0")[:64],
        )
        return organization, work, evidence, version

    def test_evidence_and_version_can_still_be_created(self):
        organization, work, evidence, version = self.create_provenance_context("VALID")

        self.assertEqual(evidence.organizacion, organization)
        self.assertEqual(evidence.obra, work)
        self.assertEqual(version.evidencia, evidence)

    def test_evidence_version_still_rejects_cross_tenant_organization(self):
        _, _, evidence, _ = self.create_provenance_context("OWNER")
        other = Organizacion.objects.create(nombre="Foreign provenance tenant")
        version = VersionEvidencia(
            evidencia=evidence,
            organizacion=other,
            version=2,
            archivo="evidencias/test/foreign.pdf",
            nombre_original="foreign.pdf",
            checksum_sha256="f" * 64,
        )

        with self.assertRaises(ValidationError) as context:
            version.full_clean()

        self.assertIn("organizacion", context.exception.message_dict)

    def test_ingestion_entities_can_still_be_created(self):
        organization, _, _, version = self.create_provenance_context("INGESTION")
        source = FuenteDatos.objects.create(
            organizacion=organization,
            nombre="Archivo tabular",
        )
        template = PlantillaMapeo.objects.create(
            organizacion=organization,
            fuente_datos=source,
            nombre="Plantilla ARQ-02G",
        )
        mapping = MapeoColumna.objects.create(
            plantilla=template,
            columna_origen="Cantidad",
            columna_normalizada="cantidad",
            concepto_normalizado="cantidad_material",
            unidad_esperada="kg",
        )
        ingestion = ProcesoIngesta.objects.create(
            organizacion=organization,
            version_evidencia=version,
            fuente_datos=source,
            plantilla_mapeo=template,
            tipo_ingesta=ProcesoIngesta.TipoIngesta.TABULAR,
        )
        record = RegistroExtraido.objects.create(
            proceso_ingesta=ingestion,
            numero_fila=1,
            datos_originales={"Cantidad": "12"},
        )

        self.assertEqual(mapping.plantilla, template)
        self.assertEqual(ingestion.version_evidencia, version)
        self.assertEqual(record.proceso_ingesta, ingestion)

    def test_processed_raw_record_remains_immutable(self):
        organization, _, _, version = self.create_provenance_context("IMMUTABLE")
        source = FuenteDatos.objects.create(
            organizacion=organization,
            nombre="Fuente inmutable",
        )
        ingestion = ProcesoIngesta.objects.create(
            organizacion=organization,
            version_evidencia=version,
            fuente_datos=source,
        )
        record = RegistroExtraido.objects.create(
            proceso_ingesta=ingestion,
            numero_fila=1,
            datos_originales={"valor": "original"},
            estado=RegistroExtraido.Estado.PROCESADO,
        )
        record.datos_originales = {"valor": "alterado"}

        with self.assertRaises(ValidationError):
            record.save()
