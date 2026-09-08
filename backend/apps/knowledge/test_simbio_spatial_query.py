from types import SimpleNamespace
from unittest.mock import patch
from django.test import SimpleTestCase
from .simbio_spatial_query import query_simbio_layer_at_point
class SimbioSpatialQueryTests(SimpleTestCase):
    def test_point_order_bands_and_no_geometry(self):
        layer=SimpleNamespace(layer_url="https://arcgis.mma.gob.cl/server/rest/services/SIMBIO/X/FeatureServer/0",supports_distance_query=True,max_record_count=2,object_id_field="OID",display_field="NAME",layer_name="Layer",service_code="X",layer_id=0,snapshot=SimpleNamespace(content_hash="a"*64))
        calls=[]
        def fetch(url,params=None):
            calls.append(params)
            if params.get("returnIdsOnly")=="true":return {"objectIds":{None:[1],1:[1,2],5:[1,2,3]}[params.get("distance")]}
            ids=[int(x) for x in params["objectIds"].split(",")];return {"features":[{"attributes":{"NAME":f"N{i}","OID":i}} for i in ids]}
        with patch("apps.knowledge.simbio_spatial_query.fetch_arcgis_json",side_effect=fetch):result=query_simbio_layer_at_point(layer,-37.4698,-72.3537,"proximity")
        self.assertEqual([(x["object_id"],x["proximity_band"]) for x in result],[(1,"intersects"),(2,"within_1km"),(3,"within_5km")]);self.assertEqual(calls[0]["geometry"],"-72.3537,-37.4698");self.assertEqual(calls[0]["inSR"],4326);self.assertEqual(calls[-1]["returnGeometry"],"false")
    def test_ecoregion_has_no_distance_and_unsupported_proximity_fails(self):
        layer=SimpleNamespace(layer_url="https://arcgis.mma.gob.cl/server/rest/services/SIMBIO/X/FeatureServer/0",supports_distance_query=False,max_record_count=2,object_id_field="OID",display_field="",layer_name="Eco",service_code="X",layer_id=0,snapshot=SimpleNamespace(content_hash="a"*64))
        with patch("apps.knowledge.simbio_spatial_query.fetch_arcgis_json",side_effect=[{"objectIds":[]}]) as fetch:query_simbio_layer_at_point(layer,0,0,"intersects");self.assertNotIn("distance",fetch.call_args.args[1])
        with patch("apps.knowledge.simbio_spatial_query.fetch_arcgis_json",return_value={"objectIds":[]}),self.assertRaises(ValueError):query_simbio_layer_at_point(layer,0,0,"proximity")
