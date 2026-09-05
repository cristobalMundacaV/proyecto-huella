from django.db import transaction
from .models import EnvironmentalSource, SourceState

SOURCES=(("retc","RETC","Ministerio del Medio Ambiente","DOCUMENT_INDEX"),("huellachile","HuellaChile","Ministerio del Medio Ambiente","DOCUMENT_INDEX"),("bcn-leychile","BCN LeyChile","Biblioteca del Congreso Nacional","DOCUMENT_INDEX"),("snifa","SNIFA","Superintendencia del Medio Ambiente","DOCUMENT_INDEX"),("sea-seia","SEA / SEIA","Servicio de Evaluacion Ambiental","DOCUMENT_INDEX"),("simbio","SIMBIO","Ministerio del Medio Ambiente","DOCUMENT_INDEX"),("ide-mma","IDE MMA","Ministerio del Medio Ambiente","ARCGIS_REST"),("okobaudat","OKOBAUDAT","Gobierno Federal de Alemania","DOCUMENT_INDEX"))
@transaction.atomic
def ensure_environmental_source_registry():
    result=[]
    for code,name,agency,access in SOURCES:
        source,_=EnvironmentalSource.objects.get_or_create(codigo=code,defaults={"nombre":name,"organismo":agency,"descripcion":"Registro preparado para integracion futura controlada.","connector_key":f"pending-{code}","tipo_acceso":access,"nivel_autoridad":"oficial","pais":"Chile" if code!="okobaudat" else "Alemania"})
        SourceState.objects.get_or_create(source=source); result.append(source)
    return result
def ensure_source_registry_after_migrate(**kwargs): ensure_environmental_source_registry()
