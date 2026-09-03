# Infraestructura web versionada

## Arquitectura

- `https://carbonozero.mundacasolutions.com`: landing pública, assets y verificación pública en `/verificar/:codigo`.
- `https://app.carbonozero.mundacasolutions.com`: plataforma React. La raíz redirige temporalmente a `/login` y las demás rutas usan el fallback SPA.
- Ambos hosts envían `/api/` y `/admin/` a Django en `127.0.0.1:8000`.
- La plataforma responde `X-Robots-Tag: noindex, nofollow`.
- `/app` en el host público se conserva sólo como redirección legacy a la plataforma.

Las reglas viven en `ops/nginx/`. Certbot sólo obtiene certificados; nunca modifica Nginx.

## Instalación de un VPS nuevo

1. Crear registros DNS para `carbonozero.mundacasolutions.com` y `app.carbonozero.mundacasolutions.com` apuntando al VPS.
2. Instalar Git, Docker con Compose, Node/npm, Nginx, Certbot, rsync y curl.
3. Clonar el repositorio y preparar el entorno:

   ```bash
   git clone <repositorio> /home/ubuntu/proyecto-huella
   cd /home/ubuntu/proyecto-huella
   cp .env.example .env
   ```

4. Completar secretos y `LETSENCRYPT_EMAIL` en `.env`, cargar las variables y provisionar web:

   ```bash
   set -a
   source .env
   set +a
   sudo --preserve-env=LETSENCRYPT_EMAIL bash scripts/install_web_infra.sh
   ```

5. Instalar el worker y desplegar:

   ```bash
   sudo bash scripts/install_deploy_worker.sh
   bash deploy.sh
   ```

El instalador crea los webroots, activa primero HTTP para ACME, solicita o expande el certificado con ambos SAN y finalmente instala la configuración HTTPS. Si el certificado ya contiene ambos nombres, no invoca Certbot.

## Migración del VPS existente

1. Crear y comprobar el DNS de `app.carbonozero.mundacasolutions.com`.
2. Actualizar el checkout y completar en `.env` los hosts y orígenes de `.env.example`, especialmente `FRONTEND_URL`, `VITE_APP_URL`, `LANDING_URL`, `APP_URL` y `LETSENCRYPT_EMAIL`.
3. Ejecutar una vez:

   ```bash
   cd /home/ubuntu/proyecto-huella
   set -a
   source .env
   set +a
   sudo --preserve-env=LETSENCRYPT_EMAIL bash scripts/install_web_infra.sh
   bash deploy.sh
   ```

4. Verificar:

   ```bash
   bash scripts/check_web_endpoints.sh
   ```

Los despliegues posteriores llaman `scripts/reconcile_web_infra.sh` automáticamente. Esa reconciliación copia la configuración desde Git, garantiza el symlink, valida con `nginx -t` y recarga Nginx; no ejecuta Certbot ni altera otros virtual hosts.

## Operación

Para reparar o aplicar Nginx sin desplegar la aplicación completa:

```bash
sudo env APP_DIR=/home/ubuntu/proyecto-huella bash scripts/reconcile_web_infra.sh
```

La renovación normal queda a cargo del timer/servicio de Certbot instalado por el sistema operativo. Antes de publicar, puede validarse el contrato versionado con `bash scripts/test_web_infra.sh`.
