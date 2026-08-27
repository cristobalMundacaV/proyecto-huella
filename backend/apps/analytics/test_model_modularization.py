from datetime import date
from decimal import Decimal

from django.apps import apps
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

import apps.analytics.models as public_models
from apps.analytics.models import (
    AccionMejoraAmbiental,
    ActividadOperacional,
    ActivoOperacional,
    AlcanceProblematica,
    CalculoAmbiental,
    CasoConocimientoAmbiental,
    CicloReevaluacionProblematica,
    ComandoCopiloto,
    CompatibilidadVersionMetodologia,
    AreaOperacional,
    EspacioTrabajoOperacional,
    EtapaObra,
    EvidenciaObra,
    EventoMaterial,
    EventoAuditoriaSaaS,
    EvaluacionCalidadDato,
    FactorAmbiental,
    FormulaAmbiental,
    FuenteDatos,
    HistorialMetaProblematica,
    HistorialProblematicaAmbiental,
    HistorialRestriccionContextual,
    HitoDecisionIA,
    IndicadorAmbiental,
    IndicadorProblematica,
    ImpactoAmbiental,
    InputCalculoAmbiental,
    CondicionOperacionalActivo,
    DiscrepanciaDato,
    MantenimientoActivo,
    MapeoColumna,
    LineaBaseAmbiental,
    LoteMaterial,
    MaterialOperacional,
    MedicionSeguimientoAmbiental,
    MemoriaOrganizacion,
    Maquinaria,
    MetodologiaAmbiental,
    Organizacion,
    Observacion,
    Obra,
    ProcesoOperacional,
    PuntoAmbientalOperacional,
    PlantillaMapeo,
    PeriodoComparable,
    PoliticaConfianzaFuente,
    ProcesoIngesta,
    ProblematicaAmbiental,
    RegistroExtraido,
    RegistroFlujoAmbiental,
    RecomendacionAgenteAmbiental,
    RestriccionContextual,
    ResultadoIntervencion,
    RutaOperacional,
    SuscripcionSaaS,
    SnapshotIntervencion,
    SnapshotValorIndicador,
    UsuarioObraAcceso,
    UsuarioOrganizacion,
    UnidadOperacional,
    VariableFormula,
    Vehiculo,
    ValorIndicador,
    VersionEvidencia,
    VersionFactorAmbiental,
    VersionMetodologia,
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

ENVIRONMENTAL_FLOW_MODELS = (RegistroFlujoAmbiental,)
ENVIRONMENTAL_FLOW_TABLES = {
    RegistroFlujoAmbiental: "analytics_registroflujoambiental",
}

QUALITY_MODELS = (EvaluacionCalidadDato, DiscrepanciaDato, PoliticaConfianzaFuente)
QUALITY_TABLES = {
    EvaluacionCalidadDato: "analytics_evaluacioncalidaddato",
    DiscrepanciaDato: "analytics_discrepanciadato",
    PoliticaConfianzaFuente: "analytics_politicaconfianzafuente",
}

INDICATOR_MODELS = (
    IndicadorAmbiental,
    ValorIndicador,
    LineaBaseAmbiental,
    PeriodoComparable,
)
INDICATOR_TABLES = {
    IndicadorAmbiental: "analytics_indicadorambiental",
    ValorIndicador: "analytics_valorindicador",
    LineaBaseAmbiental: "analytics_lineabaseambiental",
    PeriodoComparable: "analytics_periodocomparable",
}

GOVERNANCE_MODELS = (
    MetodologiaAmbiental,
    VersionMetodologia,
    FactorAmbiental,
    VersionFactorAmbiental,
    FormulaAmbiental,
    VariableFormula,
    CompatibilidadVersionMetodologia,
)
GOVERNANCE_TABLES = {
    MetodologiaAmbiental: "analytics_metodologiaambiental",
    VersionMetodologia: "analytics_versionmetodologia",
    FactorAmbiental: "analytics_factorambiental",
    VersionFactorAmbiental: "analytics_versionfactorambiental",
    FormulaAmbiental: "analytics_formulaambiental",
    VariableFormula: "analytics_variableformula",
    CompatibilidadVersionMetodologia: "analytics_compatibilidadversionmetodologia",
}

CALCULATION_MODELS = (CalculoAmbiental, InputCalculoAmbiental, ImpactoAmbiental)
CALCULATION_TABLES = {
    CalculoAmbiental: "analytics_calculoambiental",
    InputCalculoAmbiental: "analytics_inputcalculoambiental",
    ImpactoAmbiental: "analytics_impactoambiental",
}

IMPROVEMENT_MODELS = (
    ProblematicaAmbiental,
    AccionMejoraAmbiental,
    MedicionSeguimientoAmbiental,
    AlcanceProblematica,
    IndicadorProblematica,
    SnapshotIntervencion,
    SnapshotValorIndicador,
    ResultadoIntervencion,
    CicloReevaluacionProblematica,
    HistorialMetaProblematica,
    HistorialProblematicaAmbiental,
)
IMPROVEMENT_TABLES = {
    model: f"analytics_{model.__name__.lower()}" for model in IMPROVEMENT_MODELS
}

INTELLIGENCE_MODELS = (
    RecomendacionAgenteAmbiental,
    MemoriaOrganizacion,
    RestriccionContextual,
    HistorialRestriccionContextual,
    HitoDecisionIA,
    ComandoCopiloto,
    CasoConocimientoAmbiental,
)
INTELLIGENCE_TABLES = {
    model: f"analytics_{model.__name__.lower()}" for model in INTELLIGENCE_MODELS
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

    def test_environmental_flow_model_lives_in_owner_module_and_keeps_contract(self):
        for model in ENVIRONMENTAL_FLOW_MODELS:
            self.assertEqual(
                model.__module__, "apps.analytics.models.environmental_flows"
            )
            self.assertEqual(model._meta.app_label, "analytics")
            self.assertEqual(model._meta.db_table, ENVIRONMENTAL_FLOW_TABLES[model])
            self.assertIs(getattr(public_models, model.__name__), model)
            self.assertIs(apps.get_model("analytics", model.__name__), model)

    def test_quality_models_live_in_owner_module_and_keep_contract(self):
        for model in QUALITY_MODELS:
            with self.subTest(model=model.__name__):
                self.assertEqual(model.__module__, "apps.analytics.models.quality")
                self.assertEqual(model._meta.app_label, "analytics")
                self.assertEqual(model._meta.db_table, QUALITY_TABLES[model])
                self.assertIs(getattr(public_models, model.__name__), model)
                self.assertIs(apps.get_model("analytics", model.__name__), model)

    def test_indicator_models_live_in_owner_module_and_keep_contract(self):
        for model in INDICATOR_MODELS:
            with self.subTest(model=model.__name__):
                self.assertEqual(model.__module__, "apps.analytics.models.indicators")
                self.assertEqual(model._meta.app_label, "analytics")
                self.assertEqual(model._meta.db_table, INDICATOR_TABLES[model])
                self.assertIs(getattr(public_models, model.__name__), model)
                self.assertIs(apps.get_model("analytics", model.__name__), model)

    def test_governance_models_live_in_owner_module_and_keep_contract(self):
        for model in GOVERNANCE_MODELS:
            with self.subTest(model=model.__name__):
                self.assertEqual(model.__module__, "apps.analytics.models.governance")
                self.assertEqual(model._meta.app_label, "analytics")
                self.assertEqual(model._meta.db_table, GOVERNANCE_TABLES[model])
                self.assertIs(getattr(public_models, model.__name__), model)
                self.assertIs(apps.get_model("analytics", model.__name__), model)

    def test_calculation_models_live_in_owner_module_and_keep_contract(self):
        for model in CALCULATION_MODELS:
            with self.subTest(model=model.__name__):
                self.assertEqual(model.__module__, "apps.analytics.models.calculations")
                self.assertEqual(model._meta.app_label, "analytics")
                self.assertEqual(model._meta.db_table, CALCULATION_TABLES[model])
                self.assertIs(getattr(public_models, model.__name__), model)
                self.assertIs(apps.get_model("analytics", model.__name__), model)

    def test_improvement_models_live_in_owner_module_and_keep_contract(self):
        for model in IMPROVEMENT_MODELS:
            with self.subTest(model=model.__name__):
                self.assertEqual(model.__module__, "apps.analytics.models.improvement")
                self.assertEqual(model._meta.app_label, "analytics")
                self.assertEqual(model._meta.db_table, IMPROVEMENT_TABLES[model])
                self.assertIs(getattr(public_models, model.__name__), model)
                self.assertIs(apps.get_model("analytics", model.__name__), model)

    def test_intelligence_models_live_in_owner_module_and_keep_contract(self):
        for model in INTELLIGENCE_MODELS:
            with self.subTest(model=model.__name__):
                self.assertEqual(model.__module__, "apps.analytics.models.intelligence")
                self.assertEqual(model._meta.app_label, "analytics")
                self.assertEqual(model._meta.db_table, INTELLIGENCE_TABLES[model])
                self.assertIs(getattr(public_models, model.__name__), model)
                self.assertIs(apps.get_model("analytics", model.__name__), model)

    def test_intelligence_relations_keep_their_targets(self):
        expected = {
            (RecomendacionAgenteAmbiental, "problematica"): ProblematicaAmbiental,
            (
                RecomendacionAgenteAmbiental,
                "propuesta_anterior",
            ): RecomendacionAgenteAmbiental,
            (MemoriaOrganizacion, "organizacion"): Organizacion,
            (MemoriaOrganizacion, "problematica"): ProblematicaAmbiental,
            (RestriccionContextual, "organizacion"): Organizacion,
            (RestriccionContextual, "problematica"): ProblematicaAmbiental,
            (HistorialRestriccionContextual, "restriccion"): RestriccionContextual,
            (HitoDecisionIA, "propuesta"): RecomendacionAgenteAmbiental,
            (HitoDecisionIA, "problematica"): ProblematicaAmbiental,
            (ComandoCopiloto, "propuesta"): RecomendacionAgenteAmbiental,
            (ComandoCopiloto, "problematica"): ProblematicaAmbiental,
            (CasoConocimientoAmbiental, "organizacion"): Organizacion,
            (CasoConocimientoAmbiental, "resultado_origen"): ResultadoIntervencion,
        }
        for (model, field_name), target in expected.items():
            with self.subTest(model=model.__name__, field=field_name):
                self.assertIs(
                    model._meta.get_field(field_name).remote_field.model, target
                )

    def test_improvement_relations_keep_their_targets(self):
        expected = {
            (ProblematicaAmbiental, "organizacion"): Organizacion,
            (ProblematicaAmbiental, "obra"): Obra,
            (AccionMejoraAmbiental, "problematica"): ProblematicaAmbiental,
            (MedicionSeguimientoAmbiental, "problematica"): ProblematicaAmbiental,
            (MedicionSeguimientoAmbiental, "accion"): AccionMejoraAmbiental,
            (MedicionSeguimientoAmbiental, "indicador_v2"): IndicadorAmbiental,
            (MedicionSeguimientoAmbiental, "valor_indicador"): ValorIndicador,
            (MedicionSeguimientoAmbiental, "evidencia"): EvidenciaObra,
            (AlcanceProblematica, "unidad_operacional"): UnidadOperacional,
            (AlcanceProblematica, "proceso_operacional"): ProcesoOperacional,
            (AlcanceProblematica, "activo_operacional"): ActivoOperacional,
            (AlcanceProblematica, "actividad_operacional"): ActividadOperacional,
            (IndicadorProblematica, "indicador"): IndicadorAmbiental,
            (SnapshotIntervencion, "problematica"): ProblematicaAmbiental,
            (SnapshotIntervencion, "accion"): AccionMejoraAmbiental,
            (SnapshotValorIndicador, "snapshot"): SnapshotIntervencion,
            (ResultadoIntervencion, "snapshot_base"): SnapshotIntervencion,
            (ResultadoIntervencion, "snapshot_resultado"): SnapshotIntervencion,
            (CicloReevaluacionProblematica, "resultado"): ResultadoIntervencion,
            (
                HistorialMetaProblematica,
                "indicador_problematica",
            ): IndicadorProblematica,
            (HistorialProblematicaAmbiental, "problematica"): ProblematicaAmbiental,
        }
        for (model, field_name), target in expected.items():
            with self.subTest(model=model.__name__, field=field_name):
                self.assertIs(
                    model._meta.get_field(field_name).remote_field.model, target
                )

    def test_calculation_relations_still_resolve_governance_models(self):
        expected = {
            "version_metodologia": VersionMetodologia,
            "formula": FormulaAmbiental,
            "version_factor": VersionFactorAmbiental,
        }
        for field_name, target in expected.items():
            with self.subTest(field=field_name):
                self.assertIs(
                    CalculoAmbiental._meta.get_field(field_name).remote_field.model,
                    target,
                )

    def test_calculation_input_and_impact_relations_keep_their_targets(self):
        expected = {
            (CalculoAmbiental, "organizacion"): Organizacion,
            (CalculoAmbiental, "actividad"): ActividadOperacional,
            (CalculoAmbiental, "version_metodologia"): VersionMetodologia,
            (CalculoAmbiental, "formula"): FormulaAmbiental,
            (CalculoAmbiental, "version_factor"): VersionFactorAmbiental,
            (CalculoAmbiental, "recalculo_de"): CalculoAmbiental,
            (InputCalculoAmbiental, "calculo"): CalculoAmbiental,
            (InputCalculoAmbiental, "variable"): VariableFormula,
            (InputCalculoAmbiental, "observacion"): Observacion,
            (InputCalculoAmbiental, "fuente"): FuenteDatos,
            (InputCalculoAmbiental, "evidencia"): EvidenciaObra,
            (InputCalculoAmbiental, "version_evidencia"): VersionEvidencia,
            (ImpactoAmbiental, "organizacion"): Organizacion,
            (ImpactoAmbiental, "actividad"): ActividadOperacional,
            (ImpactoAmbiental, "calculo"): CalculoAmbiental,
        }
        for (model, field_name), target in expected.items():
            with self.subTest(model=model.__name__, field=field_name):
                field = model._meta.get_field(field_name)
                self.assertIs(field.remote_field.model, target)

        self.assertTrue(ImpactoAmbiental._meta.get_field("calculo").one_to_one)

    def test_governance_constraints_keep_global_tenant_and_version_contracts(self):
        expected = {
            MetodologiaAmbiental: {
                "unique_metodologia_codigo_global",
                "unique_metodologia_codigo_tenant",
            },
            FactorAmbiental: {
                "unique_factor_ambiental_codigo_global",
                "unique_factor_ambiental_codigo_tenant",
            },
            VersionMetodologia: {"unique_version_metodologia"},
            VersionFactorAmbiental: {"unique_version_factor_ambiental"},
            VariableFormula: {"unique_variable_formula"},
            CompatibilidadVersionMetodologia: {
                "unique_compatibilidad_version_metodologia"
            },
        }
        for model, names in expected.items():
            with self.subTest(model=model.__name__):
                self.assertEqual({item.name for item in model._meta.constraints}, names)

    def test_environment_quality_and_indicator_relations_keep_their_targets(self):
        expected = {
            (RegistroFlujoAmbiental, "organizacion"): Organizacion,
            (RegistroFlujoAmbiental, "actividad"): ActividadOperacional,
            (RegistroFlujoAmbiental, "evento_material"): EventoMaterial,
            (EvaluacionCalidadDato, "observacion"): Observacion,
            (DiscrepanciaDato, "actividad"): ActividadOperacional,
            (DiscrepanciaDato, "observaciones"): Observacion,
            (PoliticaConfianzaFuente, "organizacion"): Organizacion,
            (IndicadorAmbiental, "organizacion"): Organizacion,
            (IndicadorAmbiental, "obra"): Obra,
            (ValorIndicador, "indicador"): IndicadorAmbiental,
            (LineaBaseAmbiental, "indicador"): IndicadorAmbiental,
            (PeriodoComparable, "indicador"): IndicadorAmbiental,
        }
        for (model, field_name), target in expected.items():
            with self.subTest(model=model.__name__, field=field_name):
                self.assertIs(
                    model._meta.get_field(field_name).remote_field.model, target
                )

        policy_constraints = {
            item.name for item in PoliticaConfianzaFuente._meta.constraints
        }
        self.assertEqual(
            policy_constraints,
            {"unique_politica_fuente_global", "unique_politica_fuente_tenant"},
        )

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

    def create_observation_context(self, suffix=""):
        organization, _, _, work, _ = self.create_asset_context(suffix)
        source = FuenteDatos.objects.create(
            organizacion=organization, nombre=f"Fuente {suffix}"
        )
        activity = ActividadOperacional.objects.create(
            organizacion=organization,
            obra=work,
            tipo=ActividadOperacional.Tipo.CONSUMO_ENERGIA,
            codigo=f"ACT-ENV-{suffix}",
            nombre=f"Consumo {suffix}",
            timestamp_inicio=timezone.now(),
        )
        observation = Observacion.objects.create(
            organizacion=organization,
            actividad=activity,
            fuente=source,
            concepto="energia_consumida_kwh",
            valor_numerico=Decimal("25"),
            unidad="kWh",
            timestamp_observacion=timezone.now(),
        )
        return organization, work, source, activity, observation

    def test_environmental_flow_can_still_be_created(self):
        organization, work, _, activity, _ = self.create_observation_context("FLOW")
        flow = RegistroFlujoAmbiental.objects.create(
            organizacion=organization,
            actividad=activity,
            flujo=RegistroFlujoAmbiental.Flujo.ENERGIA,
            periodo_inicio=activity.timestamp_inicio,
            granularidad=RegistroFlujoAmbiental.Granularidad.OBRA,
            obra=work,
        )

        self.assertEqual(flow.actividad, activity)
        self.assertEqual(activity.registro_flujo_ambiental, flow)

    def test_environmental_flow_keeps_activity_and_tenant_validations(self):
        organization, _, _, _, _ = self.create_observation_context("LOCAL-FLOW")
        _, foreign_work, _, foreign_activity, _ = self.create_observation_context(
            "FOREIGN-FLOW"
        )
        flow = RegistroFlujoAmbiental(
            organizacion=organization,
            actividad=foreign_activity,
            flujo=RegistroFlujoAmbiental.Flujo.AGUA,
            periodo_inicio=timezone.now(),
            granularidad=RegistroFlujoAmbiental.Granularidad.OBRA,
            obra=foreign_work,
        )

        with self.assertRaises(ValidationError) as context:
            flow.full_clean()

        self.assertIn("actividad", context.exception.message_dict)

    def test_environmental_flow_keeps_destination_validation(self):
        organization, _, _, activity, _ = self.create_observation_context("DEST")
        activity.tipo = ActividadOperacional.Tipo.CONSUMO_COMBUSTIBLE
        activity.save(update_fields=["tipo"])
        flow = RegistroFlujoAmbiental(
            organizacion=organization,
            actividad=activity,
            flujo=RegistroFlujoAmbiental.Flujo.COMBUSTIBLE,
            periodo_inicio=timezone.now(),
            destino_operacional=RegistroFlujoAmbiental.DestinoOperacional.RECICLAJE,
        )

        with self.assertRaises(ValidationError) as context:
            flow.full_clean()

        self.assertIn("destino_operacional", context.exception.message_dict)

    def test_quality_entities_and_source_policies_can_still_be_created(self):
        organization, _, _, activity, observation = self.create_observation_context(
            "QUALITY"
        )
        evaluation = EvaluacionCalidadDato.objects.create(
            organizacion=organization,
            observacion=observation,
            estado=EvaluacionCalidadDato.Estado.CONFIABLE,
        )
        discrepancy = DiscrepanciaDato.objects.create(
            organizacion=organization,
            actividad=activity,
            concepto=observation.concepto,
        )
        discrepancy.observaciones.add(observation)
        global_policy = PoliticaConfianzaFuente.objects.create(
            concepto="energia_consumida_kwh",
            tipo_fuente=FuenteDatos.Tipo.MANUAL,
            prioridad=1,
        )
        tenant_policy = PoliticaConfianzaFuente.objects.create(
            organizacion=organization,
            concepto="energia_consumida_kwh",
            tipo_fuente=FuenteDatos.Tipo.DOCUMENTO,
            prioridad=2,
        )

        self.assertEqual(evaluation.observacion, observation)
        self.assertEqual(list(discrepancy.observaciones.all()), [observation])
        self.assertIsNone(global_policy.organizacion_id)
        self.assertEqual(tenant_policy.organizacion, organization)

    def test_indicator_value_baseline_and_comparison_can_still_be_created(self):
        organization, work, _, _, _ = self.create_observation_context("INDICATOR")
        corporate = IndicadorAmbiental.objects.create(
            organizacion=organization,
            codigo="energia-total",
            nombre="Energía total",
            tipo=IndicadorAmbiental.Tipo.ABSOLUTO,
            unidad="kWh",
            origen_numerador="energia_consumida_kwh",
        )
        work_indicator = IndicadorAmbiental.objects.create(
            organizacion=organization,
            alcance=IndicadorAmbiental.Alcance.OBRA,
            obra=work,
            codigo="energia-obra",
            nombre="Energía de obra",
            tipo=IndicadorAmbiental.Tipo.OPERACIONAL,
            unidad="kWh",
            origen_numerador="energia_consumida_kwh",
        )
        value = ValorIndicador.objects.create(
            indicador=work_indicator,
            periodo_inicio=date(2026, 7, 1),
            periodo_fin=date(2026, 7, 31),
            valor=Decimal("25"),
            unidad="kWh",
            fuente_calculo="test",
        )
        baseline = LineaBaseAmbiental.objects.create(
            organizacion=organization,
            indicador=work_indicator,
            periodo_inicio=date(2026, 7, 1),
            periodo_fin=date(2026, 7, 31),
            valor_base=Decimal("25"),
            cantidad_periodos=1,
        )
        comparison = PeriodoComparable.objects.create(
            indicador=work_indicator,
            periodo_actual_inicio=date(2026, 8, 1),
            periodo_actual_fin=date(2026, 8, 31),
            periodo_referencia_inicio=date(2026, 7, 1),
            periodo_referencia_fin=date(2026, 7, 31),
            regla=PeriodoComparable.Regla.ANTERIOR_EQUIVALENTE,
            motivo_comparabilidad="Misma obra y duración equivalente.",
        )

        self.assertIsNone(corporate.obra_id)
        self.assertEqual(value.indicador, work_indicator)
        self.assertEqual(baseline.indicador, work_indicator)
        self.assertEqual(comparison.indicador, work_indicator)

    def test_indicator_scope_keeps_cross_tenant_validation(self):
        organization = Organizacion.objects.create(nombre="Indicator tenant")
        other = Organizacion.objects.create(nombre="Foreign indicator tenant")
        foreign_work = Obra.objects.create(
            organizacion=other,
            nombre="Foreign indicator work",
            fecha_inicio=date(2026, 8, 27),
        )
        indicator = IndicadorAmbiental(
            organizacion=organization,
            alcance=IndicadorAmbiental.Alcance.OBRA,
            obra=foreign_work,
            codigo="cross-tenant",
            nombre="Cross tenant",
            tipo=IndicadorAmbiental.Tipo.ABSOLUTO,
            unidad="kg",
            origen_numerador="masa",
        )

        with self.assertRaises(ValidationError) as context:
            indicator.full_clean()

        self.assertIn("obra", context.exception.message_dict)

    def create_governance_context(self, suffix=""):
        organization = Organizacion.objects.create(nombre=f"Governance {suffix}")
        global_methodology = MetodologiaAmbiental.objects.create(
            codigo=f"method-global-{suffix.lower()}",
            nombre=f"Metodología global {suffix}",
            categoria="emisiones",
            flujo="combustible",
        )
        tenant_methodology = MetodologiaAmbiental.objects.create(
            organizacion=organization,
            codigo=f"method-tenant-{suffix.lower()}",
            nombre=f"Metodología tenant {suffix}",
            categoria="emisiones",
            flujo="combustible",
        )
        methodology_version = VersionMetodologia.objects.create(
            metodologia=tenant_methodology,
            version=1,
            descripcion_tecnica="Versión de prueba",
        )
        global_factor = FactorAmbiental.objects.create(
            codigo=f"factor-global-{suffix.lower()}",
            nombre=f"Factor global {suffix}",
            categoria="combustible",
            unidad_entrada="L",
        )
        tenant_factor = FactorAmbiental.objects.create(
            organizacion=organization,
            codigo=f"factor-tenant-{suffix.lower()}",
            nombre=f"Factor tenant {suffix}",
            categoria="combustible",
            unidad_entrada="L",
        )
        factor_version = VersionFactorAmbiental.objects.create(
            factor=tenant_factor,
            version=1,
            valor=Decimal("2.7000000000"),
            fuente="Fuente de prueba",
        )
        return (
            organization,
            global_methodology,
            tenant_methodology,
            methodology_version,
            global_factor,
            tenant_factor,
            factor_version,
        )

    def test_global_and_tenant_governance_entities_can_still_be_created(self):
        (
            organization,
            global_methodology,
            tenant_methodology,
            methodology_version,
            global_factor,
            tenant_factor,
            factor_version,
        ) = self.create_governance_context("CREATE")

        self.assertIsNone(global_methodology.organizacion_id)
        self.assertEqual(tenant_methodology.organizacion, organization)
        self.assertEqual(methodology_version.metodologia, tenant_methodology)
        self.assertIsNone(global_factor.organizacion_id)
        self.assertEqual(tenant_factor.organizacion, organization)
        self.assertEqual(factor_version.factor, tenant_factor)

    def test_active_methodology_and_factor_versions_remain_immutable(self):
        context = self.create_governance_context("IMMUTABLE-GOV")
        methodology_version = context[3]
        factor_version = context[6]
        VersionMetodologia.objects.filter(pk=methodology_version.pk).update(
            estado=VersionMetodologia.Estado.ACTIVA
        )
        VersionFactorAmbiental.objects.filter(pk=factor_version.pk).update(
            estado=VersionFactorAmbiental.Estado.ACTIVO
        )
        methodology_version.refresh_from_db()
        factor_version.refresh_from_db()
        methodology_version.descripcion_tecnica = "Cambio no permitido"
        factor_version.valor = Decimal("3")

        with self.assertRaises(ValidationError):
            methodology_version.save()
        with self.assertRaises(ValidationError):
            factor_version.save()

    def test_governed_version_delete_signals_remain_registered(self):
        context = self.create_governance_context("DELETE-GOV")
        methodology_version = context[3]
        factor_version = context[6]
        VersionMetodologia.objects.filter(pk=methodology_version.pk).update(
            estado=VersionMetodologia.Estado.VALIDADA
        )
        VersionFactorAmbiental.objects.filter(pk=factor_version.pk).update(
            estado=VersionFactorAmbiental.Estado.VALIDADO
        )

        with self.assertRaises(ValidationError), transaction.atomic():
            VersionMetodologia.objects.filter(pk=methodology_version.pk).delete()
        with self.assertRaises(ValidationError), transaction.atomic():
            VersionFactorAmbiental.objects.filter(pk=factor_version.pk).delete()

    def test_formula_variable_and_compatibility_can_still_be_created(self):
        context = self.create_governance_context("FORMULA")
        tenant_methodology = context[2]
        methodology_version = context[3]
        tenant_factor = context[5]
        formula = FormulaAmbiental.objects.create(
            version_metodologia=methodology_version,
            factor_ambiental=tenant_factor,
            codigo="formula-transporte",
            tipo=FormulaAmbiental.Tipo.TRANSPORTE_COMBUSTIBLE,
            expresion_legible="combustible x factor",
        )
        variable = VariableFormula.objects.create(
            formula=formula,
            clave="combustible",
            concepto_observacion="combustible_consumido_l",
            unidad_esperada="L",
        )
        second_version = VersionMetodologia.objects.create(
            metodologia=tenant_methodology,
            version=2,
        )
        compatibility = CompatibilidadVersionMetodologia.objects.create(
            version_origen=methodology_version,
            version_destino=second_version,
            estado=CompatibilidadVersionMetodologia.Estado.COMPATIBLE,
        )

        self.assertEqual(variable.formula, formula)
        self.assertEqual(compatibility.version_origen, methodology_version)
        self.assertEqual(compatibility.version_destino, second_version)

    def test_governed_formula_and_variables_remain_protected(self):
        context = self.create_governance_context("PROTECTED-FORMULA")
        methodology_version = context[3]
        formula = FormulaAmbiental.objects.create(
            version_metodologia=methodology_version,
            factor_ambiental=context[5],
            codigo="formula-protegida",
            tipo=FormulaAmbiental.Tipo.TRANSPORTE_COMBUSTIBLE,
            expresion_legible="combustible x factor",
        )
        variable = VariableFormula.objects.create(
            formula=formula,
            clave="combustible",
            concepto_observacion="combustible_consumido_l",
            unidad_esperada="L",
        )
        VersionMetodologia.objects.filter(pk=methodology_version.pk).update(
            estado=VersionMetodologia.Estado.ACTIVA
        )
        formula.refresh_from_db()
        variable.refresh_from_db()

        formula.expresion_legible = "cambio"
        variable.descripcion = "cambio"
        with self.assertRaises(ValidationError):
            formula.save()
        with self.assertRaises(ValidationError):
            variable.save()
        with self.assertRaises(ValidationError), transaction.atomic():
            FormulaAmbiental.objects.filter(pk=formula.pk).delete()
        with self.assertRaises(ValidationError), transaction.atomic():
            VariableFormula.objects.filter(pk=variable.pk).delete()

    def create_calculation_context(self, suffix=""):
        organization, work, source, activity, observation = (
            self.create_observation_context(f"CALC-{suffix}")
        )
        methodology = MetodologiaAmbiental.objects.create(
            organizacion=organization,
            codigo=f"calculation-method-{suffix.lower()}",
            nombre=f"Método de cálculo {suffix}",
            categoria="emisiones",
            flujo="combustible",
        )
        methodology_version = VersionMetodologia.objects.create(
            metodologia=methodology,
            version=1,
        )
        factor = FactorAmbiental.objects.create(
            organizacion=organization,
            codigo=f"calculation-factor-{suffix.lower()}",
            nombre=f"Factor de cálculo {suffix}",
            categoria="combustible",
            unidad_entrada="L",
        )
        factor_version = VersionFactorAmbiental.objects.create(
            factor=factor,
            version=1,
            valor=Decimal("2.7000000000"),
            fuente="Fuente de prueba",
        )
        formula = FormulaAmbiental.objects.create(
            version_metodologia=methodology_version,
            factor_ambiental=factor,
            codigo=f"calculation-formula-{suffix.lower()}",
            tipo=FormulaAmbiental.Tipo.TRANSPORTE_COMBUSTIBLE,
            expresion_legible="combustible x factor",
        )
        variable = VariableFormula.objects.create(
            formula=formula,
            clave="combustible",
            concepto_observacion=observation.concepto,
            unidad_esperada=observation.unidad,
        )
        evidence = EvidenciaObra.objects.create(
            organizacion=organization,
            obra=work,
            archivo=SimpleUploadedFile("evidence.txt", b"evidence"),
            nombre=f"Evidencia {suffix}",
        )
        evidence_version = VersionEvidencia.objects.create(
            evidencia=evidence,
            organizacion=organization,
            version=1,
            archivo=SimpleUploadedFile("evidence-v1.txt", b"evidence-v1"),
            nombre_original="evidence-v1.txt",
            checksum_sha256="a" * 64,
        )
        calculation = CalculoAmbiental.objects.create(
            organizacion=organization,
            actividad=activity,
            version_metodologia=methodology_version,
            formula=formula,
            version_factor=factor_version,
            resultado=Decimal("67.5000000000"),
            unidad_resultado="kgCO2e",
            formula_aplicada=formula.expresion_legible,
            completitud="elegible",
            snapshot_tecnico={"source": "architecture-test"},
        )
        return {
            "organization": organization,
            "activity": activity,
            "source": source,
            "observation": observation,
            "methodology_version": methodology_version,
            "factor_version": factor_version,
            "formula": formula,
            "variable": variable,
            "evidence": evidence,
            "evidence_version": evidence_version,
            "calculation": calculation,
        }

    def test_calculation_input_and_impact_can_still_be_created(self):
        context = self.create_calculation_context("CREATE")
        calculation_input = InputCalculoAmbiental.objects.create(
            calculo=context["calculation"],
            variable=context["variable"],
            observacion=context["observation"],
            valor_utilizado=Decimal("25"),
            unidad=context["observation"].unidad,
            concepto=context["observation"].concepto,
            fuente=context["source"],
            evidencia=context["evidence"],
            version_evidencia=context["evidence_version"],
        )
        impact = ImpactoAmbiental.objects.create(
            organizacion=context["organization"],
            actividad=context["activity"],
            calculo=context["calculation"],
            tipo=ImpactoAmbiental.Tipo.GENERADO,
            categoria="emisiones",
            valor=context["calculation"].resultado,
            unidad=context["calculation"].unidad_resultado,
            timestamp=context["activity"].timestamp_inicio,
        )

        self.assertEqual(calculation_input.observacion, context["observation"])
        self.assertEqual(calculation_input.evidencia, context["evidence"])
        self.assertEqual(
            calculation_input.version_evidencia, context["evidence_version"]
        )
        self.assertEqual(impact.calculo, context["calculation"])
        self.assertEqual(context["calculation"].impacto, impact)

    def test_persisted_calculation_remains_immutable(self):
        calculation = self.create_calculation_context("IMMUTABLE")["calculation"]
        calculation.resultado = Decimal("999")

        with self.assertRaises(ValidationError):
            calculation.save()

    def test_recalculation_contract_can_still_create_a_new_calculation(self):
        context = self.create_calculation_context("RECALCULATION")
        original = context["calculation"]
        recalculation = CalculoAmbiental.objects.create(
            organizacion=context["organization"],
            actividad=context["activity"],
            version_metodologia=context["methodology_version"],
            formula=context["formula"],
            version_factor=context["factor_version"],
            resultado=Decimal("68.0000000000"),
            unidad_resultado=original.unidad_resultado,
            formula_aplicada=original.formula_aplicada,
            completitud=original.completitud,
            version_interna=2,
            recalculo_de=original,
            motivo_recalculo="Corrección documentada",
        )

        self.assertEqual(recalculation.recalculo_de, original)
        self.assertEqual(list(original.recalculos.all()), [recalculation])

    def create_improvement_context(self, suffix=""):
        organization, work, _, activity, _ = self.create_observation_context(
            f"IMPROVEMENT-{suffix}"
        )
        indicator = IndicadorAmbiental.objects.create(
            organizacion=organization,
            codigo=f"improvement-{suffix.lower()}",
            nombre=f"Indicador {suffix}",
            tipo=IndicadorAmbiental.Tipo.ABSOLUTO,
            unidad="kgCO2e",
            origen_numerador="impactos_ambientales",
            direccion_deseable=IndicadorAmbiental.DireccionDeseable.MENOR,
        )
        indicator_value = ValorIndicador.objects.create(
            indicador=indicator,
            periodo_inicio=date(2026, 7, 1),
            periodo_fin=date(2026, 7, 31),
            valor=Decimal("10"),
            unidad=indicator.unidad,
            fuente_calculo="architecture-test",
        )
        problem = ProblematicaAmbiental.objects.create(
            organizacion=organization,
            obra=work,
            titulo=f"Problemática {suffix}",
            descripcion="Desviación ambiental verificable",
            categoria="emisiones",
            valor_inicial=Decimal("10"),
            objetivo_meta=Decimal("8"),
            fecha_deteccion=date(2026, 8, 1),
        )
        action = AccionMejoraAmbiental.objects.create(
            problematica=problem,
            titulo=f"Acción {suffix}",
            descripcion="Intervención operacional",
        )
        link = IndicadorProblematica.objects.create(
            problematica=problem,
            indicador=indicator,
            direccion_deseada=IndicadorAmbiental.DireccionDeseable.MENOR,
            valor_objetivo=Decimal("8"),
        )
        scope = AlcanceProblematica.objects.create(
            problematica=problem,
            actividad_operacional=activity,
            indicador=indicator,
        )
        return {
            "organization": organization,
            "work": work,
            "activity": activity,
            "indicator": indicator,
            "indicator_value": indicator_value,
            "problem": problem,
            "action": action,
            "link": link,
            "scope": scope,
        }

    def test_improvement_state_choices_remain_unchanged(self):
        self.assertEqual(
            set(ProblematicaAmbiental.Estado.values),
            {
                "detectada",
                "analizando",
                "propuesta",
                "accion_seleccionada",
                "implementando",
                "seguimiento",
                "evaluando",
                "escalada_profesional",
                "cerrada",
                "en_analisis",
                "accion_propuesta",
                "en_implementacion",
                "en_seguimiento",
                "resuelta",
                "mejora_insuficiente",
                "no_resuelta",
                "escalada",
            },
        )
        self.assertEqual(
            set(AccionMejoraAmbiental.Estado.values),
            {
                "propuesta",
                "ajustada",
                "seleccionada",
                "en_implementacion",
                "seguimiento",
                "evaluada",
                "descartada",
                "cancelada",
            },
        )
        self.assertEqual(
            set(ResultadoIntervencion.Estado.values),
            {
                "no_implementada",
                "no_viable",
                "parcial",
                "implementada_sin_efecto",
                "positiva",
                "negativa",
                "inconclusa",
            },
        )

    def test_complete_improvement_graph_can_still_be_created(self):
        context = self.create_improvement_context("GRAPH")
        measurement = MedicionSeguimientoAmbiental.objects.create(
            problematica=context["problem"],
            accion=context["action"],
            fecha=date(2026, 8, 20),
            valor=Decimal("9"),
            unidad="kgCO2e",
            indicador_v2=context["indicator"],
            valor_indicador=context["indicator_value"],
        )
        base = SnapshotIntervencion.objects.create(
            problematica=context["problem"],
            accion=context["action"],
            ciclo=1,
            tipo=SnapshotIntervencion.Tipo.BASE,
            fecha=date(2026, 8, 1),
        )
        snapshot_value = SnapshotValorIndicador.objects.create(
            snapshot=base,
            indicador=context["indicator"],
            valor=Decimal("10"),
            unidad="kgCO2e",
            periodo_inicio=date(2026, 7, 1),
            periodo_fin=date(2026, 7, 31),
            valor_indicador_origen=context["indicator_value"],
        )
        result_snapshot = SnapshotIntervencion.objects.create(
            problematica=context["problem"],
            accion=context["action"],
            ciclo=1,
            tipo=SnapshotIntervencion.Tipo.RESULTADO,
            fecha=date(2026, 8, 31),
            congelado=True,
        )
        result = ResultadoIntervencion.objects.create(
            problematica=context["problem"],
            accion=context["action"],
            ciclo=1,
            snapshot_base=base,
            snapshot_resultado=result_snapshot,
            estado=ResultadoIntervencion.Estado.PARCIAL,
            fecha_evaluacion=date(2026, 8, 31),
        )
        cycle = CicloReevaluacionProblematica.objects.create(
            problematica=context["problem"],
            numero=1,
            accion=context["action"],
            snapshot_base=base,
            snapshot_resultado=result_snapshot,
            resultado=result,
            fecha_inicio=date(2026, 8, 1),
            fecha_cierre=date(2026, 8, 31),
        )
        user = User.objects.create_user(username="improvement-history")
        target_history = HistorialMetaProblematica.objects.create(
            problematica=context["problem"],
            indicador_problematica=context["link"],
            valor_anterior=Decimal("9"),
            valor_nuevo=Decimal("8"),
            justificacion_tecnica="Nueva evidencia",
            motivo="Ajuste gobernado",
            usuario=user,
        )
        event_history = HistorialProblematicaAmbiental.objects.create(
            problematica=context["problem"],
            evento="verificacion",
            estado_anterior=ProblematicaAmbiental.Estado.EVALUANDO,
            estado_nuevo=ProblematicaAmbiental.Estado.CERRADA,
        )

        self.assertEqual(context["problem"].acciones.get(), context["action"])
        self.assertEqual(measurement.valor_indicador, context["indicator_value"])
        self.assertEqual(snapshot_value.snapshot, base)
        self.assertEqual(cycle.resultado, result)
        self.assertEqual(target_history.indicador_problematica, context["link"])
        self.assertEqual(event_history.problematica, context["problem"])

    def test_improvement_cross_tenant_validations_remain_unchanged(self):
        context = self.create_improvement_context("LOCAL")
        other = Organizacion.objects.create(nombre="Improvement foreign")
        foreign_work = Obra.objects.create(
            organizacion=other,
            nombre="Foreign work",
            fecha_inicio=date(2026, 8, 1),
        )
        problem = context["problem"]
        problem.obra = foreign_work

        with self.assertRaises(ValidationError) as error:
            problem.full_clean()

        self.assertIn("obra", error.exception.message_dict)

    def test_frozen_improvement_snapshot_and_values_remain_immutable(self):
        context = self.create_improvement_context("FROZEN")
        snapshot = SnapshotIntervencion.objects.create(
            problematica=context["problem"],
            accion=context["action"],
            tipo=SnapshotIntervencion.Tipo.BASE,
            fecha=date(2026, 8, 1),
        )
        value = SnapshotValorIndicador.objects.create(
            snapshot=snapshot,
            indicador=context["indicator"],
            valor=Decimal("10"),
            unidad="kgCO2e",
            periodo_inicio=date(2026, 7, 1),
            periodo_fin=date(2026, 7, 31),
        )
        SnapshotIntervencion.objects.filter(pk=snapshot.pk).update(congelado=True)
        snapshot.refresh_from_db()
        value.refresh_from_db()

        snapshot.metadata_tecnica = {"changed": True}
        value.valor = Decimal("99")
        with self.assertRaises(ValidationError):
            snapshot.save()
        with self.assertRaises(ValidationError):
            value.save()
        with self.assertRaises(ValidationError):
            snapshot.delete()
        with self.assertRaises(ValidationError):
            value.delete()

    def create_intelligence_context(self, suffix=""):
        context = self.create_improvement_context(f"INTELLIGENCE-{suffix}")
        base = SnapshotIntervencion.objects.create(
            problematica=context["problem"],
            accion=context["action"],
            ciclo=1,
            tipo=SnapshotIntervencion.Tipo.BASE,
            fecha=date(2026, 8, 1),
        )
        result_snapshot = SnapshotIntervencion.objects.create(
            problematica=context["problem"],
            accion=context["action"],
            ciclo=1,
            tipo=SnapshotIntervencion.Tipo.RESULTADO,
            fecha=date(2026, 8, 31),
        )
        result = ResultadoIntervencion.objects.create(
            problematica=context["problem"],
            accion=context["action"],
            ciclo=1,
            snapshot_base=base,
            snapshot_resultado=result_snapshot,
            estado=ResultadoIntervencion.Estado.POSITIVA,
            fecha_evaluacion=date(2026, 8, 31),
        )
        proposal = RecomendacionAgenteAmbiental.objects.create(
            problematica=context["problem"],
            accion="Consolidar cargas",
            justificacion="Reducir viajes parciales",
            indicador_afectado=context["indicator"].codigo,
            resultado_esperado="Reducir emisiones",
            prioridad=RecomendacionAgenteAmbiental.Prioridad.MEDIA,
            periodo_seguimiento="Mensual",
            nivel_confianza=RecomendacionAgenteAmbiental.Confianza.MEDIA,
        )
        context.update({"result": result, "proposal": proposal})
        return context

    def test_intelligence_entities_and_human_command_states_can_still_be_created(self):
        context = self.create_intelligence_context("CREATE")
        user = User.objects.create_user(username="intelligence-user")
        memory = MemoriaOrganizacion.objects.create(
            organizacion=context["organization"],
            problematica=context["problem"],
            tipo=MemoriaOrganizacion.Tipo.ACCION_ACEPTADA,
            contenido={"accion": context["action"].id},
            fuente_origen="confirmacion_humana",
        )
        restriction = RestriccionContextual.objects.create(
            organizacion=context["organization"],
            problematica=context["problem"],
            tipo="operacional",
            descripcion="Ventana horaria limitada",
            created_by=user,
        )
        restriction_history = HistorialRestriccionContextual.objects.create(
            restriccion=restriction,
            contenido_anterior={},
            contenido_nuevo={"horario": "diurno"},
            motivo="Confirmación operacional",
            usuario=user,
        )
        milestone = HitoDecisionIA.objects.create(
            organizacion=context["organization"],
            problematica=context["problem"],
            propuesta=context["proposal"],
            tipo=HitoDecisionIA.Tipo.DECISION,
            resumen="Propuesta confirmada por usuario",
            usuario=user,
        )
        prepared = ComandoCopiloto.objects.create(
            organizacion=context["organization"],
            problematica=context["problem"],
            propuesta=context["proposal"],
            tipo=ComandoCopiloto.Tipo.ACCION,
        )
        confirmed = ComandoCopiloto.objects.create(
            organizacion=context["organization"],
            problematica=context["problem"],
            tipo=ComandoCopiloto.Tipo.REEVALUACION,
            estado=ComandoCopiloto.Estado.CONFIRMADO,
            confirmado_por=user,
        )
        rejected = ComandoCopiloto.objects.create(
            organizacion=context["organization"],
            problematica=context["problem"],
            tipo=ComandoCopiloto.Tipo.RESTRICCION,
            estado=ComandoCopiloto.Estado.RECHAZADO,
            confirmado_por=user,
        )

        self.assertEqual(
            context["problem"].recomendaciones_agente.get(), context["proposal"]
        )
        self.assertEqual(memory.problematica, context["problem"])
        self.assertEqual(restriction_history.restriccion, restriction)
        self.assertEqual(milestone.propuesta, context["proposal"])
        self.assertEqual(prepared.estado, ComandoCopiloto.Estado.PREPARADO)
        self.assertEqual(confirmed.estado, ComandoCopiloto.Estado.CONFIRMADO)
        self.assertEqual(rejected.estado, ComandoCopiloto.Estado.RECHAZADO)

    def test_environmental_knowledge_case_can_still_be_created(self):
        context = self.create_intelligence_context("KNOWLEDGE")
        case = CasoConocimientoAmbiental.objects.create(
            organizacion=context["organization"],
            resultado_origen=context["result"],
            preset="construccion",
            tipo_problematica="emisiones-altas",
            categoria_ambiental="emisiones",
            tipo_accion="optimizacion-logistica",
            contexto_operacional={"obra": context["work"].id},
            resultado=CasoConocimientoAmbiental.Resultado.EXITOSO,
            metricas_comparadas=[{"indicador": context["indicator"].id}],
            grado_implementacion="completo",
            viabilidad="alta",
            fuerza_evidencia=CasoConocimientoAmbiental.Fuerza.MEDIA,
            fundamento_evidencia=["Resultado de intervención verificable"],
            origen_conocimiento=CasoConocimientoAmbiental.Origen.MIXTO,
            fecha_caso=date(2026, 8, 31),
            fingerprint="knowledge-architecture-test",
        )

        self.assertEqual(case.resultado_origen, context["result"])
        self.assertEqual(case.estado, CasoConocimientoAmbiental.Estado.CANDIDATO)

    def test_intelligence_tenant_safety_remains_unchanged(self):
        context = self.create_intelligence_context("TENANT")
        other = Organizacion.objects.create(nombre="Foreign intelligence tenant")
        memory = MemoriaOrganizacion(
            organizacion=other,
            problematica=context["problem"],
            tipo=MemoriaOrganizacion.Tipo.INTERVENCION,
            contenido={},
            fuente_origen="test",
        )
        restriction = RestriccionContextual(
            organizacion=other,
            problematica=context["problem"],
            tipo="operational",
            descripcion="Foreign restriction",
        )

        with self.assertRaises(ValidationError) as memory_error:
            memory.full_clean()
        with self.assertRaises(ValidationError) as restriction_error:
            restriction.full_clean()

        self.assertIn("problematica", memory_error.exception.message_dict)
        self.assertIn("problematica", restriction_error.exception.message_dict)
