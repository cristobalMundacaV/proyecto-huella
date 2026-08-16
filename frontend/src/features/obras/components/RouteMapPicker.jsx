import { useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { LocateFixed, MapPin, Search } from "lucide-react";
import { calculateRouteDistance } from "@/shared/services/api";
import { formatNumber } from "@/shared/utils/formatters";

const defaultCenter = [-38.7359, -72.5904];

function createMarkerIcon(label, tone) {
  return L.divIcon({
    className: "",
    html: `<div style="
      align-items:center;
      background:${tone};
      border:2px solid white;
      border-radius:999px;
      box-shadow:0 8px 20px rgba(0,0,0,.35);
      color:#042f2e;
      display:flex;
      font-size:12px;
      font-weight:800;
      height:30px;
      justify-content:center;
      width:30px;
    ">${label}</div>`,
    iconAnchor: [15, 15],
    iconSize: [30, 30],
  });
}

async function searchNominatim(query) {
  const response = await fetch(
    `https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&countrycodes=cl&q=${encodeURIComponent(
      query
    )}`,
    {
      headers: {
        Accept: "application/json",
      },
    }
  );

  if (!response.ok) {
    throw new Error("No se pudo buscar la direccion.");
  }

  const results = await response.json();

  if (!results.length) {
    throw new Error("No se encontro esa direccion.");
  }

  const place = results[0];

  return {
    address: place.display_name || query,
    coords: {
      lat: Number(place.lat),
      lon: Number(place.lon),
      display_name: place.display_name || query,
    },
  };
}

function toLatLng(coords) {
  if (!coords) {
    return null;
  }

  return [Number(coords.lat), Number(coords.lon ?? coords.lng)];
}

function RouteMapPicker({
  destinationCoords,
  destinationValue,
  onDestinationChange,
  onOriginChange,
  originCoords,
  originValue,
  routeGeometry,
  onDistanceCalculated,
}) {
  const destinationMarkerRef = useRef(null);
  const mapElementRef = useRef(null);
  const mapRef = useRef(null);
  const onDestinationChangeRef = useRef(onDestinationChange);
  const onOriginChangeRef = useRef(onOriginChange);
  const originMarkerRef = useRef(null);
  const polylineRef = useRef(null);
  const selectionModeRef = useRef("origin");
  const [error, setError] = useState("");
  const [searching, setSearching] = useState(null);
  const [selectionMode, setSelectionMode] = useState("origin");
  const [distanceResult, setDistanceResult] = useState(null);
  const [calculating, setCalculating] = useState(false);

  const originLatLng = useMemo(() => toLatLng(originCoords), [originCoords]);
  const destinationLatLng = useMemo(
    () => toLatLng(destinationCoords),
    [destinationCoords]
  );
  const routeLatLngs = useMemo(
    () =>
      (routeGeometry || [])
        .map((point) =>
          Array.isArray(point)
            ? [Number(point[0]), Number(point[1])]
            : toLatLng(point)
        )
        .filter(
          (point) =>
            point &&
            Number.isFinite(point[0]) &&
            Number.isFinite(point[1])
        ),
    [routeGeometry]
  );

  useEffect(() => {
    onDestinationChangeRef.current = onDestinationChange;
    onOriginChangeRef.current = onOriginChange;
  }, [onDestinationChange, onOriginChange]);

  useEffect(() => {
    selectionModeRef.current = selectionMode;
  }, [selectionMode]);

  useEffect(() => {
    if (!mapElementRef.current || mapRef.current) {
      return undefined;
    }

    const map = L.map(mapElementRef.current, {
      center: defaultCenter,
      scrollWheelZoom: true,
      zoom: 6,
    });
    mapRef.current = map;

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors",
      maxZoom: 19,
    }).addTo(map);

    map.on("click", (event) => {
      const coords = {
        lat: event.latlng.lat,
        lon: event.latlng.lng,
        display_name: `${event.latlng.lat.toFixed(6)}, ${event.latlng.lng.toFixed(6)}`,
      };
      const payload = {
        address: coords.display_name,
        coords,
      };

      if (selectionModeRef.current === "origin") {
        onOriginChangeRef.current(payload);
        setSelectionMode("destination");
      } else {
        onDestinationChangeRef.current(payload);
      }
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!mapRef.current) {
      return;
    }

    if (originLatLng) {
      if (!originMarkerRef.current) {
        originMarkerRef.current = L.marker(originLatLng, {
          icon: createMarkerIcon("O", "#6ee7b7"),
        }).addTo(mapRef.current);
      }
      originMarkerRef.current.setLatLng(originLatLng);
    } else if (originMarkerRef.current) {
      originMarkerRef.current.remove();
      originMarkerRef.current = null;
    }

    if (destinationLatLng) {
      if (!destinationMarkerRef.current) {
        destinationMarkerRef.current = L.marker(destinationLatLng, {
          icon: createMarkerIcon("D", "#67e8f9"),
        }).addTo(mapRef.current);
      }
      destinationMarkerRef.current.setLatLng(destinationLatLng);
    } else if (destinationMarkerRef.current) {
      destinationMarkerRef.current.remove();
      destinationMarkerRef.current = null;
    }

    if (originLatLng && destinationLatLng) {
      const hasRouteGeometry = routeLatLngs.length > 2;
      const path = hasRouteGeometry
        ? routeLatLngs
        : [originLatLng, destinationLatLng];

      if (!polylineRef.current) {
        polylineRef.current = L.polyline(path, {
          color: hasRouteGeometry ? "#22d3ee" : "#fbbf24",
          opacity: 0.9,
          weight: 4,
        }).addTo(mapRef.current);
      }
      polylineRef.current.setStyle({
        color: hasRouteGeometry ? "#22d3ee" : "#fbbf24",
        dashArray: hasRouteGeometry ? null : "8 8",
      });
      polylineRef.current.setLatLngs(path);
      mapRef.current.fitBounds(L.latLngBounds(path), { padding: [40, 40] });
    } else if (originLatLng || destinationLatLng) {
      mapRef.current.setView(originLatLng || destinationLatLng, 12);
    }
  }, [destinationLatLng, originLatLng, routeLatLngs]);

  useEffect(() => {
    let isCancelled = false;

    async function computeDistance() {
      if (!originLatLng || !destinationLatLng) {
        setDistanceResult(null);
        if (onDistanceCalculated) onDistanceCalculated(null);
        return;
      }

      setCalculating(true);
      try {
        const result = await calculateRouteDistance({
          origen: originValue,
          destino: destinationValue,
          origen_coords: originCoords,
          destino_coords: destinationCoords,
        });

        if (!isCancelled) {
          setDistanceResult(result);
          if (onDistanceCalculated) {
            onDistanceCalculated(result.distancia_km || null, result);
          }
        }
      } catch (err) {
        setDistanceResult(null);
        if (onDistanceCalculated) onDistanceCalculated(null, null);
      } finally {
        if (!isCancelled) setCalculating(false);
      }
    }

    computeDistance();

    return () => {
      isCancelled = true;
    };
    // Los valores textuales y callback no participan en la identidad de la ruta calculada.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [originLatLng, destinationLatLng, routeLatLngs]);

  const handleSearch = async (type) => {
    const value = type === "origin" ? originValue : destinationValue;

    if (!value.trim()) {
      setError("Escribe una direccion para buscarla en OpenStreetMap.");
      return;
    }

    setSearching(type);
    setError("");

    try {
      const payload = await searchNominatim(value);

      if (type === "origin") {
        onOriginChange(payload);
        setSelectionMode("destination");
      } else {
        onDestinationChange(payload);
      }
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSearching(null);
    }
  };

  return (
    <div className="mt-4 rounded-3xl border border-slate-800 bg-slate-950 p-4">
      <div className="mb-3 grid grid-cols-1 gap-3 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] xl:items-end">
        <label className="space-y-2 text-sm">
          <span className="text-slate-300">Origen proveedor / planta</span>
          <div className="flex gap-2">
            <input
              value={originValue}
              onChange={(event) =>
                onOriginChange({ address: event.target.value, coords: null })
              }
              className="min-w-0 flex-1 rounded-2xl border border-slate-700 bg-slate-900 px-4 py-3 text-slate-100 outline-none transition focus:border-emerald-400/60"
              placeholder="Busca o marca origen proveedor / planta"
            />
            <button
              type="button"
              onClick={() => handleSearch("origin")}
              disabled={searching === "origin"}
              className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-emerald-400/20 bg-emerald-400/10 text-emerald-200 disabled:opacity-60"
              aria-label="Buscar origen"
            >
              <Search size={18} />
            </button>
          </div>
        </label>

        <label className="space-y-2 text-sm">
          <span className="text-slate-300">Destino obra</span>
          <div className="flex gap-2">
            <input
              value={destinationValue}
              onChange={(event) =>
                onDestinationChange({ address: event.target.value, coords: null })
              }
              className="min-w-0 flex-1 rounded-2xl border border-slate-700 bg-slate-900 px-4 py-3 text-slate-100 outline-none transition focus:border-emerald-400/60"
              placeholder="Busca o marca destino obra"
            />
            <button
              type="button"
              onClick={() => handleSearch("destination")}
              disabled={searching === "destination"}
              className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-cyan-400/20 bg-cyan-400/10 text-cyan-200 disabled:opacity-60"
              aria-label="Buscar destino"
            >
              <Search size={18} />
            </button>
          </div>
        </label>

        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setSelectionMode("origin")}
            className={`flex items-center gap-2 rounded-2xl border px-4 py-3 text-sm font-bold ${
              selectionMode === "origin"
                ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-200"
                : "border-slate-700 bg-slate-900 text-slate-300"
            }`}
          >
            <MapPin size={16} />
            Origen proveedor / planta
          </button>
          <button
            type="button"
            onClick={() => setSelectionMode("destination")}
            className={`flex items-center gap-2 rounded-2xl border px-4 py-3 text-sm font-bold ${
              selectionMode === "destination"
                ? "border-cyan-400/30 bg-cyan-400/10 text-cyan-200"
                : "border-slate-700 bg-slate-900 text-slate-300"
            }`}
          >
            <LocateFixed size={16} />
            Destino obra
          </button>
        </div>
      </div>

      <div
        ref={mapElementRef}
        className="h-72 overflow-hidden rounded-2xl border border-slate-800 bg-slate-900"
      />

      <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <label className="space-y-2 text-sm">
          <span className="text-slate-300">Origen proveedor / planta</span>
          <input
            readOnly
            value={originValue || ""}
            className="min-w-0 w-full rounded-2xl border border-slate-700 bg-slate-900 px-4 py-3 text-slate-300 outline-none"
          />
        </label>

        <label className="space-y-2 text-sm">
          <span className="text-slate-300">Destino obra</span>
          <input
            readOnly
            value={destinationValue || ""}
            className="min-w-0 w-full rounded-2xl border border-slate-700 bg-slate-900 px-4 py-3 text-slate-300 outline-none"
          />
        </label>

        <label className="space-y-2 text-sm">
          <span className="text-slate-300">Distancia km</span>
          <input
            readOnly
            value={
              calculating
                ? "Calculando..."
                : distanceResult && distanceResult.distancia_km != null
                ? formatNumber(Number(distanceResult.distancia_km), 3)
                : ""
            }
            className="min-w-0 w-full rounded-2xl border border-slate-700 bg-slate-900 px-4 py-3 text-slate-300 outline-none"
          />
        </label>
      </div>

      <p className="mt-3 text-xs text-slate-500">
        Mapa por OpenStreetMap. Busqueda por Nominatim. Distancia por ruta OSRM.
      </p>
      {originLatLng && destinationLatLng && routeLatLngs.length <= 2 && (
        <p className="mt-2 text-sm text-amber-200">Distancia aproximada.</p>
      )}
      {error && <p className="mt-2 text-sm text-amber-200">{error}</p>}
    </div>
  );
}

export default RouteMapPicker;
