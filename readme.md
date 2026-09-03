# Carbono Zero

Carbono Zero es una plataforma de inteligencia ambiental para constructoras, diseñada para medir, monitorear y gestionar emisiones de carbono en obras mediante registros de materiales, transporte, maquinaria, energia, agua, residuos y evidencias documentales.

## Capacidades principales

- Gestion de constructoras, etapas o frentes de obra y obras.
- Registro de emisiones por categoria constructiva.
- Calculo de emisiones en kg CO2e usando cantidad por factor de emision.
- Indicadores de intensidad de carbono por superficie declarada.
- Evidencias documentales asociadas a obras y registros de emision.
- Transporte de obra con estimacion de emisiones logisticas.
- Reportes ambientales y ficha ambiental verificable de obra.
- AI Advisor orientado a reduccion de impacto en construccion.
- Monitoreo IoT opcional para faena, maquinaria, energia y condiciones operativas.

## Dominio

El sistema trabaja con estos conceptos principales:

- Constructora
- Usuario de constructora
- Configuracion de constructora
- Etapa de obra
- Obra
- Registro de emision
- Evidencia de obra
- Transporte de obra
- Factor de emision
- Material de construccion

## API principal

Endpoints disponibles bajo `/api/`:

- `GET /auth/me/`
- `GET /auth/csrf-token/`
- `POST /auth/login/`
- `POST /auth/logout/`
- `POST /auth/bootstrap/`
- `GET /dashboard/`
- `GET|POST /constructoras/`
- `GET|PATCH|DELETE /constructoras/<constructora_id>/`
- `GET /constructoras/<constructora_id>/estado/`
- `GET|PATCH /constructoras/<constructora_id>/configuracion/`
- `GET /constructoras/<constructora_id>/dashboard/`
- `GET|POST /constructoras/<constructora_id>/etapas/`
- `GET|POST /constructoras/<constructora_id>/usuarios/`
- `GET|POST /constructoras/<constructora_id>/obras/`
- `GET|POST /constructoras/<constructora_id>/registros-emision/`
- `GET|POST /constructoras/<constructora_id>/evidencias/`
- `GET /constructoras/<constructora_id>/reportes/`
- `GET|POST /obras/`
- `GET|PATCH|DELETE /obras/<codigo_obra>/`
- `GET|POST /obras/<codigo_obra>/registros-emision/`
- `GET|POST /obras/<codigo_obra>/evidencias/`
- `GET|POST /obras/<codigo_obra>/transportes/`
- `GET /verificar/obra/<codigo_obra>/`
- `GET|POST /factores-emision/`
- `GET /factores/catalogo/`
- `GET|POST /materiales-construccion/`
- `POST /rutas/calcular-distancia/`
- `GET /sistema/estado/`
- `POST /ai-advisor/`

## Desarrollo con Docker

1. Crear `.env` desde `.env.example`.
2. Levantar servicios:

```bash
docker compose up -d --build
```

3. Ejecutar migraciones:

```bash
docker compose exec backend python manage.py migrate
```

4. Crear usuario inicial:

```bash
docker compose exec backend python manage.py createsuperuser
```

5. Cargar demo de construccion:

```bash
docker compose exec backend python manage.py seed_construccion_demo
```

## Despliegue web

La infraestructura Nginx es parte del repositorio. La landing pública vive en
`https://carbonozero.mundacasolutions.com` y la plataforma en
`https://app.carbonozero.mundacasolutions.com`.

Instalación mínima de un VPS:

```bash
git clone <repositorio> /home/ubuntu/proyecto-huella
cd /home/ubuntu/proyecto-huella
cp .env.example .env
# completar secretos, hosts, DNS y LETSENCRYPT_EMAIL
set -a && source .env && set +a
sudo --preserve-env=LETSENCRYPT_EMAIL bash scripts/install_web_infra.sh
sudo bash scripts/install_deploy_worker.sh
bash deploy.sh
```

La instalación y la migración detalladas están en
[`docs/architecture/WEB_INFRASTRUCTURE.md`](docs/architecture/WEB_INFRASTRUCTURE.md).

## Reset de base de datos de desarrollo

Los datos de desarrollo pueden regenerarse desde cero:

```bash
docker compose down
docker volume rm proyecto-huella_postgres_data
docker compose up -d --build
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_construccion_demo
```

## Validacion

Backend:

```bash
docker compose exec backend python manage.py makemigrations --check
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py check
docker compose exec backend python manage.py test
```

Frontend:

```bash
cd frontend
npm run build
```

## Demo incluida

El comando `seed_construccion_demo` crea:

- Constructora Andina SpA.
- Edificio Habitacional Los Robles.
- Etapas de excavacion, fundaciones, obra gruesa, instalaciones, terminaciones y retiro de residuos.
- Registros de hormigon, acero, aridos, cemento, transportes, maquinaria, energia y residuos.
- Factores iniciales para materiales, combustibles, electricidad, transporte y residuos.
