# Arquitectura Carbono Zero: sensores e inteligencia

Carbono Zero ahora debe operar como sistema de gestion ambiental continua. La obra envia telemetria, el backend guarda el dato crudo, transforma consumos medibles en registros de emision y entrega contexto al motor de recomendaciones.

## Flujo principal

1. Dispositivo registrado en `DispositivoSensor`.
2. Lectura recibida en `POST /api/iot/ingesta/`.
3. Dato bruto guardado en `RegistroSensor`.
4. Si corresponde, se crea automaticamente un `RegistroEmision`.
5. El motor `intelligence_engine.py` une datos historicos, evidencias e IoT.
6. Las recomendaciones salen por `POST /api/intelligence/recommendations/`.

## Entidades nuevas

- `DispositivoSensor`: representa sensores fisicos o gateways instalados en obra.
- `RegistroSensor`: representa lecturas crudas recibidas desde sensores.
- `intelligence_engine.py`: arma el contexto ambiental y operacional para recomendaciones.

## Tipos iniciales de lectura

- diesel_litros
- gasolina_litros
- electricidad_kwh
- horas_maquinaria
- horas_encendido
- agua_litros
- gps_evento
- temperatura
- humedad

## Reglas de consolidacion

- Combustible, electricidad y horas de maquinaria pueden crear registros de emision.
- Temperatura, humedad y GPS quedan como telemetria operacional.
- Cada lectura puede usar `external_id` para evitar duplicados.
- La metadata permite trazar el registro ambiental hasta el sensor original.

## Endpoints nuevos

- `GET/POST /api/iot/dispositivos/`
- `GET/PATCH /api/iot/dispositivos/<dispositivo_id>/`
- `POST /api/iot/ingesta/`
- `GET /api/iot/registros/`
- `GET /api/iot/operacion/kpis/`
- `POST /api/intelligence/context/`
- `POST /api/intelligence/recommendations/`

## Prioridad siguiente

1. Validar migraciones con `python manage.py makemigrations iot` y `python manage.py migrate`.
2. Ejecutar pruebas con `python manage.py test apps.iot apps.analytics`.
3. Crear frontend para dispositivos, lecturas, KPIs y recomendaciones.
4. Separar los presets para que construccion, transporte, industrial y aserradero no mezclen sus flujos.
