# Roles y permisos tenant

Carbono Zero separa el plano de plataforma del plano tenant. La administración de plataforma depende exclusivamente de `User.is_superuser`; no es un rol de `UsuarioOrganizacion`. Los permisos tenant nunca autorizan crear, suspender o eliminar organizaciones ni modificar metodología, capacidades o factores globales.

## Modelo

La autorización sigue: usuario → membresía activa → rol → permiso → alcance → recurso. La ausencia de membresía, un rol inválido o un permiso desconocido se deniega. El backend es la fuente de verdad; el frontend usa las capacidades retornadas por `/auth/me` únicamente para navegación y presentación.

Roles estándar:

- **Administrador:** configuración, equipo y operación completa de su tenant.
- **Responsable ambiental:** gobierno funcional ambiental sin administración legal ni de usuarios.
- **Analista ambiental:** preparación, análisis y registro; no aprueba ni confirma acciones segregadas.
- **Operador:** captura en terreno dentro de las obras asignadas; no gobierna configuración.
- **Revisor ambiental:** revisa, valida, observa y aprueba; no modifica el dato original ni administra el tenant.
- **Lector:** consulta sin mutaciones.

## Matriz resumida

| Dominio | Admin | Responsable | Analista | Operador | Revisor | Lector |
|---|---|---|---|---|---|---|
| Organización / equipo | gestionar | ver organización | ver | ver | ver | ver |
| Obras / estructura | gestionar | gestionar | ver | ver alcance | ver | ver |
| Datos / evidencias | gestionar y validar | gestionar y validar | crear/editar | crear/editar | revisar/validar | ver |
| Importaciones | crear/revisar/confirmar | crear/revisar/confirmar | crear/revisar | no por defecto | revisar/confirmar | ver |
| Indicadores / factores propios | gestionar/aprobar | gestionar | gestionar/preparar | ver | revisar/aprobar | ver |
| Problemas / acciones | gestionar/cerrar | gestionar/cerrar | crear/gestionar | crear/actualizar | revisar/cerrar | ver |
| Compliance / reportes | gestionar/aprobar | gestionar/generar | preparar | ver | revisar/aprobar | ver |
| Auditoría | ver | ver | no por defecto | no | ver | no por defecto |

El catálogo exhaustivo y la matriz ejecutable residen en `backend/apps/analytics/permissions.py`.

## Alcance

`organizacion` conserva acceso a todas las obras del tenant. `obras` exige al menos una relación formal `UsuarioObraAcceso` y limita tanto listados como recursos derivados. Una obra de otro tenant o fuera del alcance responde 404 para evitar enumeración. Los recursos puramente organizacionales se evalúan por permiso tenant, sin alcance de obra.

## Segregación y aislamiento

Crear, editar, revisar, validar, confirmar, aprobar y cerrar son permisos distintos. El orden obligatorio es: validar tenant, validar permiso y después validar alcance. Toda creación deriva la organización desde el endpoint validado; IDs de obra del payload deben pertenecer al tenant y al alcance. Los serializers de equipo no aceptan `is_staff`, `is_superuser`, grupos ni permisos Django. El último administrador activo no puede desactivarse, eliminarse ni degradarse.
