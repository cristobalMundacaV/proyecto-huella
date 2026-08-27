# INFRA-DEPLOY-01 — Deploy automatizado con systemd

## Arquitectura

Carbono Zero se reconcilia desde el propio VPS, sin Jenkins, GitHub Actions, webhooks ni
otro daemon residente:

```text
origin/main
    ↓ cada 2 minutos
systemd timer
    ↓
worker oneshot + flock
    ↓
fetch y comparación de SHA
    ↓ si cambió
checkout/reset + deploy.sh
    ↓ solo si todo termina correctamente
/var/lib/carbonozero-deploy/deployed.sha
```

GitHub funciona únicamente como repositorio. Journald conserva toda la salida del
worker y de `deploy.sh`.

## Instalación única

En el VPS, desde el checkout perteneciente al usuario de aplicación:

```bash
cd ~/proyecto-huella
git pull
sudo bash scripts/install_deploy_worker.sh
```

El instalador toma `SUDO_USER` como `APP_USER`, y el checkout actual como `APP_DIR`.
Puede configurarse explícitamente:

```bash
sudo APP_USER=ubuntu APP_DIR=/home/ubuntu/proyecto-huella BRANCH=main \
  bash scripts/install_deploy_worker.sh
```

Instala los ejecutables con `install -m 0755`; ningún pull posterior requiere
`chmod +x`. La configuración no secreta queda en `/etc/default/carbonozero-deploy`, el
estado en `/var/lib/carbonozero-deploy` y el lock en
`/var/lock/carbonozero-deploy-worker.lock`.

## Usuario y permisos

Systemd ejecuta el coordinador como root para administrar lock y estado. Todas las
operaciones Git y `deploy.sh` se ejecutan mediante `runuser` como `APP_USER`, nunca como
root. El checkout debe pertenecer a ese usuario.

El usuario de aplicación necesita:

- lectura/escritura del checkout y credenciales SSH de solo lectura para `origin`;
- permiso para usar Docker, normalmente pertenencia al grupo `docker`;
- los permisos no interactivos mínimos que ya necesita `deploy.sh` para publicar en
  `/var/www/carbonozero`, ejecutar `nginx -t` y recargar Nginx.

El instalador no crea `sudo ALL`, no modifica sudoers y no almacena credenciales. Si los
permisos existentes no son suficientes, el deploy falla y `deployed.sha` no cambia.

## Reconciliación y concurrencia

El timer usa `OnBootSec=2min`, `OnUnitInactiveSec=2min` y `Persistent=true`. El worker
adquiere `flock` sin espera; si ya hay otro deploy registra “Ya existe un despliegue
activo” y termina correctamente.

Cada ronda ejecuta `git fetch --prune origin main`, compara el SHA remoto con
`deployed.sha` y usa `git checkout -B` seguido de `git reset --hard`. El checkout del VPS
es deliberadamente descartable y no debe contener cambios locales.

El worker invoca:

```bash
SKIP_GIT_UPDATE=1 bash "$APP_DIR/deploy.sh"
```

Así `deploy.sh` conserva una única implementación de build, migraciones, frontend,
Nginx y healthchecks, sin repetir Git ni depender del bit ejecutable. Solo después de
que Docker Compose, `manage.py check`, migraciones, collectstatic, frontend, `nginx -t`,
reload y endpoints `/` y `/app` terminen correctamente se reemplaza atómicamente
`deployed.sha`.

Tras cada despliegue se consulta otra vez `origin/main`. Si hubo un push durante el
build, se ejecuta otra ronda. `MAX_ROUNDS=4` evita un loop infinito; si todavía quedan
cambios, el siguiente timer continúa desde el último SHA exitoso.

## Operación

```bash
# Estado y agenda
systemctl status carbonozero-deploy-worker.timer
systemctl list-timers | grep carbonozero

# Reconciliación inmediata, sin ejecutar deploy directamente
sudo carbonozero-request-deploy

# Logs
journalctl -u carbonozero-deploy-worker.service -f
journalctl -u carbonozero-deploy-worker.service --since today

# Último SHA exitoso
cat /var/lib/carbonozero-deploy/deployed.sha
```

Para deshabilitar la automatización:

```bash
sudo systemctl disable --now carbonozero-deploy-worker.timer
```

Para volver temporalmente al procedimiento manual de emergencia:

```bash
cd /home/ubuntu/proyecto-huella
bash deploy.sh
```

## Checklist de validación en servidor

1. Ejecutar el instalador una vez.
2. Revisar `systemctl status carbonozero-deploy-worker.timer`.
3. Revisar `systemctl list-timers | grep carbonozero`.
4. Ejecutar `sudo carbonozero-request-deploy`.
5. Observar `journalctl -u carbonozero-deploy-worker.service -f`.
6. Confirmar `/var/lib/carbonozero-deploy/deployed.sha`.
7. Hacer un push pequeño y seguro a `main`.
8. Esperar hasta dos minutos.
9. Confirmar el nuevo SHA, healthchecks y estado de contenedores.

## Rollback manual

Detén primero el timer para impedir una reconciliación inmediata hacia `origin/main`:

```bash
sudo systemctl stop carbonozero-deploy-worker.timer
cd /home/ubuntu/proyecto-huella
git fetch --prune origin main
git reset --hard <sha-anterior>
SKIP_GIT_UPDATE=1 bash deploy.sh
```

Después de resolver la causa, restaura `main` y vuelve a habilitar el timer. Este rollback
es lógico, no transaccional: una migración destructiva o incompatible puede impedir
volver completamente al binario anterior y requiere un plan de datos propio.

## Troubleshooting

- **No despliega:** revisar timer, `journalctl`, conectividad de `origin` y
  `/etc/default/carbonozero-deploy`.
- **Lock ocupado:** comprobar el worker activo; no borrar el lock mientras exista un
  despliegue. `flock` libera el bloqueo cuando termina el proceso.
- **Docker denegado:** revisar membresía del usuario de aplicación en el grupo Docker.
- **Nginx/sudo solicita contraseña:** configurar únicamente permisos no interactivos y
  acotados a las operaciones requeridas; no usar `NOPASSWD: ALL`.
- **Deploy fallido:** corregir la causa y esperar el siguiente timer o ejecutar el
  trigger manual. El SHA anterior permanece registrado.

## Jenkins, GitHub Actions y servicios externos

El `Jenkinsfile` histórico fue eliminado porque realizaba la misma reconciliación por
SSH y obligaba a mantener Jenkins, credenciales y un pipeline externo. Este cambio no
desinstala ni detiene Jenkins en el servidor. Si existe un Jenkins dedicado únicamente
a Carbono Zero, puede retirarse manualmente después de validar el timer:

```bash
sudo systemctl disable --now jenkins
```

No ejecutar ese comando si Jenkins también sirve Foodies u otro proyecto. No se creó
ningún workflow de GitHub Actions ni webhook.

## Deuda preservada

- El backend productivo continúa usando Django `runserver`. Debe migrarse a
  Gunicorn/Uvicorn en un correctivo separado, con dependencia y configuración
  explícitas; no se mezcló silenciosamente aquí.
- No existe `scripts/backup_db.sh` ni mecanismo equivalente. No se improvisó una
  política de backups en este alcance. Antes de migraciones sensibles se requiere
  definir almacenamiento, retención, cifrado y restauración verificada.
- `npm ci` y `docker compose up --build` siguen siendo los principales consumidores de
  memoria. `flock`, ausencia de Jenkins, eliminación de builds duplicados y `Nice=10`
  reducen presión sin imponer límites arbitrarios de Node.
- El primer alta debe validarse una vez en el VPS porque systemd, permisos Docker,
  credenciales Git, sudo mínimo, Nginx y endpoints públicos no pueden certificarse desde
  Windows local.
