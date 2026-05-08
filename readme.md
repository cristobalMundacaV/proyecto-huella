# Carbono Zero — README completo

Resumen
-------
`Carbono Zero` es una plataforma para medir, analizar y optimizar la huella de carbono en la cadena de valor de productos madereros, desde el aserradero hasta su uso en construcción. Incluye:

- Backend API en `Django` + `Django REST Framework`.
- Frontend SPA en `React` + `Vite`.
- Procesos y utilidades en Python para ingestión, limpieza y cálculo de emisiones.
- Dashboard alternativo en `Streamlit`.
- Fase 12: Integración BIM / API para que constructoras y arquitectos consuman el "pasaporte" del lote.

Características clave
--------------------

- Registro y trazabilidad de `lotes` (volumen, especie, origen/destino).
- Cálculo de emisiones por actividades y transporte.
- Cálculo de CO2 almacenado en la madera y balance neto.
- Generación de Pasaporte Verde (PDF verificable) y certificado digital.
- Exportación pública y directa para integración BIM: JSON, CSV y ficha técnica.
- Endpoints y helpers para integración programática (ver sección API).

Requisitos
----------

- Python 3.11+ (se probó con 3.13)
- Node.js 18+ / npm 8+
- Git

Instalación rápida
-----------------

1) Clona el repositorio y crea el entorno Python:

```bash
git clone <repo-url> carbono-zero
cd carbono-zero
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

2) Instala dependencias del frontend:

```bash
cd frontend
npm install
cd ..
```

3) Configura variables de entorno copiando el ejemplo:

```bash
copy env.example .env    # Windows
```

4) Aplica migraciones y crea superusuario (opcional):

```bash
cd backend
python manage.py migrate
python manage.py createsuperuser
cd ..
```

Ejecución (desarrollo)
----------------------

- Levantar backend:

```bash
cd backend
python manage.py runserver
```

- Levantar frontend (otra terminal):

```bash
cd frontend
npm run dev
```

- Dashboard Streamlit (opcional):

```bash
streamlit run legacy/app_old/dashboard/streamlit_app.py
```

Variables de entorno principales
-------------------------------

Revisa `env.example` para la lista completa. Variables importantes:

- `DJANGO_SECRET_KEY` — secreto de Django.
- `DJANGO_DEBUG` — `True` para desarrollo.
- `VITE_API_URL` — URL base que usa el frontend para llamar a la API (por defecto `http://127.0.0.1:8000/api`).
- `OPENAI_API_KEY` — si quieres habilitar el asesor IA.

Arquitectura y rutas relevantes
------------------------------

- Backend API base: `/api/` (definida en `backend/config/urls.py`).
- App principal: `backend/apps/analytics` — modelos, vistas, servicios y tests.
- Frontend: `frontend/src` — componentes y `frontend/src/services/api.js` con helpers de integración.

Fase 12 — Integración BIM / API
--------------------------------

Esta fase permite a constructoras/arquitectos consumir el pasaporte del lote y materializarlo en modelos BIM o bases de datos.

Endpoints principales (GET):

- `GET /api/integraciones/lotes/<id_lote>/`
	- Respuesta JSON con payload BIM completo (payload construido por `backend/apps/analytics/services/integraciones.py`).
- `GET /api/integraciones/lotes/<id_lote>/export.json`
	- Forzado a descarga del JSON con el payload BIM.
- `GET /api/integraciones/lotes/<id_lote>/export.csv`
	- CSV con campos clave (`lote, producto, volumen_m3, emisiones_kgco2e, co2_almacenado, balance_neto, pasaporte, estado_confianza`).
- `GET /api/integraciones/lotes/<id_lote>/ficha-tecnica/`
	- Respuesta con `ficha_tecnica` y el objeto `bim` (propiedades para Pset en IFC/IFC material properties).

Helpers frontend
----------------

El frontend incluye helpers para construir las URLs de integración en `frontend/src/services/api.js`:

- `getLoteIntegracionUrl(idLote)`
- `getLoteExportJsonUrl(idLote)`
- `getLoteExportCsvUrl(idLote)`
- `getLoteFichaTecnicaUrl(idLote)`

Ejemplo de payload (ejemplo de respuesta API):

```json
{
	"lote": "LOTE-001",
	"producto": "Pino radiata dimensionado",
	"volumen_m3": 12,
	"emisiones_kgco2e": 500,
	"co2_almacenado": 1200,
	"balance_neto": -700,
	"pasaporte": "Verde"
}
```

Notas de integración BIM
------------------------

- El payload incluye un bloque `bim` con campos pensados para mapear a un `IfcMaterial` y a un `Pset`:

	- `bim.material_name`, `bim.classification`, `bim.ifc_material`, `bim.property_set`, `bim.properties`.

- Para integrar en modelos IFC/BIM: mapear `bim.properties` a propiedades del `Pset` del elemento material.

Export CSV
----------

El CSV de exportación está pensado para ingestión rápida en ERPs o sistemas de obra. Cabeceras y ejemplo:

```
lote,producto,volumen_m3,emisiones_kgco2e,co2_almacenado,balance_neto,pasaporte,estado_confianza
LOTE-001,Pino radiata dimensionado,12,500,1200,-700,Verde,Alta confianza
```

Tests
-----

Se incluyen tests unitarios y de integración en `backend/apps/analytics/tests.py`.

Ejecutar tests backend:

```bash
cd backend
python manage.py test analytics
```

Ejecutar los tests de Python del workspace:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Desarrollo frontend
-------------------

- Iniciar el servidor de desarrollo (Vite):

```bash
cd frontend
npm run dev
```

- Construir bundle de producción:

```bash
cd frontend
npm run build
```

Consumo de la API — ejemplos
---------------------------

1) Obtener payload BIM en JSON (curl):

```bash
curl -sS http://127.0.0.1:8000/api/integraciones/lotes/LOTE-001/ | jq
```

2) Descargar CSV:

```bash
curl -OJ http://127.0.0.1:8000/api/integraciones/lotes/LOTE-001/export.csv
```

3) Consumir desde un script Node/React: usar los helpers en `frontend/src/services/api.js` para construir URLs y descargar directamente.

Despliegue
---------

- Backend: desplegar `backend` en WSGI/ASGI (Gunicorn + Nginx o similar) y configurar variables de entorno.
- Frontend: servir `dist` generado por `npm run build` desde CDN o servidor estático.
- Asegurar `CORS` y `CSRF` en producción (ver `env.example` y `settings.py`).

Backup y restauracion de datos
------------------------------

El proyecto incluye un exportador de datos que genera un archivo `backup_datos.json` en la raiz del repositorio. Ese archivo se puede copiar al servidor productivo y restaurar con Django.

Exportar datos desde la raiz del proyecto:

```bash
cd backend
python manage.py exportar_datos
```

Exportar a otra ruta:

```bash
cd backend
python manage.py exportar_datos --output ../backup_datos.json
```

Restaurar en produccion desde la raiz del proyecto:

```bash
cd backend
python manage.py migrate
python manage.py importar_datos --input ../backup_datos.json
```

Si prefieres cargarlo directamente con `loaddata`, tambien funciona:

```bash
cd backend
python manage.py loaddata ../backup_datos.json
```

Contribuir
----------

1. Abre un issue describiendo el cambio o bug.
2. Crea una rama `feature/<descripcion>` o `fix/<descripcion>`.
3. Añade tests donde aplique.
4. Envía un PR y solicita revisión.

Contacto
--------

Para integraciones comerciales o soporte, contacta al equipo del proyecto (email interno o canal Slack del equipo).

Licencia
--------

Revisa el archivo de licencia del repositorio (si aplica) o agrega la licencia deseada antes de distribuir.

