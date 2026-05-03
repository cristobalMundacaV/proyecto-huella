"""Wrapper para rutas/geocoding."""
from .rutas import geocode_location, route_distance_km


class MapaRutas:
    @staticmethod
    def geocode(q):
        return geocode_location(q)

    @staticmethod
    def calcular_distancia(origen, destino):
        return route_distance_km(origen, destino)


__all__ = ["MapaRutas"]
