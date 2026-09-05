from django.db import transaction
from .models import EnvironmentalSource, SourceState

SOURCES=(("retc","RETC","Ministerio del Medio Ambiente","CKAN"),("huellachile","HuellaChile","Ministerio del Medio Ambiente","FILE"),("bcn-leychile","BCN LeyChile","Biblioteca del Congreso Nacional","SPARQL"),("snifa","SNIFA","Superintendencia del Medio Ambiente","DOCUMENT_INDEX"),("sea-seia","SEA / SEIA","Servicio de Evaluacion Ambiental","DOCUMENT_INDEX"),("simbio","SIMBIO","Ministerio del Medio Ambiente","ARCGIS_REST"),("ide-mma","IDE MMA","Ministerio del Medio Ambiente","WFS"),("okobaudat","OKOBAUDAT","Gobierno Federal de Alemania","REST"))
@transaction.atomic
def ensure_environmental_source_registry():
    result=[]
    for code,name,agency,access in SOURCES:
        source,created=EnvironmentalSource.objects.get_or_create(codigo=code,defaults={"nombre":name,"organismo":agency,"descripcion":"Registro preparado para integracion futura controlada.","connector_key":f"pending-{code}","tipo_acceso":access,"nivel_autoridad":"oficial","pais":"Chile" if code!="okobaudat" else "Alemania"})
        legacy={"retc":"DOCUMENT_INDEX","huellachile":"DOCUMENT_INDEX","bcn-leychile":"DOCUMENT_INDEX","simbio":"DOCUMENT_INDEX","ide-mma":"ARCGIS_REST","okobaudat":"DOCUMENT_INDEX"}.get(code)
        if not created and legacy and source.connector_key==f"pending-{code}" and source.tipo_acceso==legacy:
            source.tipo_acceso=access;source.save(update_fields=["tipo_acceso","updated_at"])
        SourceState.objects.get_or_create(source=source); result.append(source)
    return result
def ensure_source_registry_after_migrate(**kwargs): ensure_environmental_source_registry()
