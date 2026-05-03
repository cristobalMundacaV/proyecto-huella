from __future__ import annotations

import json
import math
from urllib.parse import quote_plus
from urllib.request import Request, urlopen


USER_AGENT = "ProyectoHuella/1.0 (+https://localhost)"


def _http_json(url, timeout=5):
    request = Request(url, headers={"User-Agent": USER_AGENT})

    with urlopen(request, timeout=timeout) as response:
        payload = response.read().decode("utf-8")

    return json.loads(payload)


def geocode_location(query):
    if not query:
        return None

    url = (
        "https://nominatim.openstreetmap.org/search"
        f"?format=jsonv2&limit=1&q={quote_plus(query)}"
    )
    results = _http_json(url)

    if not results:
        return None

    item = results[0]

    return {
        "lat": float(item["lat"]),
        "lon": float(item["lon"]),
        "display_name": item.get("display_name", query),
    }


def haversine_km(origin_lat, origin_lon, destination_lat, destination_lon):
    radius_km = 6371.0088
    lat1 = math.radians(origin_lat)
    lon1 = math.radians(origin_lon)
    lat2 = math.radians(destination_lat)
    lon2 = math.radians(destination_lon)

    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    return 2 * radius_km * math.asin(math.sqrt(a))


def _normalize_coords(coords):
    if not coords:
        return None

    lat = coords.get("lat")
    lon = coords.get("lon", coords.get("lng"))

    if lat in (None, "") or lon in (None, ""):
        return None

    return {
        "lat": float(lat),
        "lon": float(lon),
        "display_name": coords.get("display_name") or coords.get("address") or "",
    }


def osrm_route_distance_km(origin, destination, origin_coords, destination_coords):
    coords = (
        f"{origin_coords['lon']},{origin_coords['lat']};"
        f"{destination_coords['lon']},{destination_coords['lat']}"
    )
    url = (
        "https://router.project-osrm.org/route/v1/driving/"
        f"{coords}?overview=full&geometries=geojson&alternatives=false&steps=false"
    )

    try:
        payload = _http_json(url, timeout=8)
    except Exception:
        return None

    if payload.get("code") != "Ok" or not payload.get("routes"):
        return None

    route = payload["routes"][0]
    distance_meters = route["distance"]
    duration_seconds = route.get("duration")
    route_geometry = [
        [lat, lon]
        for lon, lat in route.get("geometry", {}).get("coordinates", [])
    ]

    return {
        "origen": origin,
        "destino": destination,
        "distancia_km": round(distance_meters / 1000, 3),
        "duracion_min": round(duration_seconds / 60, 1) if duration_seconds else None,
        "metodo": "osrm_driving",
        "origen_coords": origin_coords,
        "destino_coords": destination_coords,
        "origen_geocodificado": origin_coords,
        "destino_geocodificado": destination_coords,
        "route_geometry": route_geometry,
    }


def route_distance_km(origin, destination, origin_coords=None, destination_coords=None):
    origin_coords = _normalize_coords(origin_coords) or geocode_location(origin)
    destination_coords = _normalize_coords(destination_coords) or geocode_location(destination)

    if not origin_coords or not destination_coords:
        raise ValueError("No se pudo geocodificar uno de los puntos.")

    osrm_distance = osrm_route_distance_km(
        origin,
        destination,
        origin_coords,
        destination_coords,
    )

    if osrm_distance:
        return osrm_distance

    distance_km = haversine_km(
        origin_coords["lat"],
        origin_coords["lon"],
        destination_coords["lat"],
        destination_coords["lon"],
    )

    return {
        "origen": origin,
        "destino": destination,
        "distancia_km": round(distance_km, 3),
        "duracion_min": None,
        "metodo": "geodesic_fallback",
        "advertencia": "Ruta estimada en linea recta por falta de ruta OSRM.",
        "origen_coords": origin_coords,
        "destino_coords": destination_coords,
        "origen_geocodificado": origin_coords,
        "destino_geocodificado": destination_coords,
        "route_geometry": [
            [origin_coords["lat"], origin_coords["lon"]],
            [destination_coords["lat"], destination_coords["lon"]],
        ],
    }
