from django.db import transaction
from .models import EnvironmentalSource, SourceState

SOURCES=(("retc","RETC","Ministerio del Medio Ambiente","CKAN"),("huellachile","HuellaChile","Ministerio del Medio Ambiente","FILE"),("bcn-leychile","BCN LeyChile","Biblioteca del Congreso Nacional","SPARQL"),("snifa","SNIFA","Superintendencia del Medio Ambiente","DOCUMENT_INDEX"),("sea-seia","SEA / SEIA","Servicio de Evaluacion Ambiental","DOCUMENT_INDEX"),("simbio","SIMBIO","Ministerio del Medio Ambiente","ARCGIS_REST"),("ide-mma","IDE MMA","Ministerio del Medio Ambiente","WFS"),("okobaudat","OKOBAUDAT","Gobierno Federal de Alemania","REST"))
RETC_MANAGED_DEFAULTS={"connector_key":"retc_ckan","tipo_acceso":"CKAN","base_url":"https://datosretc.mma.gob.cl","documentation_url":"https://datosretc.mma.gob.cl/api/3/action/help_show?name=package_search","licencia_nombre":"Creative Commons Attribution","licencia_url":"http://www.opendefinition.org/licenses/cc-by","atribucion_requerida":True,"nivel_autoridad":"oficial","pais":"Chile","organismo":"Ministerio del Medio Ambiente"}
HUELLACHILE_MANAGED_DEFAULTS={"connector_key":"huellachile_web","tipo_acceso":"FILE","base_url":"https://huellachile.mma.gob.cl","documentation_url":"https://huellachile.mma.gob.cl/recursos-material-de-apoyo/","atribucion_requerida":True,"nivel_autoridad":"oficial","pais":"Chile","organismo":"Ministerio del Medio Ambiente"}
@transaction.atomic
def ensure_environmental_source_registry():
    result=[]
    for code,name,agency,access in SOURCES:
        source,created=EnvironmentalSource.objects.get_or_create(codigo=code,defaults={"nombre":name,"organismo":agency,"descripcion":"Registro preparado para integracion futura controlada.","connector_key":f"pending-{code}","tipo_acceso":access,"nivel_autoridad":"oficial","pais":"Chile" if code!="okobaudat" else "Alemania"})
        legacy={"retc":"DOCUMENT_INDEX","huellachile":"DOCUMENT_INDEX","bcn-leychile":"DOCUMENT_INDEX","simbio":"DOCUMENT_INDEX","ide-mma":"ARCGIS_REST","okobaudat":"DOCUMENT_INDEX"}.get(code)
        if not created and legacy and source.connector_key==f"pending-{code}" and source.tipo_acceso==legacy:
            source.tipo_acceso=access;source.save(update_fields=["tipo_acceso","updated_at"])
        retc_unconfigured=(source.connector_key=="pending-retc" and source.tipo_acceso=="CKAN" and not source.base_url and not source.documentation_url and not source.licencia_nombre and not source.licencia_url and source.atribucion_requerida and source.nivel_autoridad=="oficial" and source.pais=="Chile" and source.organismo=="Ministerio del Medio Ambiente")
        if code=="retc" and retc_unconfigured:
            for field,value in RETC_MANAGED_DEFAULTS.items(): setattr(source,field,value)
            source.save(update_fields=[*RETC_MANAGED_DEFAULTS,"updated_at"])
        huellachile_unconfigured=(source.connector_key=="pending-huellachile" and source.tipo_acceso=="FILE" and not source.base_url and not source.documentation_url and not source.licencia_nombre and not source.licencia_url and source.atribucion_requerida and source.nivel_autoridad=="oficial" and source.pais=="Chile" and source.organismo=="Ministerio del Medio Ambiente")
        if code=="huellachile" and huellachile_unconfigured:
            for field,value in HUELLACHILE_MANAGED_DEFAULTS.items(): setattr(source,field,value)
            source.save(update_fields=[*HUELLACHILE_MANAGED_DEFAULTS,"updated_at"])
        SourceState.objects.get_or_create(source=source); result.append(source)
    return result
def ensure_source_registry_after_migrate(**kwargs): ensure_environmental_source_registry()
