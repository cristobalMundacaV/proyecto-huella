import hashlib,json
from django.conf import settings
from .connectors.simbio import fetch_arcgis_json,validate_simbio_url

BANDS=("intersects","within_1km","within_5km")
def _ids(layer,latitude,longitude,distance=None):
    params={"geometry":f"{longitude},{latitude}","geometryType":"esriGeometryPoint","inSR":4326,"spatialRel":"esriSpatialRelIntersects","returnIdsOnly":"true"}
    if distance is not None:params.update(distance=distance,units="esriSRUnit_Kilometer")
    data=fetch_arcgis_json(layer.layer_url+"/query",params);return set(data.get("objectIds") or [])
def query_simbio_layer_at_point(layer_fact,latitude,longitude,mode):
    validate_simbio_url(layer_fact.layer_url+"/query")
    intersect=_ids(layer_fact,latitude,longitude)
    if mode=="proximity":
        if not layer_fact.supports_distance_query:raise ValueError("La capa no soporta consultas de proximidad.")
        one=_ids(layer_fact,latitude,longitude,1);five=_ids(layer_fact,latitude,longitude,5);bandsets=(("intersects",intersect),("within_1km",one-intersect),("within_5km",five-one))
    elif mode=="intersects":bandsets=(("intersects",intersect),)
    else:raise ValueError("Modo espacial no permitido.")
    bands={oid:band for band,ids in bandsets for oid in ids};ids=sorted(bands)
    limit=getattr(settings,"SIMBIO_SPATIAL_MAX_FEATURES",5000)
    if len(ids)>limit:raise ValueError("Consulta SIMBIO excede el limite operativo.")
    features=[];batch=max(1,min(layer_fact.max_record_count or 500,500))
    for start in range(0,len(ids),batch):
        data=fetch_arcgis_json(layer_fact.layer_url+"/query",{"objectIds":",".join(map(str,ids[start:start+batch])),"outFields":"*","returnGeometry":"false"})
        features.extend(data.get("features") or [])
    output=[]
    for item in features:
        attrs={key:item.get("attributes",{})[key] for key in sorted(item.get("attributes",{}))};oid=attrs.get(layer_fact.object_id_field)
        if oid not in bands:continue
        payload={"service_code":layer_fact.service_code,"layer_id":layer_fact.layer_id,"layer_snapshot_content_hash":layer_fact.snapshot.content_hash,"object_id":oid,"proximity_band":bands[oid],"attributes":attrs};digest=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()).hexdigest();display=attrs.get(layer_fact.display_field) if layer_fact.display_field else None
        output.append({"object_id":oid,"display_name":display or f"{layer_fact.layer_name} #{oid}","proximity_band":bands[oid],"attributes":attrs,"feature_hash":digest})
    return sorted(output,key=lambda x:(BANDS.index(x["proximity_band"]),x["object_id"]))
